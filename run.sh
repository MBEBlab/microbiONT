#!/bin/bash

# Get current directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "Starting NanoBot..."

# 1. Add local 'bin' folder to PATH
# This ensures the app uses your bundled Samtools/NanoPlot/Porechop/NanoFilt
export PATH="$DIR/bin:$PATH"

# 2. Start Ollama (if not running)
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting AI Engine..."
    ollama serve > /dev/null 2>&1 &
    sleep 2
fi

# 3. Activate Environment and Run App
if [ -d "nanobot_env" ]; then
    source nanobot_env/bin/activate
    
    echo "Launching Interface..."
    # Run Streamlit
    streamlit run app.py
else
    echo "Error: Environment not found. Please run './install.sh' first."
    exit 1
fi
