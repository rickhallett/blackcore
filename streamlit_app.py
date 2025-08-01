"""Nassau Campaign Intelligence - Streamlit GUI for Blackcore."""

import streamlit as st
import requests
import json
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import time

# Configuration
API_BASE_URL = "http://localhost:8000"

# Page configuration
st.set_page_config(
    page_title="Nassau Campaign Intelligence",
    page_icon="🏴‍☠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for campaign styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f4e79;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .status-good { color: #28a745; }
    .status-warning { color: #ffc107; }
    .status-error { color: #dc3545; }
</style>
""", unsafe_allow_html=True)


class BlackcoreAPI:
    """API client for Blackcore backend."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        # For now, skip authentication - would add JWT token here
        # self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def get_dashboard_stats(self):
        """Get dashboard statistics."""
        try:
            response = self.session.get(f"{self.base_url}/api/dashboard/stats", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to fetch dashboard stats: {e}")
            return None
    
    def search_global(self, query: str, entity_types=None, limit=50):
        """Perform global search."""
        params = {"query": query, "limit": limit}
        if entity_types:
            params["entity_types"] = entity_types
        
        try:
            response = self.session.get(
                f"{self.base_url}/api/search/global", 
                params=params,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Search failed: {e}")
            return None
    
    def get_health_status(self):
        """Check backend health."""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200, response.json() if response.status_code == 200 else None
        except:
            return False, None


# Initialize API client
@st.cache_resource
def get_api_client():
    return BlackcoreAPI(API_BASE_URL)


def show_connection_status():
    """Show backend connection status in sidebar."""
    api = get_api_client()
    
    with st.sidebar:
        st.markdown("### 🔌 System Status")
        
        is_healthy, health_data = api.get_health_status()
        
        if is_healthy:
            st.success("🟢 Backend Connected")
            if health_data:
                st.caption(f"Version: {health_data.get('version', 'Unknown')}")
        else:
            st.error("🔴 Backend Offline")
            st.caption("Check if FastAPI server is running on port 8000")


def show_dashboard():
    """Campaign Intelligence Dashboard."""
    st.markdown('<h1 class="main-header">🏴‍☠️ Nassau Campaign Intelligence</h1>', unsafe_allow_html=True)
    
    # Refresh button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🔄 Refresh Dashboard", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Fetch dashboard data
    api = get_api_client()
    
    with st.spinner("🔍 Gathering intelligence data..."):
        stats = api.get_dashboard_stats()
    
    if not stats:
        st.error("❌ Unable to connect to intelligence backend")
        st.info("Make sure the FastAPI server is running: `uvicorn blackcore.minimal.api.app:app --reload`")
        return
    
    # Key metrics row
    st.subheader("📊 Campaign Intelligence Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        transcript_count = stats.get("transcripts", {}).get("total", 0)
        transcript_delta = stats.get("transcripts", {}).get("today", 0)
        st.metric(
            "📝 Intelligence Reports", 
            transcript_count, 
            f"+{transcript_delta} today"
        )
    
    with col2:
        people_count = stats.get("entities", {}).get("people", 0)
        people_delta = stats.get("entities", {}).get("people_new", 0)
        st.metric(
            "👥 People Tracked", 
            people_count, 
            f"+{people_delta} new"
        )
    
    with col3:
        org_count = stats.get("entities", {}).get("organizations", 0)
        org_delta = stats.get("entities", {}).get("organizations_new", 0)
        st.metric(
            "🏢 Organizations", 
            org_count, 
            f"+{org_delta} new"
        )
    
    with col4:
        transgression_count = stats.get("entities", {}).get("transgressions", 0)
        transgression_delta = stats.get("entities", {}).get("transgressions_new", 0)
        st.metric(
            "⚠️ Violations Found", 
            transgression_count, 
            f"+{transgression_delta} new",
            delta_color="inverse"  # Red for new violations is good for campaign
        )
    
    # Recent Activity Timeline
    st.subheader("📈 Recent Intelligence Activity")
    
    recent_activity = stats.get("recent_activity", [])
    if recent_activity:
        # Convert to DataFrame for visualization
        df_activity = pd.DataFrame(recent_activity)
        df_activity['timestamp'] = pd.to_datetime(df_activity['timestamp'])
        
        # Create timeline chart
        fig = px.scatter(
            df_activity,
            x="timestamp",
            y="event_type",
            color="entity_type",
            size=[1] * len(df_activity),  # Equal size dots
            hover_data=["title", "description"],
            title="Intelligence Timeline"
        )
        
        fig.update_layout(
            height=300,
            xaxis_title="Time",
            yaxis_title="Activity Type"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Activity feed
        with st.expander("📋 Detailed Activity Feed", expanded=False):
            for activity in recent_activity[:10]:
                timestamp = datetime.fromisoformat(activity['timestamp'].replace('Z', '+00:00'))
                time_ago = datetime.now().replace(tzinfo=timestamp.tzinfo) - timestamp
                
                if time_ago.days > 0:
                    time_str = f"{time_ago.days} days ago"
                elif time_ago.seconds > 3600:
                    time_str = f"{time_ago.seconds // 3600} hours ago"
                else:
                    time_str = f"{time_ago.seconds // 60} minutes ago"
                
                st.markdown(f"""
                **{activity['title']}** *({time_str})*  
                {activity['description']}  
                *Type: {activity['event_type']} | Entity: {activity.get('entity_type', 'N/A')}*
                """)
                st.divider()
    else:
        st.info("No recent activity to display")
    
    # Processing Performance
    st.subheader("⚡ System Performance")
    
    processing_stats = stats.get("processing", {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_time = processing_stats.get("avg_processing_time", 0)
        st.metric("⏱️ Avg Processing", f"{avg_time:.1f}s")
    
    with col2:
        success_rate = processing_stats.get("success_rate", 0)
        st.metric("✅ Success Rate", f"{success_rate:.1%}")
    
    with col3:
        cache_hit_rate = processing_stats.get("cache_hit_rate", 0)
        st.metric("🎯 Cache Efficiency", f"{cache_hit_rate:.1%}")
    
    with col4:
        total_processed = processing_stats.get("total_processed", 0)
        st.metric("📊 Total Processed", total_processed)


def show_search():
    """Intelligence Search Interface."""
    st.title("🔍 Campaign Intelligence Search")
    
    # Search interface
    col1, col2 = st.columns([3, 1])
    
    with col1:
        query = st.text_input(
            "Search across all intelligence databases",
            placeholder="Enter search terms (people, organizations, events, violations...)",
            key="search_query"
        )
    
    with col2:
        entity_types = st.multiselect(
            "Filter by type",
            ["people", "organizations", "tasks", "events", "documents", "transgressions"],
            key="entity_filter"
        )
    
    if query:
        api = get_api_client()
        
        with st.spinner(f"🔍 Searching for '{query}'..."):
            results = api.search_global(query, entity_types, limit=100)
        
        if results and results.get("results"):
            st.success(f"Found {results['total_results']} results in {results['search_time']:.2f}s")
            
            # Results display
            for i, result in enumerate(results["results"]):
                with st.expander(f"#{i+1} - {result['type'].title()}: {result['title']}", expanded=i < 3):
                    
                    # Relevance score
                    relevance = result.get("relevance_score", 0)
                    st.progress(relevance, text=f"Relevance: {relevance:.1%}")
                    
                    # Entity type badge
                    entity_type = result['type']
                    type_colors = {
                        'people': '🟢',
                        'organizations': '🟡', 
                        'transgressions': '🔴',
                        'events': '🟣',
                        'documents': '🔵',
                        'tasks': '🟠'
                    }
                    st.markdown(f"**Type:** {type_colors.get(entity_type, '⚪')} {entity_type.title()}")
                    
                    # Show key properties
                    properties = result.get("properties", {})
                    for key, value in properties.items():
                        if value and key not in ["id"] and len(str(value)) < 200:
                            st.markdown(f"**{key}:** {value}")
                    
                    # Show snippet if available
                    if result.get("snippet"):
                        st.markdown(f"*📝 Context: {result['snippet']}*")
                    
                    # Quick actions
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button(f"📋 Copy Info", key=f"copy_{result['id']}"):
                            # Copy key info to clipboard (would need additional implementation)
                            st.success("Info copied!")
                    
                    with col2:
                        if st.button(f"🔗 View Relations", key=f"relations_{result['id']}"):
                            st.info("Relationship view coming soon!")
            
            # Search suggestions
            if results.get("suggestions"):
                st.subheader("💡 Search Suggestions")
                suggestion_cols = st.columns(min(5, len(results["suggestions"])))
                for i, suggestion in enumerate(results["suggestions"][:5]):
                    with suggestion_cols[i]:
                        if st.button(suggestion, key=f"suggestion_{i}", use_container_width=True):
                            st.session_state.search_query = suggestion
                            st.rerun()
        
        elif results:
            st.info(f"No results found for '{query}'. Try different search terms or check the suggestions below.")
        else:
            st.error("Search failed - please check your connection and try again")


def show_processing():
    """Processing Queue Management (Simplified)."""
    st.title("⚡ Intelligence Processing")
    
    st.info("🚧 Processing queue management interface coming soon!")
    
    # Mock processing status for now
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("⏳ Pending", 2)
    with col2:
        st.metric("🔄 Processing", 1)
    with col3:
        st.metric("✅ Completed", 47)
    with col4:
        st.metric("❌ Failed", 0)
    
    st.success("🟢 Processing worker is running normally")
    
    # Recent processing activity
    st.subheader("Recent Processing Activity")
    
    # Mock data
    processing_data = [
        {"Time": "15 min ago", "File": "Council_Meeting_2024-01-15.txt", "Status": "✅ Completed", "Entities": 6},
        {"Time": "2 hours ago", "File": "Mayor_Interview_2024-01-14.txt", "Status": "✅ Completed", "Entities": 4},
        {"Time": "4 hours ago", "File": "Planning_Committee_2024-01-13.txt", "Status": "✅ Completed", "Entities": 8},
    ]
    
    df = pd.DataFrame(processing_data)
    st.dataframe(df, use_container_width=True)


def main():
    """Main application."""
    # Sidebar navigation
    with st.sidebar:
        st.title("🏴‍☠️ Nassau Campaign")
        st.markdown("*Intelligence Operations*")
        st.markdown("---")
        
        # Navigation
        pages = {
            "📊 Dashboard": show_dashboard,
            "🔍 Intelligence Search": show_search, 
            "⚡ Processing": show_processing
        }
        
        selected_page = st.selectbox("Navigate", list(pages.keys()))
        
        st.markdown("---")
        
        # Show connection status
        show_connection_status()
        
        # Campaign info
        st.markdown("---")
        st.markdown("### 📅 Campaign Status")
        st.info("**Phase 1:** Mobilization & Intelligence Gathering")
        
        # Quick stats in sidebar
        st.markdown("### 🎯 Quick Stats")
        st.metric("Days Active", "15")
        st.metric("Phase 1 Remaining", "14 days")
        
    # Display selected page
    pages[selected_page]()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "*Nassau Campaign Intelligence System | Built with Streamlit & FastAPI*",
        help="Powered by Blackcore intelligence processing engine"
    )


if __name__ == "__main__":
    main()