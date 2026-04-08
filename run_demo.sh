#!/bin/bash

# OpenEnv Demo Launcher for Scaler Meta PyTorch Hackathon
# This script launches the visualizer and then the agent in a new terminal (Mac only).

echo "🚀 Launching OpenEnv Dashboard..."

# 1. Check for API Key
if [ -z "$HF_TOKEN" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️ OPENAI_API_KEY is not set. Please enter your API key to proceed (or press Ctrl+C to cancel):"
    read -p "API Key: " OPENAI_API_KEY
    export OPENAI_API_KEY=$OPENAI_API_KEY
fi

# 2. Activate Virtual Environment
source venv/bin/activate

# 3. Start the Server in the background
echo "🏠 Starting Environment Server on http://localhost:7860..."
python3 server.py > server.log 2>&1 &
SERVER_PID=$!

# Wait for server to start
sleep 3

# 4. Open the Browser
echo "🌐 Opening Dashboard in browser..."
open http://localhost:7860

# 5. Launch Inference Agent in a NEW Terminal (Mac Specific)
echo "🤖 Starting Inference Agent in a new terminal window..."
osascript -e "tell application \"Terminal\" to do script \"cd $(pwd) && source venv/bin/activate && export OPENAI_API_KEY=$OPENAI_API_KEY && python3 inference.py\""

echo ""
echo "✨ Demo is now running!"
echo "--------------------------------------------------"
echo "Dashboard: http://localhost:7860"
echo "Server PID: $SERVER_PID"
echo "To stop the server, run: kill $SERVER_PID"
echo "--------------------------------------------------"

# Trap Ctrl+C to kill the server when this script exits
trap "echo 'Stopping server...'; kill $SERVER_PID; exit" INT
wait $SERVER_PID
