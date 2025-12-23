#!/bin/bash

# Define colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== microbiONT Installation Setup (macOS) ===${NC}"

# ==========================================
# 1. Check Homebrew
# ==========================================
echo -e "${YELLOW}[1/6] Checking Homebrew...${NC}"
if ! command -v brew &> /dev/null; then
    echo -e "${RED}Error: Homebrew not found.${NC}"
    echo "Please install Homebrew first: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
fi

# ==========================================
# 2. Install System Tools (Minimap2 is crucial for Emu)
# ==========================================
echo -e "${YELLOW}[2/6] Installing Biology Tools...${NC}"
echo "Installing python3, samtools, mafft, fasttree, minimap2, git..."
brew install python3 samtools mafft fasttree minimap2 git wget

# ==========================================
# 3. Setup Python Environment
# ==========================================
echo -e "${YELLOW}[3/6] Setting up Python...${NC}"
if [ ! -d "microbiONT_env" ]; then
    python3 -m venv microbiONT_env
fi
source microbiONT_env/bin/activate
pip3 install --upgrade pip
pip3 install -r requirements.txt

# ==========================================
# 4. Install Emu from Source (Mac Special)
# ==========================================
echo -e "${YELLOW}[4/6] Installing Emu (Taxonomy Tool)...${NC}"

if ! command -v emu &> /dev/null; then
    echo "Downloading Emu source code..."
    
    git clone https://gitlab.com/treangenlab/emu.git temp_emu_install
       
    cd temp_emu_install
    echo "Installing Emu into virtual environment..."
    pip3 install .
        
    cd ..
    rm -rf temp_emu_install
    
    echo "✅ Emu installed successfully!"
else
    echo "Emu is already installed."
fi

# ==========================================
# 5. Install Ollama
# ==========================================
echo -e "${YELLOW}[5/6] Setting up AI (Ollama)...${NC}"
if ! command -v ollama &> /dev/null; then
    brew install ollama
fi

# ==========================================
# 6. Setup AI Model
# ==========================================
echo -e "${YELLOW}[6/6] Configuring AI Model...${NC}"
# Start Ollama in background
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
    echo "⚠️ Modelfile not found, skipping custom model."
fi

kill $PID

echo -e "${GREEN}=== Installation Complete! ===${NC}"
echo "IMPORTANT for Mac Users:"
echo "1. This app uses system tools installed via Homebrew."
echo "2. Please manually download 'Dorado for macOS' from GitHub if you need basecalling."
echo "   (Set the path in the app's Basecalling tab)"
echo ""
echo "Run the app using: ./run.sh"
