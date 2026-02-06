# microbiONT: AI-Driven Nanopore Analysis Platform 

**microbiONT** is a GUI-based application for Oxford Nanopore Technologies (ONT) sequencing analysis, specifically designed for 16S and 18S amplicon studies. It integrates local Large Language Models (LLM) with standard bioinformatics tools to automate workflows from raw signal processing to taxonomy classification.

The application runs **entirely locally**, utilizing your GPU for processing, ensuring data privacy.

## Features

* **Standard Analysis Workflow**
    Automated pipeline for 16S/18S amplicons including Basecalling (Dorado), Filtering (NanoFilt), Demultiplexing (Porechop), and Taxonomy Classification (Emu).

* **Customizable Pipeline**
    Users can define custom start and stop points for their analysis (e.g., running only Demultiplexing and QC) or use individual modules independently.

* **Taxonomy and Format Conversion**
    Utilizes Emu for species-level classification and automatically formats outputs for downstream analysis tools like MicrobiomeAnalyst, FAPROTAX, and PICRUSt2.

* **Interactive Terminal**
    Includes a built-in terminal that allows users to execute bash commands directly or generate them using the integrated local AI assistant.

## Prerequisites

* **OS:** Linux (Ubuntu 22.04+ recommended) and Windows 10/11 (via WSL2)
* **Hardware:** * **GPU:** At least NVIDIA GPU with **VRAM 6GB+** (Required for AI model).
    * **Storage:** At least 10GB free space.
* **Dorado:** Must be installed (usually via **MinKNOW** or standalone).
* **Homebrew:** Required for **macOS** users only.

## Installation

1.  **Download** the `microbiONT_version.zip` package from the [Releases page](https://github.com/MBEBlab/microbiONT/releases).
2.  **Extract** the downloaded zip file.
3.  **OPEN** a terminal application. 
4.  **Navigate** to the extracted microbiONT folder.
3.  **Run the installation script** (This only needs to be done once to set up the environment and AI model):
   
```bash
# Navigate to the microbiONT directory (replace path/to/ with actual location)
cd path/to/microbiONT

# Grant execution permissions and install
chmod +x install.sh run.sh
./install.sh
```        	
## Database Setup (Optional)

To use the **Taxonomy (Emu)** module, reference databases must be configured. **microbiONT** comes with pre-configured databases located in the `emu_db/` directory, so no immediate action is required for standard usage.

### Adding Custom Databases
The application automatically detects valid databases. To add your own:
1. Place your custom Emu database folder inside the **`emu_db/`** directory.
2. Restart or refresh the application; the new database will appear in the dropdown menu.

### Included Databases
We provide a curated selection of databases for immediate use:
* **16S rRNA**:
  * `emu_default`: Default Emu database.
  * `16S_NCBI`: NCBI 16S RefSeq collection.
* **18S rRNA**:
  * `18S_Invertebrates` & `18S_C_P_P`: Sourced from the MetaZooGene Barcode Atlas and Database (MZGdb), covering Chromista, Plantae, and Protozoa.
  
## Usage

Open your terminal and execute the following commands to launch **microbiONT**:

```bash
# Navigate to the microbiONT directory (replace path/to/ with actual location)
cd path/to/microbiONT

#Run the startup script
./run.sh 
```
The application interface will automatically open in your default web browser.

## Quick Start

1. **Prepare Data**: Place your `.pod5` files into the **`pod5/`** directory.
   * *For testing*: Move `test.pod5` from the **`test_data/`** directory to the **`pod5/`** directory.
2. **Navigate**: Launch the app and go to the **One-Click Flow** tab on the sidebar.
3. **Select Pipeline**: Click **Run 16S Workflow**.
4. **Execute**: Review the generated command in the terminal window and click the **RUN** button to start the analysis.


Note on Tools

This package includes portable binaries for Samtools, NanoFilt, Porechop, minimap2, and emu in the bin/ directory.It relies on your system's *Dorado* installation. You can download different versions of Dorado independently and specify the installation path in the app settings if needed. If Dorado is not currently installed, the install.sh script will automatically handle the installation for you.

## Citations

If you use microbiONT for your research, please cite the following tools:

    Dorado: https://github.com/nanoporetech/dorado
    Samtools: https://doi.org/10.1093/bioinformatics/btp352
    NanoFilt: https://doi.org/10.1093/bioinformatics/bty149
    Porechop: https://github.com/rrwick/Porechop
    NanoPlot: https://doi.org/10.1093/bioinformatics/btad311
    Emu: https://doi.org/10.1038/s41592-022-01520-4
    MZGdb: https://doi.org/10.1007/s00227-021-03887-y

## Powered by:

    Streamlit: https://github.com/streamlit/streamlit
    Ollama: https://github.com/ollama/ollama
    Llama 3.1: https://ai.meta.com/blog/meta-llama-3/

## License

This project is licensed under the MIT License - see the LICENSE file for details.
    
