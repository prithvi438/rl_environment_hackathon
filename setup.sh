#!/bin/bash

# OpenEnv Setup Script for Scaler Meta PyTorch Hackathon
# This script automates the creation of a virtual environment and dependency installation.

echo "🚀 Starting OpenEnv Setup..."

# 1. Create Virtual Environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo "✅ Virtual environment already exists."
fi

# 2. Activate Virtual Environment
source venv/bin/activate

# 3. Install/Update Pip
echo "🔧 Updating pip..."
pip install --upgrade pip

# 4. Install Dependencies
if [ -f "requirements.txt" ]; then
    echo "📥 Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
else
    echo "❌ requirements.txt not found!"
    exit 1
fi

# 5. Run Validation
echo "🧪 Running environment validation..."
python3 validate.py

echo ""
echo "✨ Setup Complete!"
echo "--------------------------------------------------"
echo "To start the environment:"
echo "1. Run: source venv/bin/activate"
echo "2. Run: python3 server.py"
echo "3. (In a new terminal) Run: python3 inference.py"
echo "--------------------------------------------------"
