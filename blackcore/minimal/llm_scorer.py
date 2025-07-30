"""
LLM-Based Similarity Scorer for Intelligent Deduplication

Uses Claude 3.5 Haiku with function calling to provide intelligent
entity matching without hardcoded rules or mappings.
"""

import json
import hashlib
from typing import Dict, Tuple, Optional, Any, List
from datetime import datetime, timedelta

try:
    import anthropic
except ImportError:
    anthropic = None


class LLMScorerCache:
    """Simple in-memory cache for LLM scoring decisions."""

    def __init__(self, ttl_seconds: int = 3600):
        """Initialize cache with TTL in seconds."""
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.ttl = timedelta(seconds=ttl_seconds)

    def get_cache_key(self, entity1: Dict, entity2: Dict, entity_type: str) -> str:
        """Generate stable cache key for entity pair."""
        # Normalize and sort entities to ensure consistent ordering
        e1_str = json.dumps({"type": entity_type, **entity1}, sort_keys=True)
        e2_str = json.dumps({"type": entity_type, **entity2}, sort_keys=True)
        combined = "".join(sorted([e1_str, e2_str]))
        return hashlib.md5(combined.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return value
            else:
                # Expired, remove it
                del self.cache[key]
        return None

    def set(self, key: str, value: Any):
        """Set cache value with current timestamp."""
        self.cache[key] = (value, datetime.now())

    def clear_expired(self):
        """Remove all expired entries."""
        now = datetime.now()
        expired_keys = [
            key
            for key, (_, timestamp) in self.cache.items()
            if now - timestamp >= self.ttl
        ]
        for key in expired_keys:
            del self.cache[key]


class LLMScorer:
    """LLM-based similarity scoring for intelligent deduplication."""

    # Function calling tool definition
    SCORING_TOOL = {
        "name": "score_entity_match",
        "description": "Analyze two entities and determine if they represent the same real-world entity",
        "input_schema": {
            "type": "object",
            "properties": {
                "confidence_score": {
                    "type": "number",
                    "description": "Similarity score from 0-100",
                    "minimum": 0,
                    "maximum": 100,
                },
                "is_match": {
                    "type": "boolean",
                    "description": "Whether these entities represent the same real-world entity",
                },
                "match_reason": {
                    "type": "string",
                    "description": "Primary reason for match/non-match decision",
                },
                "supporting_evidence": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of specific evidence supporting the decision",
                },
                "analysis_dimensions": {
                    "type": "object",
                    "properties": {
                        "name_similarity": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100,
                        },
                        "temporal_proximity": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100,
                        },
                        "social_graph": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100,
                        },
                        "location_overlap": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100,
                        },
                        "communication_pattern": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100,
                        },
                        "professional_context": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100,
                        },
                        "behavioral_pattern": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100,
                        },
                        "linguistic_similarity": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100,
                        },
                    },
                    "description": "Individual dimension scores",
                },
            },
            "required": [
                "confidence_score",
                "is_match",
                "match_reason",
                "supporting_evidence",
            ],
        },
    }

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-haiku-20241022",
        cache_ttl: int = 3600,
        temperature: float = 0.1,
    ):
        """Initialize LLM scorer.

        Args:
            api_key: Anthropic API key
            model: Model to use (default: Claude 3.5 Haiku)
            cache_ttl: Cache TTL in seconds (default: 1 hour)
            temperature: LLM temperature for consistency (default: 0.1)
        """
        if anthropic is None:
            raise ImportError(
                "anthropic package required for LLM scorer. Install with: pip install anthropic"
            )

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.cache = LLMScorerCache(ttl_seconds=cache_ttl)

    def score_entities(
        self,
        entity1: Dict,
        entity2: Dict,
        entity_type: str = "person",
        context: Optional[Dict] = None,
    ) -> Tuple[float, str, Dict]:
        """Score similarity between two entities using LLM analysis.

        Args:
            entity1: First entity properties
            entity2: Second entity properties
            entity_type: Type of entity (person, organization)
            context: Additional context for comparison

        Returns:
            Tuple of (score 0-100, match_reason, additional_details)
        """
        # Check cache first
        cache_key = self.cache.get_cache_key(entity1, entity2, entity_type)
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Build and send request to LLM
        prompt = self._build_prompt(entity1, entity2, entity_type, context or {})

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}],
                tools=[self.SCORING_TOOL],
            )

            # Process response
            result = self._process_response(response)

            # Cache result
            self.cache.set(cache_key, result)

            return result

        except Exception as e:
            # On error, return low confidence score
            print(f"LLM scoring error: {e}")
            return 0.0, f"LLM error: {str(e)}", {"error": True}

    def score_batch(
        self, entity_pairs: List[Tuple[Dict, Dict, str]], batch_size: int = 5
    ) -> List[Tuple[float, str, Dict]]:
        """Score multiple entity pairs efficiently.

        Args:
            entity_pairs: List of (entity1, entity2, entity_type) tuples
            batch_size: Number of comparisons per LLM request

        Returns:
            List of scoring results
        """
        results = []

        # Process in batches
        for i in range(0, len(entity_pairs), batch_size):
            batch = entity_pairs[i : i + batch_size]

            # Check cache for each pair
            batch_to_process = []
            for entity1, entity2, entity_type in batch:
                cache_key = self.cache.get_cache_key(entity1, entity2, entity_type)
                cached = self.cache.get(cache_key)
                if cached is not None:
                    results.append(cached)
                else:
                    batch_to_process.append((entity1, entity2, entity_type))

            # Process uncached pairs
            if batch_to_process:
                batch_results = self._process_batch(batch_to_process)
                results.extend(batch_results)

        return results

    def _build_prompt(
        self, entity1: Dict, entity2: Dict, entity_type: str, context: Dict
    ) -> str:
        """Build comprehensive prompt for LLM analysis."""
        prompt = f"""Analyze these two {entity_type} entities for potential duplication.

Entity 1:
{json.dumps(entity1, indent=2)}

Entity 2:
{json.dumps(entity2, indent=2)}

Additional Context:"""

        if context.get("time_gap"):
            prompt += f"\n- Time between mentions: {context['time_gap']}"

        if context.get("shared_connections"):
            prompt += (
                f"\n- Shared connections: {', '.join(context['shared_connections'])}"
            )

        if context.get("source_documents"):
            prompt += f"\n- Source documents: {', '.join(context['source_documents'])}"

        prompt += """

Please analyze whether these represent the same real-world entity. Consider:
1. Name variations (nicknames, abbreviations, cultural differences)
2. Contact information overlap
3. Professional/organizational context
4. Temporal patterns
5. Communication patterns
6. Any other relevant patterns

Use the score_entity_match tool to provide your structured analysis."""

        return prompt

    def _process_response(
        self, response: anthropic.types.Message
    ) -> Tuple[float, str, Dict]:
        """Extract scoring from LLM response."""
        # Look for tool use in response
        for content in response.content:
            if content.type == "tool_use" and content.name == "score_entity_match":
                result = content.input
                return (
                    result["confidence_score"],
                    result["match_reason"],
                    {
                        "is_match": result["is_match"],
                        "evidence": result["supporting_evidence"],
                        "dimensions": result.get("analysis_dimensions", {}),
                    },
                )

        # Fallback if no tool use found
        return 0.0, "No structured response from LLM", {"error": True}

    def _process_batch(
        self, batch: List[Tuple[Dict, Dict, str]]
    ) -> List[Tuple[float, str, Dict]]:
        """Process a batch of entity pairs in a single LLM request."""
        # Build batch prompt
        prompt = "Analyze the following entity pairs for potential duplication.\n\n"

        for i, (entity1, entity2, entity_type) in enumerate(batch):
            prompt += f"Comparison {i + 1} ({entity_type}):\n"
            prompt += f"Entity A: {json.dumps(entity1)}\n"
            prompt += f"Entity B: {json.dumps(entity2)}\n\n"

        prompt += (
            "For each comparison, use the score_entity_match tool to provide analysis."
        )

        try:
            # Create a tool for each comparison
            tools = [self.SCORING_TOOL] * len(batch)

            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}],
                tools=tools,
            )

            # Extract all tool uses
            results = []
            tool_uses = [c for c in response.content if c.type == "tool_use"]

            for i, (entity1, entity2, entity_type) in enumerate(batch):
                if i < len(tool_uses):
                    result = tool_uses[i].input
                    score_result = (
                        result["confidence_score"],
                        result["match_reason"],
                        {
                            "is_match": result["is_match"],
                            "evidence": result["supporting_evidence"],
                            "dimensions": result.get("analysis_dimensions", {}),
                        },
                    )
                else:
                    # Fallback if not enough tool uses
                    score_result = (0.0, "Batch processing error", {"error": True})

                # Cache result
                cache_key = self.cache.get_cache_key(entity1, entity2, entity_type)
                self.cache.set(cache_key, score_result)
                results.append(score_result)

            return results

        except Exception as e:
            print(f"Batch LLM scoring error: {e}")
            # Return error results for all in batch
            return [(0.0, f"Batch error: {str(e)}", {"error": True})] * len(batch)

    def clear_cache(self):
        """Clear the response cache."""
        self.cache.cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        self.cache.clear_expired()
        return {
            "entries": len(self.cache.cache),
            "ttl_seconds": self.cache.ttl.total_seconds(),
        }


# Fallback to simple scorer if LLM fails
class LLMScorerWithFallback(LLMScorer):
    """LLM scorer with fallback to simple scoring."""

    def __init__(self, api_key: str, fallback_scorer=None, **kwargs):
        """Initialize with fallback scorer."""
        super().__init__(api_key, **kwargs)
        self.fallback_scorer = fallback_scorer

    def score_entities(
        self,
        entity1: Dict,
        entity2: Dict,
        entity_type: str = "person",
        context: Optional[Dict] = None,
    ) -> Tuple[float, str, Dict]:
        """Score with fallback on error."""
        try:
            return super().score_entities(entity1, entity2, entity_type, context)
        except Exception as e:
            if self.fallback_scorer:
                # Use fallback scorer
                score, reason = self.fallback_scorer.score_entities(
                    entity1, entity2, entity_type
                )
                return score, reason, {"fallback": True, "error": str(e)}
            else:
                raise
