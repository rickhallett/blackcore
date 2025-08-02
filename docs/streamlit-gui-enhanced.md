# Nassau Campaign Intelligence - Enhanced GUI

## 🚀 Quick Start

```bash
# Launch the enhanced GUI
./run_enhanced_gui.sh

# Or manually:
streamlit run streamlit_app.py
```

## 🎯 New Features

### 1. 🕸️ Network Explorer (`pages/network_explorer.py`)
**Interactive Entity Relationship Visualization**
- **Visual network graph** showing connections between entities
- **Depth control** to explore 1-4 levels of relationships
- **Entity filtering** by type (people, organizations, events, transgressions)
- **Multiple layout algorithms** (spring, circular, Kamada-Kawai)
- **Relationship strength filtering** to focus on important connections
- **Export capabilities** for network data (JSON, CSV)
- **Entity detail cards** with full property inspection

**Key Use Cases:**
- Discover hidden connections between council members
- Map organizational relationships
- Identify influence networks
- Track transgression patterns across entities

### 2. ⚠️ Transgression Tracker (`pages/transgression_tracker.py`)
**Comprehensive Violation Monitoring Dashboard**
- **Severity distribution** pie chart (Critical, High, Medium, Low)
- **Timeline visualization** of violations over time
- **Pattern heatmap** showing violation types vs entities
- **Detailed violation cards** with evidence tracking
- **Trend analysis** for strategic insights
- **Export reports** in CSV and JSON formats

**Key Features:**
- Real-time violation statistics
- Evidence management system
- Related entity tracking
- Status monitoring (Active, Investigating, Resolved)
- Automated insights generation

### 3. 🔍 Advanced Search (`pages/advanced_search.py`)
**Powerful Search with Intelligent Filtering**
- **Full-text search** across all intelligence data
- **Advanced filters:**
  - Entity type selection
  - Date range filtering
  - Property-based filtering
  - Status and severity filters
- **Relevance scoring** with term highlighting
- **Search suggestions** based on partial queries
- **Faceted results** showing distribution
- **Pagination** for large result sets
- **Export results** to CSV

**Search Features:**
- Token-based indexing for fast searches
- Matched term highlighting
- Search history tracking
- Bulk result operations

### 4. ✅ Task Board (`pages/task_board.py`)
**Campaign Task Management with Kanban Board**
- **Three-column Kanban board** (To Do, In Progress, Done)
- **Task cards** with:
  - Priority indicators (color-coded borders)
  - Assignee badges
  - Due date tracking
  - Progress bars
  - Overdue alerts
- **Drag-and-drop** task movement (via buttons)
- **Task creation** with full metadata
- **Analytics dashboard:**
  - Priority distribution
  - Status breakdown
  - Burndown chart
  - Upcoming deadlines
- **Team workload view** showing task distribution

**Task Features:**
- Real-time task updates
- Team member assignment
- Due date management
- Progress tracking
- Tag system for categorization

## 📋 Navigation

The enhanced GUI uses Streamlit's multi-page architecture:

1. **Main Dashboard** - Original dashboard with key metrics
2. **Network Explorer** - Entity relationship visualization
3. **Transgression Tracker** - Violation monitoring
4. **Advanced Search** - Powerful search interface
5. **Task Board** - Campaign task management

## 🛠️ Technical Architecture

### Page Structure
```
blackcore/
├── streamlit_app.py          # Main dashboard
├── pages/                    # Enhanced features
│   ├── network_explorer.py   # Network visualization
│   ├── transgression_tracker.py # Violation tracking
│   ├── advanced_search.py    # Advanced search
│   └── task_board.py        # Task management
└── .streamlit/
    └── pages.toml           # Page configuration
```

### Data Sources
All pages read from the JSON files in `blackcore/models/json/`:
- `people_places.json` - People and locations
- `organizations_bodies.json` - Organizations
- `identified_transgressions.json` - Violations
- `actionable_tasks.json` - Campaign tasks
- `intelligence_transcripts.json` - Raw intelligence

### State Management
- Session state for user interactions
- Cached data loading for performance
- Persistent task storage in `campaign_tasks.json`

## 🎨 UI/UX Features

### Visual Design
- **Consistent color scheme** across all pages
- **Custom CSS** for polished appearance
- **Responsive layouts** adapting to screen size
- **Interactive visualizations** using Plotly
- **Smooth transitions** and hover effects

### User Experience
- **Contextual help** on all major features
- **Export options** on every page
- **Keyboard shortcuts** for common actions
- **Progress indicators** for long operations
- **Error handling** with user-friendly messages

## 🚦 Performance Optimizations

1. **Data Caching**
   - `@st.cache_resource` for data loaders
   - Indexed search for fast queries
   - Lazy loading for large datasets

2. **Visualization Performance**
   - Limited node rendering in network graphs
   - Pagination for search results
   - Progressive data loading

3. **State Management**
   - Minimal session state usage
   - Efficient rerun triggers
   - Batched updates

## 🔧 Configuration

### Environment Variables
No additional environment variables needed - uses existing Blackcore configuration.

### Customization Options
1. **Task Board Team Members**: Edit in `task_board.py`
2. **Network Layout**: Modify algorithms in `network_explorer.py`
3. **Search Index**: Adjust tokenization in `advanced_search.py`
4. **Transgression Severity Levels**: Update in `transgression_tracker.py`

## 📊 Campaign Use Cases

### Daily Operations
1. **Morning Brief**: Check Dashboard → Review new transgressions → Update task board
2. **Investigation**: Search for entity → Explore network → Document findings
3. **Task Management**: Create tasks → Assign to team → Track progress

### Strategic Analysis
1. **Relationship Mapping**: Use Network Explorer to identify key influencers
2. **Violation Patterns**: Analyze transgression trends for campaign messaging
3. **Resource Planning**: Use task analytics to optimize team efforts

### Reporting
1. Export transgression reports for public release
2. Generate network diagrams for presentations
3. Create task summaries for team meetings

## 🐛 Troubleshooting

### Common Issues

1. **"Backend Offline" Error**
   - Ensure FastAPI is running: `uvicorn blackcore.minimal.api.app:app --reload`
   - Or use test API: `python test_gui_app.py`

2. **Pages Not Found**
   - Run from blackcore directory
   - Ensure `pages/` directory exists
   - Check file permissions

3. **Slow Performance**
   - Clear Streamlit cache: Press 'C' in terminal
   - Reduce network depth in Network Explorer
   - Limit search results

## 🚀 Future Enhancements

### Planned Features
1. **Real-time Updates**: WebSocket integration for live data
2. **Mobile Responsive**: Optimized layouts for field use
3. **Report Builder**: Custom report generation with templates
4. **AI Insights**: Automated pattern detection and recommendations
5. **Collaboration**: Multi-user support with activity feeds

### Integration Points
1. **Notion Sync**: Direct updates to Notion databases
2. **Export Formats**: PDF reports, PowerPoint presentations
3. **External Data**: Import from other campaign tools
4. **Notifications**: Alerts for critical transgressions

This enhanced GUI transforms the Blackcore intelligence system into a powerful campaign command center, providing the Nassau Initiative team with professional-grade tools for their 2-month campaign timeline.