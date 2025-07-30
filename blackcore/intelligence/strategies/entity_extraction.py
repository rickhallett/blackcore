"""Entity extraction strategy implementation."""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from ..interfaces import (
    IAnalysisStrategy,
    ILLMProvider,
    IGraphBackend,
    AnalysisType,
    AnalysisRequest,
    AnalysisResult,
    Entity
)

logger = logging.getLogger(__name__)


class EntityExtractionStrategy(IAnalysisStrategy):
    """Strategy for extracting entities from unstructured text."""
    
    def __init__(self):
        """Initialize entity extraction strategy."""
        self.supported_entity_types = [
            "person", "organization", "location", "project",
            "event", "product", "technology", "concept"
        ]
    
    def can_handle(self, analysis_type: AnalysisType) -> bool:
        """Check if this strategy can handle the analysis type."""
        return analysis_type == AnalysisType.ENTITY_EXTRACTION
    
    async def analyze(
        self,
        request: AnalysisRequest,
        llm: ILLMProvider,
        graph: IGraphBackend
    ) -> AnalysisResult:
        """Extract entities from text using LLM."""
        start_time = datetime.now()
        
        try:
            # Extract parameters
            text = request.parameters.get("text", "")
            entity_types = request.parameters.get("entity_types", self.supported_entity_types)
            deduplicate = request.parameters.get("deduplicate", True)
            
            if not text:
                return AnalysisResult(
                    request=request,
                    success=False,
                    data=None,
                    errors=["No text provided for entity extraction"]
                )
            
            # Build prompt
            prompt = self._build_extraction_prompt(text, entity_types, request.context)
            
            # Get LLM response
            response = await llm.complete(
                prompt=prompt,
                system_prompt=self._get_system_prompt(),
                temperature=0.3,  # Lower temperature for more consistent extraction
                response_format={"type": "json_object"}
            )
            
            # Parse response
            try:
                extracted_data = json.loads(response)
                entities_data = extracted_data.get("entities", [])
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response: {e}")
                return AnalysisResult(
                    request=request,
                    success=False,
                    data=None,
                    errors=[f"Failed to parse LLM response: {str(e)}"]
                )
            
            # Process and store entities
            stored_entities = []
            merged_count = 0
            
            for entity_data in entities_data:
                # Create entity
                entity = self._create_entity_from_data(entity_data, request.context.get("source"))
                
                if deduplicate:
                    # Check for existing similar entities
                    existing = await self._find_similar_entity(entity, graph)
                    if existing:
                        # Merge properties
                        entity = self._merge_entities(existing, entity)
                        merged_count += 1
                
                # Store entity
                success = await graph.add_entity(entity)
                if success:
                    stored_entities.append(entity.to_dict())
                else:
                    logger.warning(f"Failed to store entity: {entity.name}")
            
            # Calculate duration
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Prepare metadata
            metadata = {
                "entities_extracted": len(entities_data),
                "entities_stored": len(stored_entities),
                "merged_count": merged_count,
                "entity_types": entity_types
            }
            
            return AnalysisResult(
                request=request,
                success=True,
                data={"entities": stored_entities},
                metadata=metadata,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return AnalysisResult(
                request=request,
                success=False,
                data=None,
                errors=[str(e)],
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
    
    def _build_extraction_prompt(
        self,
        text: str,
        entity_types: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for entity extraction."""
        context_str = ""
        if context:
            context_str = f"\n\nAdditional context:\n{json.dumps(context, indent=2)}"
        
        return f"""Extract entities from the following text. Focus on identifying {', '.join(entity_types)}.

Text:
{text}
{context_str}

For each entity, provide:
- name: The entity's name as it appears in the text
- type: One of {', '.join(entity_types)}
- properties: A dictionary of relevant attributes
- confidence: A confidence score between 0 and 1

Return the result as a JSON object with an "entities" array."""
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for entity extraction."""
        return """You are an expert at extracting structured entities from unstructured text.
Focus on identifying key entities and their properties accurately.
Be conservative - only extract entities that are clearly mentioned in the text.
Provide confidence scores that reflect the clarity of the entity reference."""
    
    def _create_entity_from_data(
        self,
        data: Dict[str, Any],
        source: Optional[str] = None
    ) -> Entity:
        """Create Entity object from extracted data."""
        # Generate deterministic ID based on name and type
        entity_id = f"{data['type']}_{data['name'].lower().replace(' ', '_')}"
        
        return Entity(
            id=entity_id,
            name=data["name"],
            type=data["type"],
            properties=data.get("properties", {}),
            confidence=data.get("confidence", 1.0),
            source=source
        )
    
    async def _find_similar_entity(
        self,
        entity: Entity,
        graph: IGraphBackend
    ) -> Optional[Entity]:
        """Find similar existing entity in graph."""
        # Search by exact name and type
        results = await graph.search_entities({
            "name": entity.name,
            "type": entity.type
        })
        
        if results:
            return results[0]
        
        # Could implement fuzzy matching here for more sophisticated deduplication
        return None
    
    def _merge_entities(self, existing: Entity, new: Entity) -> Entity:
        """Merge properties from new entity into existing one."""
        # Merge properties, preferring new values for conflicts
        merged_properties = {**existing.properties, **new.properties}
        
        # Update confidence as weighted average
        total_confidence = existing.confidence + new.confidence
        merged_confidence = (existing.confidence * 0.7 + new.confidence * 0.3)
        
        return Entity(
            id=existing.id,
            name=existing.name,
            type=existing.type,
            properties=merged_properties,
            confidence=min(merged_confidence, 1.0),
            source=existing.source or new.source
        )