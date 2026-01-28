import pandas as pd
import os
import argparse
import sys

# Argument Parsing
parser = argparse.ArgumentParser(description='MicrobiONT Post-Processing')
parser.add_argument('-i', '--input_dir', required=True, help='Emu output directory')
parser.add_argument('-d', '--db_dir', required=True, help='Emu Database directory')
parser.add_argument("-o", "--outdir", help="Output directory", default="converted_out")
parser.add_argument('--ma', action='store_true', help='Output MicrobiomeAnalyst files')
parser.add_argument('--picrust', action='store_true', help='Output PICRUSt2 files')
parser.add_argument('--faprotax', action='store_true', help='Output FAPROTAX files')

args = parser.parse_args()

class TreeNode:
    def __init__(self, name):
        self.name = name
        self.children = {} # {name: Node}

    def get_or_create_child(self, name):
        if name not in self.children:
            self.children[name] = TreeNode(name)
        return self.children[name]

    def merge_with(self, other_node):
       
        for child_name, child_node in other_node.children.items():
            if child_name in self.children:
                self.children[child_name].merge_with(child_node)
            else:
                self.children[child_name] = child_node

def build_compressed_tree(df, ranks):
   
    root = TreeNode("Root")

    for _, row in df.iterrows():
        current = root
        for rank in ranks:
            val = row[rank]
            name = str(val).strip() if not pd.isna(val) else "Unassigned"
            current = current.get_or_create_child(name)
        tax_id = str(row['tax_id']).strip()
        current.get_or_create_child(tax_id)

    def compress_node(node):
        if not node.children:
            return node

        compressed_children = {}
        for child_node in node.children.values():
            new_child = compress_node(child_node)
            if new_child.name in compressed_children:
                compressed_children[new_child.name].merge_with(new_child)
            else:
                compressed_children[new_child.name] = new_child
        
        node.children = compressed_children

        if len(node.children) == 1:
            only_child = list(node.children.values())[0]
            return only_child
        
        return node

    new_root = compress_node(root)
    return new_root

def to_newick(node):
    if not node.children:
        return f"{node.name}:1.0"
    child_strs = [to_newick(child) for child in node.children.values()]
    return f"({','.join(child_strs)}):1.0"

def get_tree_tips(node, tips_set):
    if not node.children:
        tips_set.add(node.name)
    else:
        for child in node.children.values():
            get_tree_tips(child, tips_set)

def run_post_processing():
    print(f"\n[MicrobiONT] Starting Post-processing...")
    print(f" Input: {args.input_dir}")
    print(f" Output: {args.outdir}")
    
    emu_output_dir = args.input_dir
    output_dir = args.outdir
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    input_emu_file = os.path.join(emu_output_dir, "emu-combined-tax_id-counts.tsv")
    
    # Output file paths
    out_ma_otu = os.path.join(output_dir, "MA_OTU_table.txt")
    out_ma_tax = os.path.join(output_dir, "MA_Taxonomy_table.txt")
    out_ma_tree = os.path.join(output_dir, "MA_phylogeny.tre") 
    out_faprotax = os.path.join(output_dir, "FAPROTAX_input.txt")
    out_picrust_table = os.path.join(output_dir, "picrust2_counts.txt")

    if not os.path.exists(input_emu_file):
        print(f"Error: Emu output file not found: {input_emu_file}")
        sys.exit(1)

    if args.ma or args.faprotax or args.picrust:
        print(" Processing Taxonomy and Data...")
        try:
            df = pd.read_csv(input_emu_file, sep='\t')
            
            df['tax_id'] = df['tax_id'].astype(str).str.replace(r'\.0$', '', regex=True)
            df['tax_id'] = 'tax_' + df['tax_id']
            
            tax_ranks = ['superkingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species']
            rank_prefixes = {'superkingdom': 'k', 'phylum': 'p', 'class': 'c', 'order': 'o', 'family': 'f', 'genus': 'g', 'species': 's'}
            sample_cols = [col for col in df.columns if col not in tax_ranks and col != 'tax_id']
            df[sample_cols] = df[sample_cols].fillna(0)
            
            df_tree = df.copy()

            def format_taxonomy(row):
                last_valid_val = "Unassigned"
                last_valid_prefix = "k"
                for rank in tax_ranks:
                    val = row[rank]
                    if pd.isna(val) or str(val).strip() == "":
                        row[rank] = f"{last_valid_prefix}__{last_valid_val}_unclassified"
                    else:
                        val = str(val).strip()
                        if rank == 'species': val = val.replace(" ", "_")
                        row[rank] = val
                        last_valid_val = val
                        last_valid_prefix = rank_prefixes[rank]
                return row
            
            df[tax_ranks] = df[tax_ranks].apply(format_taxonomy, axis=1)
            
            if args.ma:
                print("   > Generating MicrobiomeAnalyst files...")
                # 1. OTU Table
                ma_otu = df[['tax_id'] + sample_cols].copy()
                ma_otu.rename(columns={'tax_id': '#NAME'}, inplace=True)
                ma_otu.to_csv(out_ma_otu, sep='\t', index=False)
                otu_ids = set(ma_otu['#NAME'].astype(str))
                
                # 2. Taxonomy Table
                ma_tax = df[['tax_id'] + tax_ranks].copy()
                ma_tax.columns = ['#TAXONOMY', 'Kingdom', 'Phylum', 'Class', 'Order', 'Family', 'Genus', 'Species']
                ma_tax.to_csv(out_ma_tax, sep='\t', index=False)
                
                # 3. Tree Generation
                print("     Building Tree with Smart Merge...")
                try:
                    final_root = build_compressed_tree(df_tree, tax_ranks)
                    
                    if not final_root.children:
                        final_tree_str = f"({final_root.name}:1.0);"
                    else:
                        child_strs = [to_newick(child) for child in final_root.children.values()]
                        final_tree_str = f"({','.join(child_strs)});"
                    
                    with open(out_ma_tree, "w") as f:
                        f.write(final_tree_str)
                    
                    print("     🔍 Verifying Consistency...")
                    tree_tips = set()
                    if not final_root.children:
                        tree_tips.add(final_root.name)
                    else:
                        for child in final_root.children.values():
                            get_tree_tips(child, tree_tips)
                    
                    missing_in_tree = otu_ids - tree_tips
                    if missing_in_tree:
                        print(f"     ❌ CRITICAL ERROR: {len(missing_in_tree)} OTUs are still missing!")
                        print(f"        Missing IDs: {list(missing_in_tree)[:5]}")
                    else:
                        print("     ✅ SUCCESS: Tree tips match OTU table 100%.")
                        print(f"     ✅ Phylogenetic Tree created: {out_ma_tree}")
                    
                except Exception as e:
                    print(f"     ⚠️ Error in tree generation: {e}")
                    import traceback
                    traceback.print_exc()

            if args.faprotax:
                faprotax_df = df[['tax_id'] + sample_cols].copy()
                faprotax_df.rename(columns={'tax_id': '#OTU ID'}, inplace=True)
                faprotax_df['taxonomy'] = df.apply(lambda row: f"k__{row['superkingdom']}; p__{row['phylum']}; c__{row['class']}; o__{row['order']}; f__{row['family']}; g__{row['genus']}; s__{row['species']}", axis=1)
                faprotax_df.to_csv(out_faprotax, sep='\t', index=False)

            if args.picrust:
                picrust_df = df[['tax_id'] + sample_cols].copy()
                picrust_df.rename(columns={'tax_id': 'OTU_ID'}, inplace=True)
                picrust_df.to_csv(out_picrust_table, sep='\t', index=False)
                
        except Exception as e:
            print(f"Error processing table: {e}")
            sys.exit(1)

if __name__ == "__main__":
    run_post_processing()