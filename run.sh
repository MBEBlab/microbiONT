#!/bin/bash

# Get current directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "Starting microbiONT..."

# ==========================================
# 1. Platform Check
# ==========================================
OS="$(uname -s)"
if [ "$OS" = "Linux" ]; then
    echo "Linux detected. Adding local 'bin' tools to PATH."
    export PATH="$DIR/bin:$PATH"
elif [ "$OS" = "Darwin" ]; then
    echo "macOS detected. Using system tools (Homebrew/System)."
else
    echo "Unknown OS: $OS. Assuming system tools are available."
fi

# ==========================================
# 2. Start Ollama (if not running)
# ==========================================
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting AI Engine (Ollama)..."
    ollama serve > /dev/null 2>&1 &
    # Wait briefly to ensure it starts
    sleep 2
else
    echo "AI Engine is already running."
fi

# ==========================================
# 3. Activate Environment and Run App
# ==========================================
if [ -d "microbiONT_env" ]; then
    source microbiONT_env/bin/activate
    
    echo "Launching Interface..."
    # Run Streamlit
    streamlit run app.py
else
    echo "Error: Virtual environment 'microbiONT_env' not found."
    echo "Please run './install.sh' (Linux) or './install_mac.sh' (Mac) first."
    exit 1
fi
