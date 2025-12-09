#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== microbiONT Installation Setup (Linux) ===${NC}"

# 1. Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed. Please install it using: sudo apt install python3"
    exit 1
fi

# 2. Create Python Virtual Environment (venv)
echo "Creating isolated Python environment..."
if [ ! -d "microbiONT_env" ]; then
    python3 -m venv microbiONT_env
    echo "Environment created."
else
    echo "Environment already exists."
fi

# 3. Install Python Dependencies
echo "Installing dependencies..."
source microbiONT_env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Check and Install Ollama
if ! command -v ollama &> /dev/null; then
    echo "Ollama not found. Installing..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "Ollama is already installed."
fi

# 5. Setup AI Model
echo "Setting up AI Model (Llama 3.1)..."
# Start Ollama in background to pull model
ollama serve > /dev/null 2>&1 &
PID=$!
sleep 5

echo "Pulling base model..."
ollama pull llama3.1

echo "Creating custom microbiONT expert model..."
ollama create microbiONT -f Modelfile

# Stop background Ollama
kill $PID

echo -e "${GREEN}=== Installation Complete! ===${NC}"
echo "You can now run the application using './run.sh'"
