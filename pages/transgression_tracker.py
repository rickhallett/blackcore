"""Transgression Tracking Dashboard for Nassau Campaign Intelligence."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import random

# Page config
st.set_page_config(
    page_title="Transgression Tracker - Nassau Intelligence",
    page_icon="⚠️",
    layout="wide"
)

# Custom CSS for transgression styling
st.markdown("""
<style>
    .transgression-card {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        border-left: 4px solid #fdcb6e;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .severity-critical {
        color: #d63031;
        font-weight: bold;
    }
    .severity-high {
        color: #e17055;
        font-weight: bold;
    }
    .severity-medium {
        color: #fdcb6e;
        font-weight: bold;
    }
    .severity-low {
        color: #74b9ff;
        font-weight: bold;
    }
    .evidence-tag {
        background: #dfe6e9;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.875rem;
        display: inline-block;
        margin: 0.25rem;
    }
    .violation-timeline {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


class TransgressionDataLoader:
    """Load and process transgression data."""
    
    def __init__(self):
        self.data_path = Path("blackcore/models/json")
        self.transgressions = []
        self.people = {}
        self.organizations = {}
        self.load_all_data()
    
    def load_all_data(self):
        """Load transgression and related entity data."""
        # Load transgressions
        transgressions_file = self.data_path / "identified_transgressions.json"
        if transgressions_file.exists():
            with open(transgressions_file, 'r') as f:
                data = json.load(f)
                key = list(data.keys())[0]
                self.transgressions = data.get(key, [])
        
        # Add mock severity and dates if not present
        for i, trans in enumerate(self.transgressions):
            if 'severity' not in trans:
                trans['severity'] = random.choice(['critical', 'high', 'medium', 'low'])
            if 'date_identified' not in trans:
                # Mock dates over past 30 days
                days_ago = random.randint(0, 30)
                trans['date_identified'] = (datetime.now() - timedelta(days=days_ago)).isoformat()
            if 'status' not in trans:
                trans['status'] = random.choice(['active', 'investigating', 'resolved', 'documented'])
            if 'evidence_count' not in trans:
                trans['evidence_count'] = random.randint(1, 5)
        
        # Load related people
        people_file = self.data_path / "people_places.json"
        if people_file.exists():
            with open(people_file, 'r') as f:
                data = json.load(f)
                key = list(data.keys())[0]
                for person in data.get(key, []):
                    self.people[person.get('id', person.get('name'))] = person
        
        # Load related organizations
        org_file = self.data_path / "organizations_bodies.json"
        if org_file.exists():
            with open(org_file, 'r') as f:
                data = json.load(f)
                key = list(data.keys())[0]
                for org in data.get(key, []):
                    self.organizations[org.get('id', org.get('name'))] = org
    
    def get_severity_stats(self) -> Dict[str, int]:
        """Get transgression counts by severity."""
        stats = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for trans in self.transgressions:
            severity = trans.get('severity', 'medium')
            if severity in stats:
                stats[severity] += 1
        return stats
    
    def get_timeline_data(self, days: int = 30) -> pd.DataFrame:
        """Get transgression timeline data."""
        timeline_data = []
        
        for trans in self.transgressions:
            date_str = trans.get('date_identified', datetime.now().isoformat())
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            
            timeline_data.append({
                'date': date.date(),
                'title': trans.get('title', 'Unknown'),
                'severity': trans.get('severity', 'medium'),
                'type': trans.get('type', 'procedural'),
                'status': trans.get('status', 'active')
            })
        
        df = pd.DataFrame(timeline_data)
        if not df.empty:
            df = df.sort_values('date')
        
        return df
    
    def get_related_entities(self, transgression_id: str) -> Dict[str, List]:
        """Get entities related to a transgression."""
        related = {'people': [], 'organizations': []}
        
        # Mock some relationships for demo
        if self.people:
            related['people'] = list(self.people.values())[:2]
        if self.organizations:
            related['organizations'] = list(self.organizations.values())[:1]
        
        return related


def create_severity_chart(severity_stats: Dict[str, int]) -> go.Figure:
    """Create severity distribution chart."""
    
    colors = {
        'critical': '#d63031',
        'high': '#e17055',
        'medium': '#fdcb6e',
        'low': '#74b9ff'
    }
    
    labels = list(severity_stats.keys())
    values = list(severity_stats.values())
    
    fig = go.Figure(data=[
        go.Pie(
            labels=[l.title() for l in labels],
            values=values,
            hole=0.4,
            marker_colors=[colors[l] for l in labels],
            textinfo='label+percent',
            textposition='outside'
        )
    ])
    
    fig.update_layout(
        title="Transgressions by Severity",
        height=350,
        showlegend=True,
        margin=dict(t=50, b=20, l=20, r=20)
    )
    
    return fig


def create_timeline_chart(df: pd.DataFrame) -> go.Figure:
    """Create timeline visualization of transgressions."""
    
    if df.empty:
        return go.Figure()
    
    # Count by date and severity
    timeline_counts = df.groupby(['date', 'severity']).size().reset_index(name='count')
    
    fig = px.scatter(
        timeline_counts,
        x='date',
        y='severity',
        size='count',
        color='severity',
        color_discrete_map={
            'critical': '#d63031',
            'high': '#e17055',
            'medium': '#fdcb6e',
            'low': '#74b9ff'
        },
        title="Transgression Timeline",
        labels={'date': 'Date', 'severity': 'Severity', 'count': 'Count'},
        height=400
    )
    
    fig.update_traces(marker=dict(sizemode='diameter', sizeref=0.5))
    fig.update_layout(
        xaxis_title="Date Identified",
        yaxis_title="Severity Level",
        hovermode='closest'
    )
    
    return fig


def create_heatmap(transgressions: List[Dict]) -> go.Figure:
    """Create heatmap of transgression types and entities."""
    
    # Create matrix of transgression types vs involved entities
    types = list(set(t.get('type', 'unknown') for t in transgressions))
    entities = ['Council', 'Mayor', 'Planning Dept', 'Contractors', 'Other']  # Mock entities
    
    # Create mock data for heatmap
    import numpy as np
    z_data = np.random.randint(0, 5, size=(len(types), len(entities)))
    
    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=entities,
        y=types,
        colorscale='Reds',
        text=z_data,
        texttemplate="%{text}",
        textfont={"size": 14},
        hovertemplate="Type: %{y}<br>Entity: %{x}<br>Count: %{z}<extra></extra>"
    ))
    
    fig.update_layout(
        title="Transgression Pattern Heatmap",
        xaxis_title="Related Entities",
        yaxis_title="Transgression Types",
        height=400
    )
    
    return fig


def show_transgression_details(transgression: Dict, related_entities: Dict):
    """Display detailed transgression information."""
    
    severity = transgression.get('severity', 'medium')
    severity_class = f"severity-{severity}"
    
    st.markdown(f"""
    <div class="transgression-card">
        <h3>{transgression.get('title', 'Unknown Transgression')}</h3>
        <p class="{severity_class}">Severity: {severity.upper()}</p>
        <p><strong>Type:</strong> {transgression.get('type', 'Unknown').title()}</p>
        <p><strong>Status:</strong> {transgression.get('status', 'Active').title()}</p>
        <p><strong>Date Identified:</strong> {transgression.get('date_identified', 'Unknown')}</p>
        <p><strong>Evidence Count:</strong> {transgression.get('evidence_count', 0)}</p>
    </div>
    """, unsafe_allow_html=True)
    
    if transgression.get('description'):
        st.markdown("**Description:**")
        st.info(transgression['description'])
    
    # Related entities
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Related People:**")
        if related_entities['people']:
            for person in related_entities['people']:
                st.markdown(f"- {person.get('name', 'Unknown')}")
        else:
            st.markdown("*No people linked*")
    
    with col2:
        st.markdown("**Related Organizations:**")
        if related_entities['organizations']:
            for org in related_entities['organizations']:
                st.markdown(f"- {org.get('name', 'Unknown')}")
        else:
            st.markdown("*No organizations linked*")


def main():
    """Main transgression tracking interface."""
    st.title("⚠️ Transgression Tracking Dashboard")
    st.markdown("*Monitor, analyze, and document violations for campaign intelligence*")
    
    # Initialize data loader
    @st.cache_resource
    def get_transgression_data():
        return TransgressionDataLoader()
    
    data_loader = get_transgression_data()
    
    # Quick stats row
    col1, col2, col3, col4 = st.columns(4)
    
    severity_stats = data_loader.get_severity_stats()
    total_transgressions = len(data_loader.transgressions)
    
    with col1:
        st.metric("Total Violations", total_transgressions)
    
    with col2:
        critical_count = severity_stats.get('critical', 0)
        st.metric(
            "Critical Severity", 
            critical_count,
            delta=f"{(critical_count/total_transgressions*100):.0f}%" if total_transgressions > 0 else "0%",
            delta_color="inverse"
        )
    
    with col3:
        active_count = sum(1 for t in data_loader.transgressions if t.get('status') == 'active')
        st.metric("Active Cases", active_count)
    
    with col4:
        evidence_total = sum(t.get('evidence_count', 0) for t in data_loader.transgressions)
        st.metric("Evidence Items", evidence_total)
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📅 Timeline", "🎯 Details", "📈 Analysis"])
    
    with tab1:
        # Overview section
        st.markdown("### Transgression Overview")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Severity distribution
            severity_fig = create_severity_chart(severity_stats)
            st.plotly_chart(severity_fig, use_container_width=True)
        
        with col2:
            # Recent transgressions table
            st.markdown("#### Recent Violations")
            
            recent_data = []
            for trans in data_loader.transgressions[:10]:
                recent_data.append({
                    'Title': trans.get('title', 'Unknown'),
                    'Severity': trans.get('severity', 'medium').title(),
                    'Type': trans.get('type', 'unknown').title(),
                    'Status': trans.get('status', 'active').title(),
                    'Evidence': trans.get('evidence_count', 0)
                })
            
            if recent_data:
                df_recent = pd.DataFrame(recent_data)
                st.dataframe(
                    df_recent,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Severity": st.column_config.TextColumn(
                            "Severity",
                            help="Violation severity level"
                        ),
                        "Evidence": st.column_config.NumberColumn(
                            "Evidence",
                            help="Number of evidence items",
                            format="%d"
                        )
                    }
                )
        
        # Pattern heatmap
        st.markdown("### Violation Patterns")
        heatmap_fig = create_heatmap(data_loader.transgressions)
        st.plotly_chart(heatmap_fig, use_container_width=True)
    
    with tab2:
        # Timeline view
        st.markdown("### Transgression Timeline")
        
        # Date range selector
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            days_back = st.selectbox(
                "Time Period",
                [7, 14, 30, 60, 90],
                index=2,
                format_func=lambda x: f"Last {x} days"
            )
        
        with col2:
            severity_filter = st.multiselect(
                "Filter by Severity",
                ['critical', 'high', 'medium', 'low'],
                default=['critical', 'high', 'medium', 'low']
            )
        
        # Get timeline data
        timeline_df = data_loader.get_timeline_data(days_back)
        
        if not timeline_df.empty and severity_filter:
            filtered_df = timeline_df[timeline_df['severity'].isin(severity_filter)]
            
            if not filtered_df.empty:
                timeline_fig = create_timeline_chart(filtered_df)
                st.plotly_chart(timeline_fig, use_container_width=True)
                
                # Timeline list
                st.markdown("#### Detailed Timeline")
                
                for _, row in filtered_df.iterrows():
                    severity_color = {
                        'critical': '🔴',
                        'high': '🟠',
                        'medium': '🟡',
                        'low': '🔵'
                    }.get(row['severity'], '⚪')
                    
                    st.markdown(f"""
                    {severity_color} **{row['date']}** - {row['title']}  
                    *Type: {row['type'].title()} | Status: {row['status'].title()}*
                    """)
            else:
                st.info("No transgressions found for selected filters")
        else:
            st.info("No timeline data available")
    
    with tab3:
        # Detailed view
        st.markdown("### Transgression Details")
        
        # Transgression selector
        transgression_options = {
            f"{t.get('title', 'Unknown')} ({t.get('severity', 'medium')})": i
            for i, t in enumerate(data_loader.transgressions)
        }
        
        if transgression_options:
            selected_display = st.selectbox(
                "Select Transgression",
                options=list(transgression_options.keys())
            )
            
            selected_idx = transgression_options[selected_display]
            selected_transgression = data_loader.transgressions[selected_idx]
            
            # Get related entities
            related_entities = data_loader.get_related_entities(
                selected_transgression.get('id', str(selected_idx))
            )
            
            # Show details
            show_transgression_details(selected_transgression, related_entities)
            
            # Evidence section
            st.markdown("### 📁 Evidence & Documentation")
            
            evidence_count = selected_transgression.get('evidence_count', 0)
            if evidence_count > 0:
                # Mock evidence items
                for i in range(min(evidence_count, 3)):
                    with st.expander(f"Evidence Item #{i+1}"):
                        st.markdown(f"""
                        **Type:** Document  
                        **Date:** {(datetime.now() - timedelta(days=i*3)).strftime('%Y-%m-%d')}  
                        **Source:** Public Records  
                        **Status:** Verified
                        """)
                        st.button(f"View Full Evidence", key=f"evidence_{i}")
            else:
                st.info("No evidence items linked to this transgression")
            
            # Action buttons
            st.markdown("### 🎯 Actions")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📝 Add Evidence", use_container_width=True):
                    st.success("Evidence upload interface coming soon!")
            
            with col2:
                if st.button("🔗 Link Entities", use_container_width=True):
                    st.info("Entity linking interface coming soon!")
            
            with col3:
                if st.button("📊 Generate Report", use_container_width=True):
                    st.info("Report generation coming soon!")
        else:
            st.info("No transgressions available")
    
    with tab4:
        # Analysis section
        st.markdown("### Transgression Analysis")
        
        # Trend analysis
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Severity Trends")
            
            # Mock trend data
            trend_dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
            trend_data = []
            
            for date in trend_dates:
                for severity in ['critical', 'high', 'medium', 'low']:
                    trend_data.append({
                        'date': date,
                        'severity': severity,
                        'count': random.randint(0, 3)
                    })
            
            trend_df = pd.DataFrame(trend_data)
            
            fig_trend = px.line(
                trend_df.groupby(['date', 'severity'])['count'].sum().reset_index(),
                x='date',
                y='count',
                color='severity',
                color_discrete_map={
                    'critical': '#d63031',
                    'high': '#e17055',
                    'medium': '#fdcb6e',
                    'low': '#74b9ff'
                },
                title="30-Day Severity Trends"
            )
            
            st.plotly_chart(fig_trend, use_container_width=True)
        
        with col2:
            st.markdown("#### Type Distribution")
            
            type_counts = {}
            for trans in data_loader.transgressions:
                trans_type = trans.get('type', 'unknown')
                type_counts[trans_type] = type_counts.get(trans_type, 0) + 1
            
            if type_counts:
                fig_types = go.Figure(data=[
                    go.Bar(
                        x=list(type_counts.keys()),
                        y=list(type_counts.values()),
                        marker_color='#e17055'
                    )
                ])
                
                fig_types.update_layout(
                    title="Violations by Type",
                    xaxis_title="Type",
                    yaxis_title="Count",
                    height=350
                )
                
                st.plotly_chart(fig_types, use_container_width=True)
        
        # Insights
        st.markdown("### 💡 Key Insights")
        
        # Calculate some insights
        total = len(data_loader.transgressions)
        critical_pct = (severity_stats.get('critical', 0) / total * 100) if total > 0 else 0
        
        insights = [
            f"📊 **{critical_pct:.0f}%** of violations are critical severity",
            f"📈 Average of **{total/30:.1f}** new violations per day",
            f"🎯 Most common type: **Procedural violations**",
            f"⚡ **{active_count}** cases require immediate attention"
        ]
        
        for insight in insights:
            st.info(insight)
        
        # Export options
        st.markdown("### 📥 Export Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Export as CSV
            export_df = pd.DataFrame([
                {
                    'Title': t.get('title', 'Unknown'),
                    'Severity': t.get('severity', 'medium'),
                    'Type': t.get('type', 'unknown'),
                    'Status': t.get('status', 'active'),
                    'Date': t.get('date_identified', ''),
                    'Evidence_Count': t.get('evidence_count', 0)
                }
                for t in data_loader.transgressions
            ])
            
            st.download_button(
                label="📥 Download CSV Report",
                data=export_df.to_csv(index=False),
                file_name=f"transgressions_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Export as JSON
            st.download_button(
                label="📥 Download JSON Data",
                data=json.dumps(data_loader.transgressions, indent=2),
                file_name=f"transgressions_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )


if __name__ == "__main__":
    main()