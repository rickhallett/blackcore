"""Path finding strategy implementation."""

import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime
from collections import deque

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


class PathFindingStrategy(IAnalysisStrategy):
    """Strategy for finding paths between entities in the graph."""
    
    def can_handle(self, analysis_type: AnalysisType) -> bool:
        """Check if this strategy can handle the analysis type."""
        return analysis_type == AnalysisType.PATH_FINDING
    
    async def analyze(
        self,
        request: AnalysisRequest,
        llm: ILLMProvider,
        graph: IGraphBackend
    ) -> AnalysisResult:
        """Find paths between entities."""
        start_time = datetime.now()
        
        try:
            # Extract parameters
            source_id = request.parameters.get("source_id")
            target_id = request.parameters.get("target_id")
            max_length = request.parameters.get("max_length", 10)
            find_all = request.parameters.get("find_all", False)
            max_paths = request.parameters.get("max_paths", 5)
            
            if not source_id or not target_id:
                return AnalysisResult(
                    request=request,
                    success=False,
                    data=None,
                    errors=["Both source_id and target_id are required"]
                )
            
            # Extract constraints
            avoid_entity_types = request.constraints.get("avoid_entity_types", [])
            prefer_relationship_types = request.constraints.get("prefer_relationship_types", [])
            
            if find_all:
                # Find multiple paths
                paths = await self._find_multiple_paths(
                    graph,
                    source_id,
                    target_id,
                    max_length,
                    max_paths,
                    avoid_entity_types,
                    prefer_relationship_types
                )
                
                # Format paths
                formatted_paths = []
                for path in paths:
                    formatted_path = self._format_path(path)
                    formatted_paths.append({
                        "path": formatted_path,
                        "length": len(path) - 1
                    })
                
                data = {
                    "paths": formatted_paths,
                    "num_paths": len(formatted_paths)
                }
            else:
                # Find single shortest path
                path = await graph.find_path(source_id, target_id, max_length)
                
                if not path:
                    return AnalysisResult(
                        request=request,
                        success=False,
                        data=None,
                        errors=[f"No path found from {source_id} to {target_id}"]
                    )
                
                # Apply constraints
                if avoid_entity_types:
                    path = self._filter_path_by_constraints(
                        path, avoid_entity_types
                    )
                
                formatted_path = self._format_path(path)
                
                data = {
                    "path": formatted_path,
                    "path_length": len(path) - 1
                }
            
            # Calculate duration
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Prepare metadata
            metadata = {
                "source_id": source_id,
                "target_id": target_id,
                "max_length": max_length,
                "constraints_applied": bool(avoid_entity_types or prefer_relationship_types)
            }
            
            return AnalysisResult(
                request=request,
                success=True,
                data=data,
                metadata=metadata,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            logger.error(f"Path finding failed: {e}", exc_info=True)
            return AnalysisResult(
                request=request,
                success=False,
                data=None,
                errors=[f"Path finding failed: {str(e)}"],
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
    
    async def _find_multiple_paths(
        self,
        graph: IGraphBackend,
        source_id: str,
        target_id: str,
        max_length: int,
        max_paths: int,
        avoid_entity_types: List[str],
        prefer_relationship_types: List[str]
    ) -> List[List[Entity]]:
        """Find multiple paths between entities."""
        paths = []
        found_paths = set()
        
        # Try to find paths with increasing lengths
        for length in range(2, max_length + 1):
            # Try to find a path of this length
            path = await graph.find_path(source_id, target_id, length)
            
            if path:
                # Check if we've seen this path before
                path_key = tuple(e.id for e in path)
                if path_key not in found_paths:
                    found_paths.add(path_key)
                    
                    # Apply constraints
                    if self._path_meets_constraints(path, avoid_entity_types):
                        paths.append(path)
                        
                        if len(paths) >= max_paths:
                            break
            
            # Also try alternative paths by temporarily "blocking" edges
            # This is a simplified approach - more sophisticated algorithms
            # could use k-shortest paths or Yen's algorithm
            if len(paths) < max_paths and paths:
                # Try to find alternative by avoiding nodes in existing paths
                blocked_nodes = set()
                for existing_path in paths:
                    blocked_nodes.update(e.id for e in existing_path[1:-1])
                
                # This would require a more sophisticated graph backend
                # For now, we'll just try the basic approach
        
        return paths
    
    def _path_meets_constraints(
        self,
        path: List[Entity],
        avoid_entity_types: List[str]
    ) -> bool:
        """Check if path meets constraints."""
        if not avoid_entity_types:
            return True
        
        for entity in path:
            if entity.type in avoid_entity_types:
                return False
        
        return True
    
    def _filter_path_by_constraints(
        self,
        path: List[Entity],
        avoid_entity_types: List[str]
    ) -> List[Entity]:
        """Filter path to avoid certain entity types."""
        # This is a simple filter - in reality, we might need to
        # find alternative paths that avoid these types
        return [e for e in path if e.type not in avoid_entity_types]
    
    def _format_path(self, path: List[Entity]) -> List[Dict[str, Any]]:
        """Format path entities for output."""
        formatted = []
        for entity in path:
            formatted.append({
                "id": entity.id,
                "name": entity.name,
                "type": entity.type,
                "properties": entity.properties
            })
        return formatted