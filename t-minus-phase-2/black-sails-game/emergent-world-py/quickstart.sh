#!/bin/bash

echo "🌍 Emergent World Engine - Quick Start"
echo "====================================="
echo

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3,11) else 1)" 2>/dev/null; then
    echo "❌ Error: Python 3.11+ is required (found $python_version)"
    echo "Please install Python 3.11 or higher"
    exit 1
fi

echo "✓ Python $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo
echo "Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# Check for LLM API keys
echo
echo "Checking for LLM API keys..."
if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "✓ Anthropic API key found"
elif [ -n "$OPENAI_API_KEY" ]; then
    echo "✓ OpenAI API key found"
else
    echo "⚠️  No LLM API keys found"
    echo "   NPCs will use simple rule-based decisions"
    echo "   Set ANTHROPIC_API_KEY or OPENAI_API_KEY for AI features"
fi

# Run the demo
echo
echo "Starting emergent world demo..."
echo "==============================="
echo

python main.py

echo
echo "Demo complete! 🎉"
echo
echo "Next steps:"
echo "- Check out examples/ for more scenarios"
echo "- Read the README.md for documentation"
echo "- Modify examples/simple_world.py to experiment"
echo
echo "To run again: python main.py"