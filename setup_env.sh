#!/bin/bash
# Script to create a Python virtual environment and install requirements.txt

set -e

ENV_DIR=".venv"
REQ_FILE="requirements.txt"

# Create virtual environment if it doesn't exist
if [ ! -d "$ENV_DIR" ]; then
    python3 -m venv $ENV_DIR
    echo "Virtual environment created at $ENV_DIR."
else
    echo "Virtual environment already exists at $ENV_DIR."
fi

# Activate the virtual environment
source $ENV_DIR/bin/activate

echo "Virtual environment activated."

# Install requirements if requirements.txt exists
if [ -f "$REQ_FILE" ]; then
    pip install --upgrade pip
    pip install -r $REQ_FILE
    echo "Requirements installed from $REQ_FILE."
else
    echo "$REQ_FILE not found. Skipping requirements installation."
fi
