# microbiONT: an AI-driven, privacy-focused platform for local Nanopore 16S and 18S amplicon analysis

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

* **OS:** Linux (Ubuntu 22.04+ recommended), Windows 10/11 (via WSL2), or macOS (Beta)
* **Hardware:** * **GPU:** At least NVIDIA GPU with **VRAM 6GB+** (Required for AI model).
    * **Storage:** At least 10GB free space.
* **Dorado:** Must be installed (usually via **MinKNOW** or standalone).
* **Homebrew:** Required for **macOS** users only.

## Installation

1.  **Download** the `microbiONT.zip` package from the [Releases page](#).
2.  **Extract** the zip file and open a terminal inside the extracted folder.
3.  **Run the installation script** (This only needs to be done once to set up the environment and AI model):

For Linux Users
    
```bash
chmod +x install.sh run.sh
./install.sh
```
For macOS Users
    
```bash
chmod +x install_macOS.sh run.sh
./install_macOS.sh
```    
IMPORTANT: The macOS version is currently in BETA. It relies on system-level dependencies (Homebrew), and full stability is not guaranteed across all macOS versions.
    	
## Database Setup (optional)

To use the Taxonomy (Emu) module, you need to set up the reference databases.

1.  We provide a default database inside the emu_db directory.
2.  If you have custom Emu databases, place the database folders inside the emu_db directory.
3.  The application will automatically detect any valid databases within this folder.

We already provide some database inside the **emu_db** directory.

## Usage

Start the application by running the launch script:

```bash
./run.sh
```
The application interface will automatically open in your default web browser.

## Quick Start

1. Launch the app and navigate to the *One-Click* tab on the sidebar.
2. Select **Run 16S Workflow** or **Run 18S Workflow**.
3. Click **Run** button located in the chat interface.


Note on Tools

This package includes portable binaries for Samtools, NanoFilt, Porechop, minimap2, emu, MAFFT, and FastTree in the bin/ directory.

It relies on your system's *Dorado* installation. You can download different versions of Dorado independently and specify the installation path in the app settings if needed. If Dorado is not currently installed, the install.sh script will automatically handle the installation for you.

## Citations

If you use microbiONT for your research, please cite the following tools:

    Dorado: https://github.com/nanoporetech/dorado
    Samtools: https://doi.org/10.1093/bioinformatics/btp352
    NanoFilt: https://doi.org/10.1093/bioinformatics/bty149
    Porechop: https://github.com/rrwick/Porechop
    NanoPlot: https://doi.org/10.1093/bioinformatics/btad311
    Emu: https://doi.org/10.1038/s41592-022-01520-4
    MAFFT: https://doi.org/10.1093/molbev/mst010 
    FastTree: https://doi.org/10.1371/journal.pone.0009490

## Powered by:

    Streamlit: https://github.com/streamlit/streamlit
    Ollama: https://github.com/ollama/ollama
    Llama 3.1: https://ai.meta.com/blog/meta-llama-3/

## License

This project is licensed under the MIT License - see the LICENSE file for details.
    
