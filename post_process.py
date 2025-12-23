import pandas as pd
import os
import shutil
import argparse
import subprocess
import sys


parser = argparse.ArgumentParser(description='MicrobiONT Post-Processing')
parser.add_argument('-i', '--input_dir', required=True, help='Emu output directory')
parser.add_argument('-d', '--db_dir', required=True, help='Emu Database directory')
parser.add_argument("-o", "--outdir", help="Output directory", default="converted_results")
parser.add_argument('--ma', action='store_true', help='Output MicrobiomeAnalyst files')
parser.add_argument('--picrust', action='store_true', help='Output PICRUSt2 files')
parser.add_argument('--faprotax', action='store_true', help='Output FAPROTAX files')
parser.add_argument('--tree', action='store_true', help='Build Phylogenetic Tree')

args = parser.parse_args()

def run_post_processing():
    print(f"\n[MicrobiONT] Starting Post-processing...")
    print(f" Input: {args.input_dir}")
    print(f" DB: {args.db_dir}")

    emu_output_dir = args.input_dir
    db_path = args.db_dir
    
   
    input_emu_file = os.path.join(emu_output_dir, "emu-combined-tax_id-counts.tsv")
    input_fasta_db = os.path.join(db_path, "species_taxid.fasta")
    
    out_ma_otu = os.path.join(emu_output_dir, "MA_OTU_table.txt")
    out_ma_tax = os.path.join(emu_output_dir, "MA_Taxonomy_table.txt")
    out_ma_tree = os.path.join(emu_output_dir, "MA_phylogeny.nwk")
    out_faprotax = os.path.join(emu_output_dir, "FAPROTAX_input.txt")
    out_picrust_table = os.path.join(emu_output_dir, "picrust2_counts.txt")
    out_picrust_fasta = os.path.join(emu_output_dir, "picrust2_reps.fasta")
    temp_alignment = os.path.join(emu_output_dir, "temp_alignment.fasta")

    if not os.path.exists(input_emu_file):
        print(f"Error: Emu output file not found: {input_emu_file}")
        sys.exit(1)

    
    if args.ma or args.faprotax or args.picrust or args.tree:
        print(" Processing Taxonomy Table...")
        try:
            df = pd.read_csv(input_emu_file, sep='\t')
            
            df['tax_id'] = df['tax_id'].astype(str).str.replace(r'\.0$', '', regex=True)
            df['tax_id'] = 'tax_' + df['tax_id']
            
            
            tax_ranks = ['superkingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species']
            rank_prefixes = {'superkingdom': 'k', 'phylum': 'p', 'class': 'c', 'order': 'o', 'family': 'f', 'genus': 'g', 'species': 's'}
            sample_cols = [col for col in df.columns if col not in tax_ranks and col != 'tax_id']
            df[sample_cols] = df[sample_cols].fillna(0)

            def format_taxonomy(row):
                last_valid_val = "Unassigned"
                last_valid_prefix = "k"
                for rank in tax_ranks:
                    val = row[rank]
                    if pd.isna(val) or str(val).strip() == "":
                        row[rank] = f"{last_valid_prefix}__{last_valid_val}"
                    else:
                        val = str(val).strip()
                        if rank == 'species': val = val.replace(" ", "_")
                        row[rank] = val
                        last_valid_val = val
                        last_valid_prefix = rank_prefixes[rank]
                return row

            df[tax_ranks] = df[tax_ranks].apply(format_taxonomy, axis=1)
            
            if args.ma:
                # MA Files
                ma_otu = df[['tax_id'] + sample_cols].copy()
                ma_otu.rename(columns={'tax_id': '#NAME'}, inplace=True)
                ma_otu.to_csv(out_ma_otu, sep='\t', index=False)
                ma_tax = df[['tax_id'] + tax_ranks].copy()
                ma_tax.columns = ['#TAXONOMY', 'Kingdom', 'Phylum', 'Class', 'Order', 'Family', 'Genus', 'Species']
                ma_tax.to_csv(out_ma_tax, sep='\t', index=False)
                print("   ✅ Generated MicrobiomeAnalyst files")

            if args.faprotax:
                faprotax_df = df[['tax_id'] + sample_cols].copy()
                faprotax_df.rename(columns={'tax_id': '#OTU ID'}, inplace=True)
                faprotax_df['taxonomy'] = df.apply(lambda row: f"k__{row['superkingdom']}; p__{row['phylum']}; c__{row['class']}; o__{row['order']}; f__{row['family']}; g__{row['genus']}; s__{row['species']}", axis=1)
                faprotax_df.to_csv(out_faprotax, sep='\t', index=False)
                print("   ✅ Generated FAPROTAX file")

            if args.picrust:
                picrust_df = df[['tax_id'] + sample_cols].copy()
                picrust_df.rename(columns={'tax_id': 'OTU_ID'}, inplace=True)
                picrust_df.to_csv(out_picrust_table, sep='\t', index=False)
                print("   ✅ Generated PICRUSt2 table")
                
        except Exception as e:
            print(f"Error processing table: {e}")
            sys.exit(1)

    
    if args.picrust or args.tree:
        print(" Extracting Sequences...")
        if not os.path.exists(input_fasta_db):
            print(f"⚠️ Database sequences not found: {input_fasta_db}")
        else:
            try:
                detected_tax_ids = set(df['tax_id'])
                written_ids = set()
                found_count = 0
                
                with open(out_picrust_fasta, "w") as out_f:
                    with open(input_fasta_db, "r") as in_f:
                        header, seq_lines, current_id, keep_seq = None, [], None, False
                        for line in in_f:
                            line = line.strip()
                            if line.startswith(">"):
                                if header and keep_seq and seq_lines:
                                    out_f.write(f">{current_id}\n{''.join(seq_lines)}\n")
                                    found_count += 1
                                    written_ids.add(current_id)
                                header = line
                                seq_lines = []
                                try:
                                    raw_id = line[1:].split(':')[0].strip()
                                    processed_id = "tax_" + raw_id
                                except: processed_id = "Unknown"
                                if processed_id in detected_tax_ids and processed_id not in written_ids:
                                    keep_seq = True
                                    current_id = processed_id
                                else:
                                    keep_seq = False
                            else:
                                if keep_seq: seq_lines.append(line)
                        if header and keep_seq and seq_lines:
                            out_f.write(f">{current_id}\n{''.join(seq_lines)}\n")
                            found_count += 1
                print(f"   ✅ Extracted {found_count} sequences.")

                
                if args.tree:
                    print("Building Phylogenetic Tree (MAFFT + FastTree)...")
                   
                    bin_dir = os.path.join(os.getcwd(), "bin")
                   
                    os.environ["PATH"] += os.pathsep + bin_dir
                    
                    if shutil.which("mafft"):
                        cmd_align = f"mafft --auto --quiet {out_picrust_fasta} > {temp_alignment}"
                        subprocess.run(cmd_align, shell=True, check=True)
                        
                        cmd_tree = f"FastTree -gtr -nt {temp_alignment} > {out_ma_tree}"
                        subprocess.run(cmd_tree, shell=True, check=True)
                        
                        print(f"   ✅ Tree generated: {out_ma_tree}")
                        if os.path.exists(temp_alignment): os.remove(temp_alignment)
                    else:
                        print("❌ mafft or FastTree not found in PATH or bin/ folder.")
            except Exception as e:
                print(f"❌ Error in tree building: {e}")

if __name__ == "__main__":
    run_post_processing()
