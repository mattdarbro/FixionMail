#!/bin/bash

# StoryKeeper Backend Startup Script
# This script handles Python environment setup and starts the backend server

set -e  # Exit on error

echo "🚀 StoryKeeper Backend Startup"
echo "================================"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "   Creating .env from .env.example..."
    cp .env.example .env
    echo "   ✅ .env created. Please edit it with your API keys:"
    echo "      - ANTHROPIC_API_KEY"
    echo "      - OPENAI_API_KEY"
    echo "      - ELEVENLABS_API_KEY (optional)"
    echo ""
    echo "   Then run this script again."
    exit 1
fi

# Detect Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: Python not found!"
    echo "   Please install Python 3.11 or higher"
    exit 1
fi

echo "✓ Using Python: $PYTHON_CMD"
$PYTHON_CMD --version
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    echo "   ✅ Virtual environment created"
    echo ""
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip -q
pip install -r backend/requirements.txt -q
echo "   ✅ Dependencies installed"
echo ""

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p generated_audio
mkdir -p generated_images
mkdir -p chroma_db
echo "   ✅ Directories created"
echo ""

# Start the server
echo "🌟 Starting FastAPI server..."
echo "   URL: http://127.0.0.1:8000"
echo "   Docs: http://127.0.0.1:8000/docs"
echo ""
echo "   Press Ctrl+C to stop"
echo "================================"
echo ""

cd backend && $PYTHON_CMD -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
