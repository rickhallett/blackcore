"""Relationship mapping strategy implementation."""

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
    Relationship,
    Entity
)

logger = logging.getLogger(__name__)


class RelationshipMappingStrategy(IAnalysisStrategy):
    """Strategy for mapping relationships between entities."""
    
    def __init__(self):
        """Initialize relationship mapping strategy."""
        self.supported_relationship_types = [
            "works_for", "manages", "owns", "partners_with",
            "related_to", "knows", "located_in", "part_of",
            "connected_to", "influences", "depends_on"
        ]
    
    def can_handle(self, analysis_type: AnalysisType) -> bool:
        """Check if this strategy can handle the analysis type."""
        return analysis_type == AnalysisType.RELATIONSHIP_MAPPING
    
    async def analyze(
        self,
        request: AnalysisRequest,
        llm: ILLMProvider,
        graph: IGraphBackend
    ) -> AnalysisResult:
        """Map relationships between entities."""
        start_time = datetime.now()
        
        try:
            # Extract parameters
            entity_ids = request.parameters.get("entity_ids", [])
            infer_implicit = request.parameters.get("infer_implicit", False)
            relationship_types = request.constraints.get(
                "relationship_types",
                self.supported_relationship_types
            )
            
            # Get entities from graph
            entities = []
            if entity_ids:
                # Get specific entities
                for entity_id in entity_ids:
                    entity = await graph.get_entity(entity_id)
                    if entity:
                        entities.append(entity)
            else:
                # Get all entities if none specified
                entities = await graph.get_entities(limit=100)
            
            if len(entities) < 2:
                return AnalysisResult(
                    request=request,
                    success=False,
                    data=None,
                    errors=["Need at least 2 entities to map relationships"]
                )
            
            # Build prompt
            prompt = self._build_mapping_prompt(
                entities,
                relationship_types,
                infer_implicit,
                request.context
            )
            
            # Get LLM response
            response = await llm.complete(
                prompt=prompt,
                system_prompt=self._get_system_prompt(),
                temperature=0.4,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            try:
                extracted_data = json.loads(response)
                relationships_data = extracted_data.get("relationships", [])
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response: {e}")
                return AnalysisResult(
                    request=request,
                    success=False,
                    data=None,
                    errors=[f"Failed to parse LLM response: {str(e)}"]
                )
            
            # Process and store relationships
            stored_relationships = []
            entity_lookup = {e.name: e for e in entities}
            
            for rel_data in relationships_data:
                # Find source and target entities
                source_entity = entity_lookup.get(rel_data["source"])
                target_entity = entity_lookup.get(rel_data["target"])
                
                if not source_entity or not target_entity:
                    logger.warning(
                        f"Could not find entities for relationship: "
                        f"{rel_data['source']} -> {rel_data['target']}"
                    )
                    continue
                
                # Create relationship
                relationship = self._create_relationship_from_data(
                    rel_data,
                    source_entity.id,
                    target_entity.id
                )
                
                # Store relationship
                success = await graph.add_relationship(relationship)
                if success:
                    stored_relationships.append(relationship.to_dict())
                else:
                    logger.warning(
                        f"Failed to store relationship: "
                        f"{source_entity.name} -> {target_entity.name}"
                    )
            
            # Calculate duration
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Prepare metadata
            metadata = {
                "relationships_found": len(relationships_data),
                "relationships_stored": len(stored_relationships),
                "entities_analyzed": len(entities),
                "inferred_implicit": infer_implicit
            }
            
            return AnalysisResult(
                request=request,
                success=True,
                data={"relationships": stored_relationships},
                metadata=metadata,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            logger.error(f"Relationship mapping failed: {e}")
            return AnalysisResult(
                request=request,
                success=False,
                data=None,
                errors=[str(e)],
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
    
    def _build_mapping_prompt(
        self,
        entities: List[Entity],
        relationship_types: List[str],
        infer_implicit: bool,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for relationship mapping."""
        entities_info = []
        for entity in entities:
            info = f"- {entity.name} ({entity.type})"
            if entity.properties:
                info += f" - Properties: {json.dumps(entity.properties)}"
            entities_info.append(info)
        
        implicit_instruction = ""
        if infer_implicit:
            implicit_instruction = """
Also infer implicit relationships based on:
- Shared properties or attributes
- Common patterns or behaviors
- Logical connections that may not be explicitly stated"""
        
        context_str = ""
        if context:
            context_str = f"\n\nAdditional context:\n{json.dumps(context, indent=2)}"
        
        return f"""Analyze the following entities and identify relationships between them.

Entities:
{chr(10).join(entities_info)}
{context_str}

Focus on these relationship types: {', '.join(relationship_types)}
{implicit_instruction}

For each relationship, provide:
- source: The source entity name
- target: The target entity name  
- type: The relationship type
- properties: A dictionary of relationship properties
- confidence: A confidence score between 0 and 1

Return the result as a JSON object with a "relationships" array."""
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for relationship mapping."""
        return """You are an expert at identifying relationships between entities.
Analyze the entities carefully and identify meaningful connections.
Consider both explicit relationships and implicit connections based on shared attributes.
Be thoughtful about directionality - ensure source and target are correctly assigned."""
    
    def _create_relationship_from_data(
        self,
        data: Dict[str, Any],
        source_id: str,
        target_id: str
    ) -> Relationship:
        """Create Relationship object from extracted data."""
        # Generate unique ID
        rel_id = f"{source_id}_{target_id}_{data['type']}_{uuid.uuid4().hex[:8]}"
        
        return Relationship(
            id=rel_id,
            source_id=source_id,
            target_id=target_id,
            type=data["type"],
            properties=data.get("properties", {}),
            confidence=data.get("confidence", 1.0)
        )