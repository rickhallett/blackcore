"""Query suggestion implementation for improved user experience.

This module provides intelligent query suggestions based on partial input,
search history, and available data.
"""

import re
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass, field
import math

from .interfaces import QuerySuggester, QuerySuggestion


class IntelligentQuerySuggester:
    """Advanced query suggestion system with learning capabilities."""
    
    def __init__(self):
        self.query_templates = self._build_query_templates()
        self.common_queries = self._load_common_queries()
        self.query_history = defaultdict(int)
        self.selection_history = defaultdict(lambda: defaultdict(int))
        self.field_values_cache = {}
    
    def suggest(
        self,
        partial_query: str,
        search_history: List[str],
        available_data: Optional[List[Dict[str, Any]]] = None
    ) -> List[QuerySuggestion]:
        """Generate query suggestions."""
        if not partial_query:
            return self._get_starter_suggestions()
        
        suggestions = []
        partial_lower = partial_query.lower().strip()
        
        # 1. Template-based suggestions
        template_suggestions = self._generate_template_suggestions(partial_lower)
        suggestions.extend(template_suggestions)
        
        # 2. History-based suggestions
        history_suggestions = self._generate_history_suggestions(
            partial_lower, search_history
        )
        suggestions.extend(history_suggestions)
        
        # 3. Data-driven suggestions
        if available_data:
            data_suggestions = self._generate_data_suggestions(
                partial_lower, available_data
            )
            suggestions.extend(data_suggestions)
        
        # 4. Completion suggestions
        completion_suggestions = self._generate_completions(partial_lower)
        suggestions.extend(completion_suggestions)
        
        # Remove duplicates and sort by score
        unique_suggestions = self._deduplicate_suggestions(suggestions)
        unique_suggestions.sort(key=lambda s: s.score, reverse=True)
        
        return unique_suggestions[:10]  # Top 10 suggestions
    
    def learn_from_selection(
        self,
        query: str,
        selected_suggestion: str,
        results_clicked: List[str]
    ) -> None:
        """Learn from user's suggestion selection."""
        # Update query history
        self.query_history[selected_suggestion] += 1
        
        # Update selection history (what was selected after typing what)
        self.selection_history[query.lower()][selected_suggestion] += 1
        
        # Update success metrics based on clicked results
        if results_clicked:
            # This suggestion led to successful results
            self.query_history[selected_suggestion] += len(results_clicked)
    
    def _get_starter_suggestions(self) -> List[QuerySuggestion]:
        """Get suggestions for empty query."""
        starters = [
            QuerySuggestion(
                text="Find all people",
                score=0.9,
                category="entity_search",
                explanation="Search for all people in the system",
                example_results=100
            ),
            QuerySuggestion(
                text="Show recent tasks",
                score=0.85,
                category="entity_search",
                explanation="Display recently created or updated tasks",
                example_results=50
            ),
            QuerySuggestion(
                text="List organizations",
                score=0.8,
                category="entity_search",
                explanation="Show all organizations",
                example_results=25
            ),
            QuerySuggestion(
                text="Find relationships between",
                score=0.75,
                category="relationship_search",
                explanation="Discover connections between entities",
                example_results=0
            )
        ]
        
        # Boost suggestions based on history
        for suggestion in starters:
            if suggestion.text in self.query_history:
                suggestion.score *= (1 + math.log(self.query_history[suggestion.text] + 1) / 10)
        
        return starters
    
    def _generate_template_suggestions(self, partial: str) -> List[QuerySuggestion]:
        """Generate suggestions from templates."""
        suggestions = []
        
        for template, config in self.query_templates.items():
            if self._matches_template(partial, template):
                # Generate suggestion from template
                suggestion_text = self._complete_template(partial, template)
                
                suggestion = QuerySuggestion(
                    text=suggestion_text,
                    score=config["base_score"] * self._calculate_match_score(partial, template),
                    category=config["category"],
                    explanation=config["explanation"],
                    example_results=config.get("example_results", 0)
                )
                suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_history_suggestions(
        self,
        partial: str,
        search_history: List[str]
    ) -> List[QuerySuggestion]:
        """Generate suggestions from search history."""
        suggestions = []
        
        # Check recent history
        for historical_query in search_history[-20:]:  # Last 20 queries
            if historical_query.lower().startswith(partial):
                # Calculate score based on recency and frequency
                recency_score = 0.8  # Could decay based on position in history
                frequency_score = math.log(self.query_history.get(historical_query, 1) + 1) / 10
                
                suggestion = QuerySuggestion(
                    text=historical_query,
                    score=recency_score + frequency_score,
                    category="history",
                    explanation="Previously searched",
                    example_results=0
                )
                suggestions.append(suggestion)
        
        # Check learned selections
        if partial in self.selection_history:
            for selected, count in self.selection_history[partial].most_common(5):
                suggestion = QuerySuggestion(
                    text=selected,
                    score=0.9 + math.log(count + 1) / 10,
                    category="learned",
                    explanation="Frequently selected after this input",
                    example_results=0
                )
                suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_data_suggestions(
        self,
        partial: str,
        available_data: List[Dict[str, Any]]
    ) -> List[QuerySuggestion]:
        """Generate suggestions based on available data."""
        suggestions = []
        
        # Extract field values if not cached
        if not self.field_values_cache:
            self._build_field_values_cache(available_data)
        
        # Suggest based on actual values
        words = partial.split()
        last_word = words[-1] if words else ""
        
        for field, values in self.field_values_cache.items():
            for value, count in values.most_common(10):
                if str(value).lower().startswith(last_word):
                    # Build suggestion
                    suggestion_text = " ".join(words[:-1] + [str(value)])
                    
                    suggestion = QuerySuggestion(
                        text=suggestion_text,
                        score=0.7 + (count / len(available_data)),
                        category="data_driven",
                        explanation=f"Common {field} value",
                        example_results=count
                    )
                    suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_completions(self, partial: str) -> List[QuerySuggestion]:
        """Generate word completions."""
        suggestions = []
        
        # Common query words
        completions = {
            "find": ["find all", "find people", "find organizations", "find related"],
            "show": ["show me", "show all", "show recent", "show top"],
            "list": ["list all", "list people", "list tasks", "list by"],
            "get": ["get all", "get latest", "get by", "get with"],
            "sort": ["sort by name", "sort by date", "sort by priority"],
            "filter": ["filter by status", "filter by type", "filter by date"],
            "with": ["with status", "with priority", "with their", "with related"],
            "created": ["created today", "created this week", "created by", "created after"],
            "updated": ["updated today", "updated recently", "updated by", "updated after"]
        }
        
        words = partial.split()
        if words:
            last_word = words[-1]
            
            for key, values in completions.items():
                if key.startswith(last_word):
                    for completion in values:
                        suggestion_text = " ".join(words[:-1] + [completion])
                        
                        suggestion = QuerySuggestion(
                            text=suggestion_text,
                            score=0.6,
                            category="completion",
                            explanation="Common query pattern",
                            example_results=0
                        )
                        suggestions.append(suggestion)
        
        return suggestions
    
    def _build_query_templates(self) -> Dict[str, Dict[str, Any]]:
        """Build query template patterns."""
        return {
            "find all {entity_type}": {
                "pattern": r"find all \w*",
                "base_score": 0.9,
                "category": "entity_search",
                "explanation": "Search for all entities of a type",
                "example_results": 50
            },
            "find {entity_type} with {field} = {value}": {
                "pattern": r"find \w+ with \w+ = \w*",
                "base_score": 0.85,
                "category": "filtered_search",
                "explanation": "Search with specific criteria",
                "example_results": 10
            },
            "show {entity_type} created {time_period}": {
                "pattern": r"show \w+ created \w*",
                "base_score": 0.8,
                "category": "temporal_search",
                "explanation": "Search by creation time",
                "example_results": 20
            },
            "{entity_type} related to {entity}": {
                "pattern": r"\w+ related to \w*",
                "base_score": 0.75,
                "category": "relationship_search",
                "explanation": "Find related entities",
                "example_results": 15
            },
            "top {n} {entity_type} by {field}": {
                "pattern": r"top \d* \w+ by \w*",
                "base_score": 0.7,
                "category": "ranked_search",
                "explanation": "Get top results by a criteria",
                "example_results": 10
            }
        }
    
    def _load_common_queries(self) -> List[str]:
        """Load common query patterns."""
        return [
            "find all people",
            "find all organizations",
            "find all tasks",
            "show recent documents",
            "list open tasks",
            "find people named",
            "show my tasks",
            "find organizations in",
            "list events this week",
            "show completed tasks",
            "find related entities",
            "show high priority tasks"
        ]
    
    def _matches_template(self, partial: str, template: str) -> bool:
        """Check if partial query matches a template."""
        # Convert template to regex pattern
        pattern = template.replace("{entity_type}", r"\w*")
        pattern = pattern.replace("{field}", r"\w*")
        pattern = pattern.replace("{value}", r"\w*")
        pattern = pattern.replace("{entity}", r"\w*")
        pattern = pattern.replace("{time_period}", r"\w*")
        pattern = pattern.replace("{n}", r"\d*")
        
        return bool(re.match(pattern, partial))
    
    def _complete_template(self, partial: str, template: str) -> str:
        """Complete a template based on partial input."""
        # Simple completion - in production, this would be smarter
        if partial.endswith(" "):
            return partial + "..."
        
        # Find the next word in template
        template_words = template.split()
        partial_words = partial.split()
        
        if len(partial_words) < len(template_words):
            next_word = template_words[len(partial_words)]
            if next_word.startswith("{"):
                # Placeholder - suggest common values
                if "entity_type" in next_word:
                    return partial + "people"
                elif "field" in next_word:
                    return partial + "name"
                elif "value" in next_word:
                    return partial + "active"
            else:
                return partial + next_word
        
        return partial
    
    def _calculate_match_score(self, partial: str, template: str) -> float:
        """Calculate how well partial matches template."""
        # Simple scoring based on completion percentage
        partial_words = len(partial.split())
        template_words = len(template.split())
        
        return min(partial_words / template_words, 1.0)
    
    def _build_field_values_cache(self, data: List[Dict[str, Any]]) -> None:
        """Build cache of common field values."""
        self.field_values_cache = defaultdict(Counter)
        
        for item in data:
            for field, value in item.items():
                if isinstance(value, (str, int)) and field not in ["id", "created_at", "updated_at"]:
                    self.field_values_cache[field][value] += 1
    
    def _deduplicate_suggestions(
        self,
        suggestions: List[QuerySuggestion]
    ) -> List[QuerySuggestion]:
        """Remove duplicate suggestions, keeping highest score."""
        seen = {}
        unique = []
        
        for suggestion in suggestions:
            text_lower = suggestion.text.lower()
            if text_lower not in seen or suggestion.score > seen[text_lower].score:
                seen[text_lower] = suggestion
        
        return list(seen.values())