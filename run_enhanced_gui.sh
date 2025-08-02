#!/bin/bash
# Launch script for Nassau Campaign Intelligence Enhanced GUI

echo "🏴‍☠️ Nassau Campaign Intelligence System"
echo "======================================"
echo ""

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "✅ Virtual environment found"
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "✅ Virtual environment found"
    source .venv/bin/activate
else
    echo "⚠️  No virtual environment found. Using system Python."
fi

# Check if Streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit not found. Installing..."
    pip install streamlit plotly pandas networkx
fi

# Check if FastAPI is running
echo ""
echo "Checking backend connection..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend API is running"
else
    echo "⚠️  Backend API not detected. Starting in background..."
    echo "   Run this in another terminal:"
    echo "   uvicorn blackcore.minimal.api.app:app --reload"
    echo ""
    echo "Or use the test API:"
    echo "   python test_gui_app.py"
    echo ""
    read -p "Press Enter to continue with GUI only..."
fi

# Create pages directory if it doesn't exist
if [ ! -d "pages" ]; then
    echo "❌ Pages directory not found. The enhanced features won't be available."
    echo "   Make sure you're running from the blackcore directory."
    exit 1
fi

# Launch Streamlit
echo ""
echo "🚀 Launching Enhanced Campaign Intelligence GUI..."
echo "================================================"
echo ""
echo "Features available:"
echo "  📊 Dashboard - Real-time campaign metrics"
echo "  🕸️ Network Explorer - Interactive entity relationships"
echo "  ⚠️ Transgression Tracker - Violation monitoring"
echo "  🔍 Advanced Search - Powerful filtering and facets"
echo "  ✅ Task Board - Campaign task management"
echo ""
echo "Opening in your browser..."

# Launch with multi-page support
streamlit run streamlit_app.py \
    --server.port 8501 \
    --server.address localhost \
    --browser.serverAddress localhost