# microbiONT: AI-Driven Nanopore Analysis Platform 

**microbiONT** is a privacy-focused, hybrid GUI application designed to streamline Nanopore sequencing analysis (specifically 16S/18S amplicons). By combining a local Large Language Model (**Llama 3.1**) with a user-friendly interface, it automates complex bioinformatics workflows without requiring command-line expertise.

## Features

* **One-Click SOP:** Automated pipeline for 16S/18S amplicon analysis (Basecalling -> Filtering -> Demultiplexing -> QC).
* **Hybrid Interface:** Choose between chatting with the AI assistant or using manual GUI controls.
* **Local Privacy:** All data processing and AI inference happen locally on your GPU. No data is uploaded to the cloud.
* **Integrated QC:** Built-in dashboard for quality control visualization and read statistics.

## Prerequisites

* **OS:** Linux (Ubuntu 22.04+ recommended).
* **Hardware:** * **GPU:** NVIDIA GPU with **VRAM 6GB+** (Required for AI model).
    * **Storage:** At least 10GB free space.
* **Dorado:** Must be installed (usually via **MinKNOW**).

## Installation

1.  **Download** the `microbiONT_Linux.zip` package from the [Releases page](#).
2.  **Extract** the zip file and open a terminal inside the folder.
3.  **Run the installation script** (This only needs to be done once to set up the environment and AI model):

    ```bash
    chmod +x install.sh run.sh
    ./install.sh
    ```

## Usage

Start the application by running the launch script:

```bash
./run.sh
```

The application interface will automatically open in your default web browser.
   
Note on Tools

This package includes portable binaries for Samtools, NanoFilt, Porechop, and NanoPlot in the bin/ directory.

It relies on your system's Dorado installation. You can download different versions of Dorado independently and specify the installation path in the app settings if needed.

Citations

If you use microbiONT for your research, please cite the following tools:

    Dorado: https://github.com/nanoporetech/dorado
    Samtools: https://doi.org/10.1093/bioinformatics/btp352
    NanoFilt: https://doi.org/10.1093/bioinformatics/bty149
    Porechop: https://github.com/rrwick/Porechop
    NanoPlot: https://doi.org/10.1093/bioinformatics/btad311

Powered by:

    Streamlit: https://github.com/streamlit/streamlit
    Ollama: https://github.com/ollama/ollama
    Llama 3.1: https://ai.meta.com/blog/meta-llama-3/

License

This project is licensed under the MIT License - see the LICENSE file for details.



    
