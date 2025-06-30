#!/bin/bash
set -e

# Update and install dependencies
sudo apt update
sudo apt install -y curl git

# Install Node.js (LTS) and npm
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Set up project dependencies
cd discord-ai-bot
npm install
npm install --save-dev wait-on

# Fix permissions for concurrently
chmod +x node_modules/.bin/concurrently
chmod -R +x node_modules/.bin/*

# Update the ollama:pull script to use llama3:8b model
sed -i 's/"ollama:pull": ".*"/"ollama:pull": "ollama pull llama3:8b"/' package.json

echo "Setup complete! You may need to log out and back in for ollama to work."
