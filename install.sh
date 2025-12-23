#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== microbiONT Installation Setup (Linux) ===${NC}"

# ==========================================
# 1. Install System Biology Tools 
# ==========================================
echo -e "${YELLOW}[1/5] Checking System Dependencies...${NC}"
echo "Installing biology tools (Samtools, MAFFT, FastTree, Minimap2)..."


if [ -x "$(command -v apt-get)" ]; then
    
    sudo apt-get update
    sudo apt-get install -y samtools mafft fasttree minimap2
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
# 5. Check and Install Ollama & AI Model
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
    echo "⚠️ Note: 'Modelfile' not found. Skipping custom model creation."
fi

# Stop background Ollama
kill $PID

echo -e "${GREEN}=== Installation Complete! ===${NC}"
echo "You can now run the application using './run.sh'"
