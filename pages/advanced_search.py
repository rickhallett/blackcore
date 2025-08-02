"""Advanced Search Interface for Nassau Campaign Intelligence."""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
import re
from collections import defaultdict
import plotly.express as px

# Page config
st.set_page_config(
    page_title="Advanced Search - Nassau Intelligence",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS for search interface
st.markdown("""
<style>
    .search-result {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }
    .search-result:hover {
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }
    .filter-chip {
        background: #e3f2fd;
        padding: 0.25rem 0.75rem;
        border-radius: 16px;
        font-size: 0.875rem;
        display: inline-block;
        margin: 0.25rem;
    }
    .search-stats {
        background: #e8f5e9;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .highlight {
        background-color: #ffeb3b;
        padding: 0 2px;
    }
</style>
""", unsafe_allow_html=True)


class AdvancedSearchEngine:
    """Advanced search engine with filtering and ranking."""
    
    def __init__(self):
        self.data_path = Path("blackcore/models/json")
        self.entities = []
        self.entity_index = {}
        self.search_history = []
        self.load_all_entities()
        self.build_search_index()
    
    def load_all_entities(self):
        """Load all entities from JSON files."""
        entity_files = {
            "people": "people_places.json",
            "organizations": "organizations_bodies.json",
            "tasks": "actionable_tasks.json",
            "events": "places_events.json",
            "documents": "documents_evidence.json",
            "transgressions": "identified_transgressions.json",
            "transcripts": "intelligence_transcripts.json"
        }
        
        for entity_type, filename in entity_files.items():
            file_path = self.data_path / filename
            if file_path.exists():
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    key = list(data.keys())[0]
                    for item in data.get(key, []):
                        # Standardize entity format
                        entity = {
                            'id': item.get('id', f"{entity_type}_{len(self.entities)}"),
                            'type': entity_type,
                            'title': item.get('name', item.get('title', 'Unknown')),
                            'data': item,
                            'searchable_text': self._create_searchable_text(item),
                            'created_date': item.get('created_date', 
                                (datetime.now() - timedelta(days=len(self.entities) % 30)).isoformat())
                        }
                        self.entities.append(entity)
    
    def _create_searchable_text(self, item: Dict) -> str:
        """Create searchable text from entity data."""
        text_parts = []
        
        # Add all string values
        for key, value in item.items():
            if isinstance(value, str):
                text_parts.append(value.lower())
            elif isinstance(value, list):
                for v in value:
                    if isinstance(v, str):
                        text_parts.append(v.lower())
        
        return ' '.join(text_parts)
    
    def build_search_index(self):
        """Build inverted index for fast searching."""
        for i, entity in enumerate(self.entities):
            # Tokenize searchable text
            tokens = re.findall(r'\w+', entity['searchable_text'].lower())
            
            # Add to index
            for token in set(tokens):
                if token not in self.entity_index:
                    self.entity_index[token] = []
                self.entity_index[token].append(i)
    
    def search(self, query: str, filters: Dict[str, Any]) -> List[Dict]:
        """Perform advanced search with filtering."""
        query_lower = query.lower()
        query_tokens = re.findall(r'\w+', query_lower)
        
        # Find matching entities
        matching_indices = set()
        
        if query_tokens:
            # Get entities matching any query token
            for token in query_tokens:
                if token in self.entity_index:
                    matching_indices.update(self.entity_index[token])
        else:
            # If no query, include all entities
            matching_indices = set(range(len(self.entities)))
        
        # Apply filters
        results = []
        for idx in matching_indices:
            entity = self.entities[idx]
            
            # Type filter
            if filters.get('entity_types') and entity['type'] not in filters['entity_types']:
                continue
            
            # Date filter
            if filters.get('date_from'):
                entity_date = datetime.fromisoformat(entity['created_date'].replace('Z', '+00:00'))
                if entity_date.date() < filters['date_from']:
                    continue
            
            if filters.get('date_to'):
                entity_date = datetime.fromisoformat(entity['created_date'].replace('Z', '+00:00'))
                if entity_date.date() > filters['date_to']:
                    continue
            
            # Property filters
            if filters.get('property_filters'):
                skip = False
                for prop, value in filters['property_filters'].items():
                    if prop in entity['data']:
                        if str(entity['data'][prop]).lower() != str(value).lower():
                            skip = True
                            break
                if skip:
                    continue
            
            # Calculate relevance score
            score = self._calculate_relevance(entity, query_tokens)
            
            results.append({
                'entity': entity,
                'score': score,
                'matched_terms': self._get_matched_terms(entity, query_tokens)
            })
        
        # Sort by relevance score
        results.sort(key=lambda x: x['score'], reverse=True)
        
        # Save to search history
        if query:
            self.search_history.append({
                'query': query,
                'timestamp': datetime.now(),
                'result_count': len(results),
                'filters': filters
            })
        
        return results
    
    def _calculate_relevance(self, entity: Dict, query_tokens: List[str]) -> float:
        """Calculate relevance score for entity."""
        score = 0.0
        
        searchable_text = entity['searchable_text']
        title_lower = entity['title'].lower()
        
        for token in query_tokens:
            # Title match (highest weight)
            if token in title_lower:
                score += 10.0
            
            # Count occurrences in searchable text
            occurrences = searchable_text.count(token)
            score += occurrences * 1.0
        
        # Boost recent entities slightly
        try:
            entity_date = datetime.fromisoformat(entity['created_date'].replace('Z', '+00:00'))
            days_old = (datetime.now().replace(tzinfo=entity_date.tzinfo) - entity_date).days
            if days_old < 7:
                score *= 1.2
            elif days_old < 30:
                score *= 1.1
        except:
            pass
        
        return score
    
    def _get_matched_terms(self, entity: Dict, query_tokens: List[str]) -> List[str]:
        """Get which query terms matched in the entity."""
        matched = []
        searchable_text = entity['searchable_text']
        
        for token in query_tokens:
            if token in searchable_text:
                matched.append(token)
        
        return matched
    
    def get_suggestions(self, partial_query: str) -> List[str]:
        """Get search suggestions based on partial query."""
        if not partial_query:
            return []
        
        partial_lower = partial_query.lower()
        suggestions = set()
        
        # Find matching tokens
        for token in self.entity_index.keys():
            if token.startswith(partial_lower):
                suggestions.add(token)
        
        # Find matching entity titles
        for entity in self.entities:
            if partial_lower in entity['title'].lower():
                suggestions.add(entity['title'])
        
        # Sort by relevance (shorter first)
        return sorted(list(suggestions), key=len)[:10]
    
    def get_facets(self, results: List[Dict]) -> Dict[str, Dict[str, int]]:
        """Get facet counts for search results."""
        facets = {
            'type': defaultdict(int),
            'status': defaultdict(int),
            'severity': defaultdict(int)
        }
        
        for result in results:
            entity = result['entity']
            
            # Type facet
            facets['type'][entity['type']] += 1
            
            # Status facet
            status = entity['data'].get('status', 'unknown')
            facets['status'][status] += 1
            
            # Severity facet (for transgressions)
            if entity['type'] == 'transgressions':
                severity = entity['data'].get('severity', 'unknown')
                facets['severity'][severity] += 1
        
        return {k: dict(v) for k, v in facets.items()}


def highlight_text(text: str, terms: List[str]) -> str:
    """Highlight search terms in text."""
    highlighted = text
    for term in terms:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        highlighted = pattern.sub(f'<span class="highlight">{term}</span>', highlighted)
    return highlighted


def show_search_result(result: Dict, idx: int):
    """Display a single search result."""
    entity = result['entity']
    score = result['score']
    matched_terms = result['matched_terms']
    
    # Type emoji
    type_emoji = {
        'people': '👤',
        'organizations': '🏢',
        'tasks': '✅',
        'events': '📅',
        'documents': '📄',
        'transgressions': '⚠️',
        'transcripts': '📝'
    }.get(entity['type'], '📌')
    
    with st.container():
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.markdown(f"""
            <div class="search-result">
                <h4>{type_emoji} {entity['title']}</h4>
                <p><strong>Type:</strong> {entity['type'].title()} | 
                   <strong>ID:</strong> {entity['id']} | 
                   <strong>Relevance:</strong> {score:.1f}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Show matched terms
            if matched_terms:
                st.caption(f"Matched: {', '.join(matched_terms)}")
        
        with col2:
            if st.button("View Details", key=f"view_{idx}"):
                st.session_state[f'show_details_{idx}'] = not st.session_state.get(f'show_details_{idx}', False)
        
        # Expandable details
        if st.session_state.get(f'show_details_{idx}', False):
            with st.expander("Full Details", expanded=True):
                # Show key properties
                important_props = ['description', 'status', 'role', 'affiliation', 'location']
                
                for prop in important_props:
                    if prop in entity['data'] and entity['data'][prop]:
                        value = entity['data'][prop]
                        if matched_terms:
                            value = highlight_text(str(value), matched_terms)
                        st.markdown(f"**{prop.title()}:** {value}", unsafe_allow_html=True)
                
                # Show all data
                st.json(entity['data'])


def main():
    """Main advanced search interface."""
    st.title("🔍 Advanced Campaign Intelligence Search")
    st.markdown("*Powerful search with filters, facets, and intelligent ranking*")
    
    # Initialize search engine
    @st.cache_resource
    def get_search_engine():
        return AdvancedSearchEngine()
    
    search_engine = get_search_engine()
    
    # Search interface
    st.markdown("### 🔎 Search Query")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        query = st.text_input(
            "Enter search terms",
            placeholder="Search for people, organizations, events, violations...",
            key="main_search",
            help="Use keywords to search across all intelligence data"
        )
    
    with col2:
        search_button = st.button("🔍 Search", type="primary", use_container_width=True)
    
    # Advanced filters in expander
    with st.expander("⚙️ Advanced Filters", expanded=False):
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        with filter_col1:
            entity_types = st.multiselect(
                "Entity Types",
                ['people', 'organizations', 'tasks', 'events', 'documents', 'transgressions', 'transcripts'],
                default=None,
                help="Filter by specific entity types"
            )
        
        with filter_col2:
            date_from = st.date_input(
                "From Date",
                value=None,
                max_value=datetime.now().date(),
                help="Filter by creation date"
            )
            
            date_to = st.date_input(
                "To Date",
                value=None,
                max_value=datetime.now().date(),
                help="Filter by creation date"
            )
        
        with filter_col3:
            # Property filters
            st.markdown("**Property Filters**")
            
            status_filter = st.selectbox(
                "Status",
                ["Any", "active", "inactive", "pending", "resolved"],
                index=0
            )
            
            severity_filter = st.selectbox(
                "Severity (Transgressions)",
                ["Any", "critical", "high", "medium", "low"],
                index=0
            )
    
    # Build filters
    filters = {
        'entity_types': entity_types if entity_types else None,
        'date_from': date_from,
        'date_to': date_to,
        'property_filters': {}
    }
    
    if status_filter != "Any":
        filters['property_filters']['status'] = status_filter
    
    if severity_filter != "Any":
        filters['property_filters']['severity'] = severity_filter
    
    # Perform search
    if search_button or query:
        with st.spinner("🔍 Searching intelligence database..."):
            results = search_engine.search(query, filters)
        
        # Search statistics
        st.markdown(f"""
        <div class="search-stats">
            Found <strong>{len(results)}</strong> results 
            {f'for "{query}"' if query else 'matching filters'}
        </div>
        """, unsafe_allow_html=True)
        
        if results:
            # Facets sidebar
            col1, col2 = st.columns([3, 1])
            
            with col2:
                st.markdown("### 📊 Result Breakdown")
                
                facets = search_engine.get_facets(results)
                
                # Type facet
                if facets['type']:
                    st.markdown("**By Type:**")
                    for entity_type, count in sorted(facets['type'].items(), 
                                                   key=lambda x: x[1], reverse=True):
                        st.caption(f"{entity_type.title()}: {count}")
                
                # Status facet
                if any(facets['status'].values()):
                    st.markdown("**By Status:**")
                    for status, count in sorted(facets['status'].items(), 
                                              key=lambda x: x[1], reverse=True):
                        if status != 'unknown':
                            st.caption(f"{status.title()}: {count}")
                
                # Export results
                st.markdown("### 💾 Export")
                
                export_data = []
                for result in results:
                    entity = result['entity']
                    export_data.append({
                        'id': entity['id'],
                        'type': entity['type'],
                        'title': entity['title'],
                        'score': result['score'],
                        'matched_terms': ', '.join(result['matched_terms'])
                    })
                
                df_export = pd.DataFrame(export_data)
                
                csv = df_export.to_csv(index=False)
                st.download_button(
                    "📥 Download Results (CSV)",
                    csv,
                    f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                    use_container_width=True
                )
            
            with col1:
                # Search results
                st.markdown("### 🔍 Search Results")
                
                # Pagination
                results_per_page = 10
                total_pages = (len(results) - 1) // results_per_page + 1
                
                if 'current_page' not in st.session_state:
                    st.session_state.current_page = 1
                
                # Page selector
                page_col1, page_col2, page_col3 = st.columns([1, 2, 1])
                
                with page_col2:
                    current_page = st.number_input(
                        "Page",
                        min_value=1,
                        max_value=total_pages,
                        value=st.session_state.current_page,
                        key="page_selector"
                    )
                    st.session_state.current_page = current_page
                
                # Show results for current page
                start_idx = (current_page - 1) * results_per_page
                end_idx = min(start_idx + results_per_page, len(results))
                
                for i, result in enumerate(results[start_idx:end_idx], start=start_idx):
                    show_search_result(result, i)
                
                # Pagination controls
                pag_col1, pag_col2, pag_col3 = st.columns([1, 2, 1])
                
                with pag_col1:
                    if current_page > 1:
                        if st.button("← Previous"):
                            st.session_state.current_page -= 1
                            st.rerun()
                
                with pag_col2:
                    st.caption(f"Page {current_page} of {total_pages}")
                
                with pag_col3:
                    if current_page < total_pages:
                        if st.button("Next →"):
                            st.session_state.current_page += 1
                            st.rerun()
        
        else:
            st.info("No results found. Try different search terms or adjust filters.")
    
    # Search suggestions
    if query and len(query) >= 2:
        suggestions = search_engine.get_suggestions(query)
        if suggestions:
            st.markdown("### 💡 Search Suggestions")
            
            suggestion_cols = st.columns(min(5, len(suggestions)))
            for i, suggestion in enumerate(suggestions[:5]):
                with suggestion_cols[i]:
                    if st.button(suggestion, key=f"sugg_{i}", use_container_width=True):
                        st.session_state.main_search = suggestion
                        st.rerun()
    
    # Recent searches
    if search_engine.search_history:
        with st.expander("🕐 Recent Searches"):
            for search in reversed(search_engine.search_history[-10:]):
                time_str = search['timestamp'].strftime("%H:%M")
                st.markdown(f"""
                **{search['query']}** - *{time_str}* ({search['result_count']} results)
                """)


if __name__ == "__main__":
    main()