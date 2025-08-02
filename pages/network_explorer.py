"""Entity Relationship Network Explorer for Nassau Campaign Intelligence."""

import streamlit as st
import plotly.graph_objects as go
import networkx as nx
import pandas as pd
from typing import Dict, List, Any, Optional, Set, Tuple
import json
from pathlib import Path
from datetime import datetime
import colorsys

# Page config
st.set_page_config(
    page_title="Network Explorer - Nassau Intelligence",
    page_icon="🕸️",
    layout="wide"
)

# Custom CSS for network visualization
st.markdown("""
<style>
    .entity-card {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        border-left: 4px solid #1f4e79;
    }
    .relationship-badge {
        background: #e3f2fd;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.875rem;
        display: inline-block;
        margin: 0.25rem;
    }
    .control-panel {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


class NetworkDataLoader:
    """Load and process network data from JSON files."""
    
    def __init__(self):
        self.data_path = Path("blackcore/models/json")
        self.entities = {}
        self.relationships = []
        self.load_all_data()
    
    def load_all_data(self):
        """Load all entity data from JSON files."""
        entity_files = {
            "people": "people_places.json",
            "organizations": "organizations_bodies.json",
            "events": "places_events.json",
            "transgressions": "identified_transgressions.json"
        }
        
        for entity_type, filename in entity_files.items():
            file_path = self.data_path / filename
            if file_path.exists():
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    # Extract entities from the first key
                    key = list(data.keys())[0]
                    for item in data.get(key, []):
                        entity_id = item.get('id', f"{entity_type}_{len(self.entities)}")
                        self.entities[entity_id] = {
                            'id': entity_id,
                            'name': item.get('name', item.get('title', 'Unknown')),
                            'type': entity_type,
                            'properties': item
                        }
        
        # Extract relationships from entity properties
        self._extract_relationships()
    
    def _extract_relationships(self):
        """Extract relationships from entity properties."""
        for entity_id, entity in self.entities.items():
            props = entity['properties']
            
            # Look for relation properties
            for key, value in props.items():
                if 'related' in key.lower() or 'associated' in key.lower():
                    if isinstance(value, list):
                        for related_id in value:
                            if related_id in self.entities:
                                self.relationships.append({
                                    'source': entity_id,
                                    'target': related_id,
                                    'type': key,
                                    'strength': 0.7
                                })
                    elif isinstance(value, str) and value in self.entities:
                        self.relationships.append({
                            'source': entity_id,
                            'target': value,
                            'type': key,
                            'strength': 0.7
                        })
    
    def get_subgraph(self, center_id: str, depth: int = 2) -> Tuple[Dict, List]:
        """Get subgraph around a specific entity."""
        if center_id not in self.entities:
            return {}, []
        
        # BFS to find nodes within depth
        visited = {center_id}
        current_level = {center_id}
        
        for _ in range(depth):
            next_level = set()
            for node in current_level:
                # Find connected nodes
                for rel in self.relationships:
                    if rel['source'] == node and rel['target'] not in visited:
                        next_level.add(rel['target'])
                        visited.add(rel['target'])
                    elif rel['target'] == node and rel['source'] not in visited:
                        next_level.add(rel['source'])
                        visited.add(rel['source'])
            current_level = next_level
        
        # Filter entities and relationships
        subgraph_entities = {eid: e for eid, e in self.entities.items() if eid in visited}
        subgraph_relationships = [
            r for r in self.relationships 
            if r['source'] in visited and r['target'] in visited
        ]
        
        return subgraph_entities, subgraph_relationships


def create_network_graph(entities: Dict, relationships: List, 
                        center_node: Optional[str] = None,
                        layout_type: str = "spring") -> go.Figure:
    """Create an interactive network graph using Plotly."""
    
    # Create NetworkX graph
    G = nx.Graph()
    
    # Add nodes
    for entity_id, entity in entities.items():
        G.add_node(entity_id, **entity)
    
    # Add edges
    for rel in relationships:
        G.add_edge(rel['source'], rel['target'], 
                  type=rel['type'], strength=rel['strength'])
    
    # Calculate layout
    if layout_type == "spring":
        pos = nx.spring_layout(G, k=2, iterations=50)
    elif layout_type == "circular":
        pos = nx.circular_layout(G)
    elif layout_type == "kamada_kawai":
        pos = nx.kamada_kawai_layout(G)
    else:
        pos = nx.spring_layout(G)
    
    # Create edge traces
    edge_traces = []
    for edge in G.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        
        edge_trace = go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            mode='lines',
            line=dict(width=edge[2].get('strength', 0.5) * 3, color='#888'),
            hoverinfo='none',
            showlegend=False
        )
        edge_traces.append(edge_trace)
    
    # Create node traces by type
    node_traces = []
    type_colors = {
        'people': '#2E86AB',
        'organizations': '#A23B72',
        'events': '#F18F01',
        'transgressions': '#C73E1D'
    }
    
    for entity_type, color in type_colors.items():
        node_x = []
        node_y = []
        node_text = []
        node_ids = []
        
        for node in G.nodes():
            if entities[node]['type'] == entity_type:
                x, y = pos[node]
                node_x.append(x)
                node_y.append(y)
                node_text.append(entities[node]['name'])
                node_ids.append(node)
        
        if node_x:  # Only create trace if there are nodes of this type
            # Highlight center node
            node_sizes = []
            for nid in node_ids:
                if nid == center_node:
                    node_sizes.append(30)
                else:
                    node_sizes.append(15)
            
            node_trace = go.Scatter(
                x=node_x,
                y=node_y,
                mode='markers+text',
                name=entity_type.title(),
                text=node_text,
                textposition="top center",
                textfont=dict(size=10),
                hoverinfo='text',
                hovertext=[f"{entities[nid]['name']}<br>Type: {entity_type}<br>ID: {nid}" 
                          for nid in node_ids],
                marker=dict(
                    size=node_sizes,
                    color=color,
                    line=dict(width=2, color='white')
                ),
                customdata=node_ids
            )
            node_traces.append(node_trace)
    
    # Create figure
    fig = go.Figure(data=edge_traces + node_traces)
    
    # Update layout
    fig.update_layout(
        title="Entity Relationship Network",
        showlegend=True,
        hovermode='closest',
        margin=dict(b=20, l=5, r=5, t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='white',
        height=600
    )
    
    return fig


def show_entity_details(entity: Dict):
    """Display detailed entity information."""
    st.markdown(f"### 🔍 Entity Details: {entity['name']}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**Type:** {entity['type'].title()}")
        st.markdown(f"**ID:** {entity['id']}")
    
    # Show key properties
    with col2:
        props = entity['properties']
        important_props = ['status', 'role', 'affiliation', 'location']
        
        for prop in important_props:
            if prop in props and props[prop]:
                st.markdown(f"**{prop.title()}:** {props[prop]}")
    
    # Show description if available
    if 'description' in props and props['description']:
        st.markdown("**Description:**")
        st.info(props['description'])
    
    # Show all properties in expander
    with st.expander("📋 All Properties"):
        st.json(props)


def main():
    """Main network explorer interface."""
    st.title("🕸️ Entity Relationship Network Explorer")
    st.markdown("*Visualize connections between people, organizations, events, and transgressions*")
    
    # Initialize data loader
    @st.cache_resource
    def get_network_data():
        return NetworkDataLoader()
    
    network_data = get_network_data()
    
    # Sidebar controls
    with st.sidebar:
        st.markdown("### 🎛️ Network Controls")
        
        # Entity selector
        entity_options = {
            f"{e['name']} ({e['type']})": eid 
            for eid, e in network_data.entities.items()
        }
        
        selected_entity_display = st.selectbox(
            "Center Entity",
            options=list(entity_options.keys()),
            help="Select an entity to explore its network"
        )
        
        selected_entity_id = entity_options.get(selected_entity_display)
        
        # Depth control
        depth = st.slider(
            "Network Depth",
            min_value=1,
            max_value=4,
            value=2,
            help="How many relationship levels to show"
        )
        
        # Layout type
        layout_type = st.selectbox(
            "Layout Algorithm",
            ["spring", "circular", "kamada_kawai"],
            help="Different ways to arrange the network"
        )
        
        # Filter by entity type
        st.markdown("### 🔍 Filters")
        
        show_types = {}
        for entity_type in ['people', 'organizations', 'events', 'transgressions']:
            show_types[entity_type] = st.checkbox(
                f"Show {entity_type.title()}",
                value=True
            )
        
        # Relationship strength threshold
        min_strength = st.slider(
            "Min Relationship Strength",
            0.0, 1.0, 0.3,
            help="Hide weak relationships"
        )
    
    # Main content area
    if selected_entity_id and selected_entity_id in network_data.entities:
        # Get subgraph
        subgraph_entities, subgraph_relationships = network_data.get_subgraph(
            selected_entity_id, depth
        )
        
        # Apply filters
        filtered_entities = {
            eid: e for eid, e in subgraph_entities.items()
            if show_types.get(e['type'], True)
        }
        
        filtered_relationships = [
            r for r in subgraph_relationships
            if r['strength'] >= min_strength
            and r['source'] in filtered_entities
            and r['target'] in filtered_entities
        ]
        
        # Statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Entities", len(filtered_entities))
        with col2:
            st.metric("Relationships", len(filtered_relationships))
        with col3:
            direct_connections = len([
                r for r in filtered_relationships
                if r['source'] == selected_entity_id or r['target'] == selected_entity_id
            ])
            st.metric("Direct Connections", direct_connections)
        with col4:
            entity_types = set(e['type'] for e in filtered_entities.values())
            st.metric("Entity Types", len(entity_types))
        
        # Network visualization
        st.markdown("### 🕸️ Network Visualization")
        
        if filtered_entities:
            fig = create_network_graph(
                filtered_entities,
                filtered_relationships,
                center_node=selected_entity_id,
                layout_type=layout_type
            )
            
            # Make it interactive
            selected_points = st.plotly_chart(
                fig,
                use_container_width=True,
                key="network_graph"
            )
            
            # Entity details section
            center_entity = network_data.entities[selected_entity_id]
            show_entity_details(center_entity)
            
            # Related entities table
            st.markdown("### 📊 Connected Entities")
            
            # Build connections data
            connections = []
            for rel in filtered_relationships:
                if rel['source'] == selected_entity_id:
                    connected_id = rel['target']
                    direction = "→"
                elif rel['target'] == selected_entity_id:
                    connected_id = rel['source']
                    direction = "←"
                else:
                    continue
                
                if connected_id in filtered_entities:
                    connections.append({
                        'Name': filtered_entities[connected_id]['name'],
                        'Type': filtered_entities[connected_id]['type'].title(),
                        'Relationship': rel['type'].replace('_', ' ').title(),
                        'Direction': direction,
                        'Strength': f"{rel['strength']:.0%}"
                    })
            
            if connections:
                df_connections = pd.DataFrame(connections)
                st.dataframe(
                    df_connections,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No direct connections found within current filters")
            
            # Export options
            st.markdown("### 💾 Export Network Data")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Export as JSON
                export_data = {
                    'entities': list(filtered_entities.values()),
                    'relationships': filtered_relationships,
                    'center_entity': selected_entity_id,
                    'export_date': datetime.now().isoformat()
                }
                
                st.download_button(
                    label="📥 Download Network (JSON)",
                    data=json.dumps(export_data, indent=2),
                    file_name=f"network_{selected_entity_id}_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json"
                )
            
            with col2:
                # Export as CSV (entities)
                df_entities = pd.DataFrame([
                    {
                        'ID': e['id'],
                        'Name': e['name'],
                        'Type': e['type']
                    }
                    for e in filtered_entities.values()
                ])
                
                st.download_button(
                    label="📥 Download Entities (CSV)",
                    data=df_entities.to_csv(index=False),
                    file_name=f"entities_{selected_entity_id}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        else:
            st.warning("No entities found matching current filters")
    else:
        st.info("👆 Select an entity from the sidebar to explore its network")
        
        # Show overall network statistics
        st.markdown("### 📊 Network Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Entities", len(network_data.entities))
        
        with col2:
            st.metric("Total Relationships", len(network_data.relationships))
        
        with col3:
            people_count = sum(1 for e in network_data.entities.values() if e['type'] == 'people')
            st.metric("People", people_count)
        
        with col4:
            org_count = sum(1 for e in network_data.entities.values() if e['type'] == 'organizations')
            st.metric("Organizations", org_count)


if __name__ == "__main__":
    main()