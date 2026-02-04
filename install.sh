#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== microbiONT Installation Setup (Linux) ===${NC}"

# ==========================================
# Install Dorado (Smart Detection)
# ==========================================
echo -e "${YELLOW}[Extra] Checking Dorado configuration...${NC}"

mkdir -p bin

SYSTEM_DORADO=""
NEED_DOWNLOAD=false

if command -v dorado &> /dev/null; then
    SYSTEM_DORADO=$(command -v dorado)
    echo -e "${GREEN}Found system Dorado at: $SYSTEM_DORADO${NC}"
elif [ -f "/opt/ont/dorado/bin/dorado" ]; then
    SYSTEM_DORADO="/opt/ont/dorado/bin/dorado"
    echo -e "${GREEN}Found Dorado at default path: $SYSTEM_DORADO${NC}"
else
    echo "System Dorado not found. Proceeding to automatic installation..."
    NEED_DOWNLOAD=true
fi

if [ "$NEED_DOWNLOAD" = false ]; then

    echo "Linking system Dorado to local bin..."
    ln -sf "$SYSTEM_DORADO" bin/dorado
    
else
    cd bin

    if [ -d "dorado_pkg" ] || [ -L "dorado" ]; then
        rm -rf dorado dorado_pkg dorado-*.tar.gz
    fi

    echo "Fetching latest release URL from GitHub..."
    LATEST_URL=$(curl -sL https://api.github.com/repos/nanoporetech/dorado/releases/latest \
    | grep "browser_download_url" \
    | grep "linux-x64.tar.gz" \
    | cut -d '"' -f 4)

    if [ -z "$LATEST_URL" ]; then
        echo -e "${YELLOW}GitHub API failed. Switching to fallback version.${NC}"
        LATEST_URL="https://cdn.oxfordnanoportal.com/software/analysis/dorado-1.1.1-linux-x64.tar.gz"
    fi

    echo "Downloading from: $LATEST_URL"
    wget -q --show-progress "$LATEST_URL" -O dorado_download.tar.gz

    echo "Extracting..."
    tar -xf dorado_download.tar.gz

    EXTRACTED_DIR=$(tar -tf dorado_download.tar.gz | head -1 | cut -f1 -d"/")
    mv "$EXTRACTED_DIR" dorado_pkg

    ln -sf dorado_pkg/bin/dorado dorado
    
    rm dorado_download.tar.gz
    cd ..
fi

echo "✅ Dorado setup complete!"

# ==========================================
# 1. Install System Biology Tools 
# ==========================================
echo -e "${YELLOW}[1/5] Checking System Dependencies...${NC}"
echo "Installing biology tools (Samtools, Minimap2)..."


if [ -x "$(command -v apt-get)" ]; then
    
    sudo apt-get update
    sudo apt-get install -y samtools minimap2
else
    echo -e "${YELLOW}Warning: 'apt-get' not found.${NC}"
    echo "Using portable binaries in 'bin/' folder as fallback."
fi

# ==========================================
# 2. Check for Python
# ==========================================
echo -e "${YELLOW}[2/5] Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed. Please install it using: sudo apt install python3"
    exit 1
fi

# ==========================================
# 3. Create Python Virtual Environment (venv)
# ==========================================
echo -e "${YELLOW}[3/5] Setting up Python Environment...${NC}"
echo "Creating isolated Python environment..."
if [ ! -d "microbiONT_env" ]; then
   
    if [ -x "$(command -v apt-get)" ]; then
         sudo apt-get install -y python3-venv
    fi
    python3 -m venv microbiONT_env
    echo "Environment created."
else
    echo "Environment already exists."
fi

# ==========================================
# 4. Install Python Dependencies
# ==========================================
echo -e "${YELLOW}[4/5] Installing Python Dependencies...${NC}"
source microbiONT_env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# ==========================================
# 5. Link NanoPlot to bin
# ==========================================
echo -e "${YELLOW}[5/6] Configuring NanoPlot...${NC}"
mkdir -p bin

VENV_NANOPLOT="$(pwd)/microbiONT_env/bin/NanoPlot"

if [ -f "$VENV_NANOPLOT" ]; then
    echo "Linking NanoPlot from venv to bin/..."
    
    ln -sf "$VENV_NANOPLOT" bin/NanoPlot
    echo "NanoPlot linked successfully!"
else
    echo "Warning: NanoPlot not found in venv. Please check requirements.txt."
fi

# ==========================================
# 6. Check and Install Ollama & AI Model
# ==========================================

if ! command -v curl &> /dev/null; then
    echo "Curl not found. Attempting to install it..."
    if [ -x "$(command -v apt-get)" ]; then
        sudo apt-get update
        sudo apt-get install -y curl
    else
        echo "Error: Curl is required but cannot be installed automatically. Please install 'curl' manually and re-run the script."
        exit 1
    fi
fi

echo -e "${YELLOW}[5/5] Setting up AI Model (Llama 3.1)...${NC}"

if ! command -v ollama &> /dev/null; then
    echo "Ollama not found. Installing..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "Ollama is already installed."
fi

# Start Ollama in background to pull model
ollama serve > /dev/null 2>&1 &
PID=$!
echo "Waiting for Ollama to start..."
sleep 5

echo "Pulling base model (llama3.1)..."
ollama pull llama3.1

if [ -f "Modelfile" ]; then
    echo "Creating custom microbiONT expert model..."
    ollama create microbiONT -f Modelfile
else
    echo "Note: 'Modelfile' not found. Skipping custom model creation."
fi

# Stop background Ollama
kill $PID

echo -e "${GREEN}=== Installation Complete! ===${NC}"
echo "You can now run the application using './run.sh'"
