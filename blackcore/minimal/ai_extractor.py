"""AI integration for entity extraction from transcripts."""

import json
from typing import Dict, Optional, List
from abc import ABC, abstractmethod

from .models import ExtractedEntities, Entity, Relationship, EntityType


class AIProvider(ABC):
    """Base class for AI providers."""

    @abstractmethod
    def extract_entities(self, text: str, prompt: str) -> ExtractedEntities:
        """Extract entities from text using the given prompt."""
        pass


class ClaudeProvider(AIProvider):
    """Claude AI provider for entity extraction."""

    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        self.api_key = api_key
        self.model = model

        # Lazy import to avoid dependency if not using Claude
        try:
            import anthropic

            self.client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError(
                "anthropic package required for Claude provider. Install with: pip install anthropic"
            )

    def extract_entities(self, text: str, prompt: str) -> ExtractedEntities:
        """Extract entities using Claude."""
        full_prompt = f"{prompt}\n\nTranscript:\n{text}"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            temperature=0.3,
            messages=[{"role": "user", "content": full_prompt}],
        )

        # Parse the response
        content = response.content[0].text
        return self._parse_response(content)

    def _parse_response(self, response: str) -> ExtractedEntities:
        """Parse Claude's response into ExtractedEntities."""
        try:
            # Try to extract JSON from the response
            # Claude sometimes wraps JSON in markdown code blocks
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                # Try to find JSON object in response
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]

            data = json.loads(json_str)

            # Parse entities
            entities = []
            for entity_data in data.get("entities", []):
                entity = Entity(
                    name=entity_data["name"],
                    type=EntityType(entity_data["type"].lower()),
                    properties=entity_data.get("properties", {}),
                    context=entity_data.get("context"),
                    confidence=entity_data.get("confidence", 1.0),
                )
                entities.append(entity)

            # Parse relationships
            relationships = []
            for rel_data in data.get("relationships", []):
                relationship = Relationship(
                    source_entity=rel_data["source_entity"],
                    source_type=EntityType(rel_data["source_type"].lower()),
                    target_entity=rel_data["target_entity"],
                    target_type=EntityType(rel_data["target_type"].lower()),
                    relationship_type=rel_data["relationship_type"],
                    context=rel_data.get("context"),
                )
                relationships.append(relationship)

            return ExtractedEntities(
                entities=entities,
                relationships=relationships,
                summary=data.get("summary"),
                key_points=data.get("key_points", []),
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Fallback: Try to extract basic information
            print(f"Warning: Failed to parse AI response as JSON: {e}")
            return self._fallback_parse(response)

    def _fallback_parse(self, response: str) -> ExtractedEntities:
        """Fallback parsing when JSON parsing fails."""
        # Simple extraction based on common patterns
        entities = []

        # Look for people (capitalized words that might be names)
        import re

        name_pattern = r"\b([A-Z][a-z]+ (?:[A-Z][a-z]+ )?[A-Z][a-z]+)\b"
        potential_names = re.findall(name_pattern, response)

        for name in set(potential_names):
            entities.append(Entity(name=name, type=EntityType.PERSON, confidence=0.5))

        return ExtractedEntities(
            entities=entities, summary="Failed to parse AI response - extracted basic entities only"
        )


class OpenAIProvider(AIProvider):
    """OpenAI provider for entity extraction."""

    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model

        # Lazy import to avoid dependency if not using OpenAI
        try:
            import openai

            self.client = openai.OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError(
                "openai package required for OpenAI provider. Install with: pip install openai"
            )

    def extract_entities(self, text: str, prompt: str) -> ExtractedEntities:
        """Extract entities using OpenAI."""
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that extracts entities and relationships from text.",
                },
                {"role": "user", "content": f"{prompt}\n\nTranscript:\n{text}"},
            ],
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        return self._parse_response(content)

    def _parse_response(self, response: str) -> ExtractedEntities:
        """Parse OpenAI's response into ExtractedEntities."""
        # Similar to Claude parsing but OpenAI usually returns cleaner JSON
        try:
            data = json.loads(response)

            entities = []
            for entity_data in data.get("entities", []):
                entity = Entity(
                    name=entity_data["name"],
                    type=EntityType(entity_data["type"].lower()),
                    properties=entity_data.get("properties", {}),
                    context=entity_data.get("context"),
                    confidence=entity_data.get("confidence", 1.0),
                )
                entities.append(entity)

            relationships = []
            for rel_data in data.get("relationships", []):
                relationship = Relationship(
                    source_entity=rel_data["source_entity"],
                    source_type=EntityType(rel_data["source_type"].lower()),
                    target_entity=rel_data["target_entity"],
                    target_type=EntityType(rel_data["target_type"].lower()),
                    relationship_type=rel_data["relationship_type"],
                    context=rel_data.get("context"),
                )
                relationships.append(relationship)

            return ExtractedEntities(
                entities=entities,
                relationships=relationships,
                summary=data.get("summary"),
                key_points=data.get("key_points", []),
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Warning: Failed to parse AI response: {e}")
            return ExtractedEntities(entities=[], summary="Failed to parse AI response")


class AIExtractor:
    """Main class for extracting entities from transcripts using AI."""

    def __init__(self, provider: str, api_key: str, model: Optional[str] = None):
        """Initialize AI extractor.

        Args:
            provider: AI provider name ("claude" or "openai")
            api_key: API key for the provider
            model: Optional model name override
        """
        self.provider_name = provider.lower()

        if self.provider_name == "claude":
            self.provider = ClaudeProvider(api_key, model or "claude-3-sonnet-20240229")
        elif self.provider_name == "openai":
            self.provider = OpenAIProvider(api_key, model or "gpt-4")
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")

    def extract_entities(self, text: str, prompt: Optional[str] = None) -> ExtractedEntities:
        """Extract entities and relationships from text.

        Args:
            text: The transcript text to analyze
            prompt: Optional custom extraction prompt

        Returns:
            ExtractedEntities containing all extracted information
        """
        if not prompt:
            prompt = self._get_default_prompt()

        return self.provider.extract_entities(text, prompt)

    def _get_default_prompt(self) -> str:
        """Get the default extraction prompt."""
        return """Analyze this transcript and extract:
1. People mentioned (names, roles, organizations)
2. Organizations mentioned
3. Tasks or action items
4. Any transgressions or issues identified
5. Key events or meetings
6. Important dates

For each entity, provide:
- Name
- Type (person/organization/task/transgression/event)
- Relevant properties (role, status, due_date, etc.)
- Context from the transcript

Also identify relationships between entities (e.g., "works for", "assigned to", "attended").

Finally, provide:
- A brief summary (2-3 sentences)
- 3-5 key points

Format your response as JSON with this structure:
{
  "entities": [
    {
      "name": "Entity Name",
      "type": "person|organization|task|transgression|event",
      "properties": {
        "role": "...",
        "status": "...",
        ...
      },
      "context": "Quote or context from transcript",
      "confidence": 0.0-1.0
    }
  ],
  "relationships": [
    {
      "source_entity": "Person Name",
      "source_type": "person",
      "target_entity": "Organization Name",
      "target_type": "organization",
      "relationship_type": "works_for",
      "context": "Optional context"
    }
  ],
  "summary": "Brief summary of the transcript",
  "key_points": ["Point 1", "Point 2", ...]
}"""

    def extract_from_batch(
        self, transcripts: List[Dict[str, str]], prompt: Optional[str] = None
    ) -> List[ExtractedEntities]:
        """Extract entities from multiple transcripts.

        Args:
            transcripts: List of transcripts with 'title' and 'content' keys
            prompt: Optional custom extraction prompt

        Returns:
            List of ExtractedEntities for each transcript
        """
        results = []

        for transcript in transcripts:
            # Add title as context
            text = (
                f"Title: {transcript.get('title', 'Untitled')}\n\n{transcript.get('content', '')}"
            )
            result = self.extract_entities(text, prompt)
            results.append(result)

        return results
