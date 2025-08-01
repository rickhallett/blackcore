# Nassau Campaign Intelligence GUI - Setup Guide

## 🏴‍☠️ Overview

This guide explains how to set up and run the Streamlit GUI for the Nassau Campaign Intelligence system, providing a user-friendly interface for the Blackcore intelligence processing engine.

## 🚀 Quick Start (Recommended)

The fastest way to get the GUI running:

```bash
# 1. Install GUI dependencies
pip install -r requirements-streamlit.txt

# 2. Run the quick start script
python start_gui.py
```

This will:
- Start the FastAPI backend on http://localhost:8000
- Start the Streamlit GUI on http://localhost:8501  
- Open your browser automatically
- Handle shutdown when you press Ctrl+C

## 📋 Prerequisites

- Python 3.11+
- Existing Blackcore installation
- Environment variables configured (`.env` file)
- JSON data files in `blackcore/models/json/`

## 🔧 Manual Setup

If you prefer to run services manually:

### 1. Install Dependencies

```bash
pip install -r requirements-streamlit.txt
```

### 2. Start FastAPI Backend

```bash
# Option 1: Using uvicorn directly
uvicorn blackcore.minimal.api.app:app --reload --port 8000

# Option 2: Using Python module
python -m uvicorn blackcore.minimal.api.app:app --reload --port 8000
```

### 3. Start Streamlit GUI (in another terminal)

```bash
streamlit run streamlit_app.py --server.port 8501
```

### 4. Access the Interface

- **GUI Dashboard:** http://localhost:8501
- **API Documentation:** http://localhost:8000/docs
- **API Health Check:** http://localhost:8000/health

## 🐳 Docker Deployment

For production deployment or isolated environments:

```bash
# Build and run with Docker Compose
docker-compose -f docker-compose.gui.yml up --build

# Or run in background
docker-compose -f docker-compose.gui.yml up -d --build
```

This starts both services with proper networking and health checks.

## 🎯 Features Available

### Dashboard View
- Real-time campaign intelligence metrics
- Recent activity timeline
- Processing performance stats
- System health monitoring

### Intelligence Search
- Global search across all databases
- Entity type filtering (people, organizations, transgressions, etc.)
- Relevance scoring and snippets
- Search suggestions

### Processing Monitor (Coming Soon)
- Queue status and job history
- Performance metrics
- Error tracking

## 🔍 Troubleshooting

### Backend Connection Issues

**Problem:** "Backend Offline" in sidebar
**Solutions:**
1. Check if FastAPI is running on port 8000
2. Verify no firewall blocking localhost:8000
3. Check console for FastAPI startup errors

### Search Not Working

**Problem:** Search returns no results
**Solutions:**
1. Verify JSON files exist in `blackcore/models/json/`
2. Check file permissions
3. Ensure JSON files have correct structure

### Import Errors

**Problem:** `ModuleNotFoundError` when starting
**Solutions:**
```bash
# Install missing dependencies
pip install -r requirements-streamlit.txt

# If still failing, install individually
pip install streamlit plotly pandas requests
```

### Port Conflicts

**Problem:** "Port already in use"
**Solutions:**
```bash
# Find process using port
lsof -i :8000  # or :8501

# Kill existing process
kill -9 <PID>

# Or use different ports
uvicorn blackcore.minimal.api.app:app --port 8001
streamlit run streamlit_app.py --server.port 8502
```

## 📊 Configuration

### API Base URL

If running services on different machines or ports, update the API URL in `streamlit_app.py`:

```python
API_BASE_URL = "http://your-api-host:8000"
```

### Environment Variables

The GUI respects the same environment variables as the main Blackcore system:

```bash
BLACKCORE_MASTER_KEY=your-master-key
NOTION_API_KEY=your-notion-key
ANTHROPIC_API_KEY=your-claude-key
```

## 🛠️ Development

### Adding New Features

1. **Backend (FastAPI):**
   - Add new endpoints in `blackcore/minimal/api/`
   - Define response models in `models.py`
   - Include router in `app.py`

2. **Frontend (Streamlit):**
   - Add new functions to `streamlit_app.py`
   - Update navigation in `main()`
   - Add API client methods as needed

### File Structure

```
blackcore/
├── streamlit_app.py                     # Main GUI application
├── start_gui.py                         # Quick start script
├── requirements-streamlit.txt           # GUI dependencies
├── docker-compose.gui.yml              # Docker deployment
├── Dockerfile.streamlit                # Streamlit container
└── blackcore/minimal/api/
    ├── dashboard_endpoints.py          # Dashboard API
    ├── search_endpoints.py             # Search API
    └── models.py                       # Response models
```

## 🔐 Security Notes

- The GUI currently runs without authentication for simplicity
- For production deployment, implement proper authentication
- Use HTTPS in production environments
- Secure environment variables appropriately

## 📞 Support

For issues specific to the GUI:
1. Check this troubleshooting guide
2. Verify backend API is accessible at `/health`
3. Check browser console for JavaScript errors
4. Review Streamlit logs for Python errors

## 🎉 Success Checklist

✅ FastAPI backend starts without errors  
✅ Streamlit GUI loads at http://localhost:8501  
✅ Sidebar shows "🟢 Backend Connected"  
✅ Dashboard displays intelligence metrics  
✅ Search returns results from your data  
✅ No errors in terminal or browser console  

When all items are checked, you're ready for campaign intelligence operations! 🏴‍☠️