#!/bin/bash

# Define colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== microbiONT Setup (macOS Metal Fix) ===${NC}"

# ==========================================
# 0. Clean up
# ==========================================
echo -e "${YELLOW}[0/7] Cleaning up...${NC}"
rm -rf bin microbiONT_env temp_emu_install temp_porechop dorado.zip dorado_pkg dorado
mkdir -p bin

# ==========================================
# 1. Check Architecture
# ==========================================
ARCH=$(uname -m)
if [[ "$ARCH" != "arm64" ]]; then
    echo -e "${RED}Error: This script is for Apple Silicon (M1/M2/M3) only.${NC}"
    exit 1
fi

# ==========================================
# 2. Install System Tools
# ==========================================
echo -e "${YELLOW}[1/7] Installing System Tools...${NC}"
if ! command -v brew &> /dev/null; then
    echo -e "${RED}Error: Homebrew not found.${NC}"
    exit 1
fi

echo "Installing Python 3.11 & dependencies..."
brew install python@3.11 samtools minimap2 git wget ollama unzip

# ==========================================
# 3. Setup Python Environment
# ==========================================
echo -e "${YELLOW}[2/7] Creating Virtual Env (Python 3.11)...${NC}"

PYTHON_EXEC=""
if [ -f "$(brew --prefix)/bin/python3.11" ]; then
    PYTHON_EXEC="$(brew --prefix)/bin/python3.11"
elif command -v python3.11 &> /dev/null; then
    PYTHON_EXEC=$(command -v python3.11)
else
    echo -e "${RED}Error: Python 3.11 failed.${NC}"
    exit 1
fi

echo "Using: $PYTHON_EXEC"
$PYTHON_EXEC -m venv microbiONT_env
source microbiONT_env/bin/activate
pip install --upgrade pip

echo "Installing Python libs..."
pip install streamlit streamlit-option-menu pandas requests pillow pysam flatten_dict biopython tqdm numpy NanoPlot NanoFilt

# ==========================================
# 4. Install Porechop
# ==========================================
echo -e "${YELLOW}[3/7] Installing Porechop...${NC}"
if ! pip show porechop &> /dev/null; then
    git clone https://github.com/rrwick/Porechop.git temp_porechop
    cd temp_porechop
    pip install .
    cd ..
    rm -rf temp_porechop
else
    echo "Porechop already installed."
fi

# ==========================================
# 5. Install Emu
# ==========================================
echo -e "${YELLOW}[4/7] Installing Emu...${NC}"
if ! pip show emu &> /dev/null; then
    git clone https://gitlab.com/treangenlab/emu.git temp_emu_install
    cd temp_emu_install
    pip install .
    cd ..
    rm -rf temp_emu_install
else
    echo "Emu installed."
fi

# ==========================================
# 6. Link Tools
# ==========================================
echo -e "${YELLOW}[5/7] Linking binaries...${NC}"
ln -sf $(which samtools) bin/samtools
ln -sf $(which minimap2) bin/minimap2

VENV_BIN="$(pwd)/microbiONT_env/bin"
if [ -f "$VENV_BIN/NanoPlot" ]; then ln -sf "$VENV_BIN/NanoPlot" bin/NanoPlot; fi
if [ -f "$VENV_BIN/NanoFilt" ]; then ln -sf "$VENV_BIN/NanoFilt" bin/NanoFilt; fi
if [ -f "$VENV_BIN/porechop" ]; then ln -sf "$VENV_BIN/porechop" bin/porechop; fi

# ==========================================
# 7. Install Dorado
# ==========================================
echo -e "${YELLOW}[6/7] Installing Dorado (v1.1.1 arm64)...${NC}"

if command -v dorado &> /dev/null; then
    echo "Found system Dorado, linking..."
    ln -sf $(command -v dorado) bin/dorado
else
    cd bin
    
    DORADO_URL="https://cdn.oxfordnanoportal.com/software/analysis/dorado-1.1.1-osx-arm64.zip"
    DIR_NAME="dorado-1.1.1-osx-arm64"

    echo "Downloading from: $DORADO_URL"
    curl -L "$DORADO_URL" -o dorado.zip --progress-bar

    if [ -f "dorado.zip" ]; then
        echo "Extracting ZIP..."
        unzip -q dorado.zip
        
        if [ -d "$DIR_NAME" ]; then
            mv "$DIR_NAME/bin/"* .
            
            if [ -d "$DIR_NAME/lib" ]; then cp -r "$DIR_NAME/lib" .; fi
            
            xattr -r -d com.apple.quarantine dorado 2>/dev/null || true
            xattr -r -d com.apple.quarantine *.metallib 2>/dev/null || true
            
            rm -rf dorado.zip "$DIR_NAME" __MACOSX
            chmod +x dorado
            
            echo "Verifying Dorado installation:"
            if [ -f "libdorado.metallib" ]; then
                echo "✅ GPU Driver (metallib) found."
            else
                echo -e "${RED}⚠️ Warning: metallib file missing!${NC}"
            fi
            ./dorado --version
            
            echo "✅ Dorado installed."
        else
            echo -e "${RED}Extraction failed. Expected folder '$DIR_NAME' not found.${NC}"
        fi
    else
        echo -e "${RED}Download failed.${NC}"
    fi
    cd ..
fi

# ==========================================
# 8. Configure AI
# ==========================================
echo -e "${YELLOW}[7/7] Configuring AI...${NC}"
if ! pgrep -x "ollama" > /dev/null; then
    ollama serve > /dev/null 2>&1 &
    PID=$!
    echo "Waiting for Ollama..."
    sleep 5
fi

ollama pull llama3.1
if [ -f "Modelfile" ]; then ollama create microbiONT -f Modelfile; fi

echo -e "${GREEN}=== Installation Complete! ===${NC}"
echo "Run using: ./run.sh"
