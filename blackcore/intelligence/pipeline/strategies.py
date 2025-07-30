"""Investigation strategies for different exploration approaches."""

import json
import logging
from typing import Dict, Any, List, Set, Optional
from abc import ABC, abstractmethod

from ..interfaces import (
    AnalysisType,
    AnalysisRequest,
    ILLMProvider
)

logger = logging.getLogger(__name__)


class InvestigationStrategy(ABC):
    """Base class for investigation strategies."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name."""
        pass
    
    @abstractmethod
    def plan_next_phase(
        self,
        current_state: Dict[str, Any],
        completed_phases: Set[str]
    ) -> Optional[Dict[str, Any]]:
        """Plan the next investigation phase."""
        pass


class BreadthFirstStrategy(InvestigationStrategy):
    """Breadth-first investigation strategy."""
    
    def __init__(self, max_depth: int = 3):
        self.max_depth = max_depth
        self._current_depth = 0
        self._entities_by_depth: Dict[int, List[str]] = {}
    
    @property
    def name(self) -> str:
        return "breadth_first"
    
    def plan_next_phase(
        self,
        current_state: Dict[str, Any],
        completed_phases: Set[str]
    ) -> Optional[Dict[str, Any]]:
        """Plan next phase in breadth-first manner."""
        # Extract entities from current state
        entities = current_state.get("entities", {})
        
        if not entities and self._current_depth == 0:
            # Initial extraction
            return {
                "name": "initial_extraction",
                "type": AnalysisType.ENTITY_EXTRACTION,
                "parameters": current_state.get("initial_context", {})
            }
        
        # Group entities by discovery depth
        for entity_id, entity in entities.items():
            depth = entity.get("depth", self._current_depth)
            if depth not in self._entities_by_depth:
                self._entities_by_depth[depth] = []
            if entity_id not in self._entities_by_depth[depth]:
                self._entities_by_depth[depth].append(entity_id)
        
        # Process all entities at current depth
        current_depth_entities = self._entities_by_depth.get(self._current_depth, [])
        
        for entity_id in current_depth_entities:
            phase_name = f"explore_{entity_id}_depth_{self._current_depth}"
            if phase_name not in completed_phases:
                return {
                    "name": phase_name,
                    "type": AnalysisType.ENTITY_EXTRACTION,
                    "parameters": {
                        "entity_id": entity_id,
                        "context": f"Explore connections of {entities[entity_id].get('name', entity_id)}"
                    }
                }
        
        # Move to next depth
        self._current_depth += 1
        if self._current_depth >= self.max_depth:
            return None
        
        # Start exploring next depth
        return self.plan_next_phase(current_state, completed_phases)


class DepthFirstStrategy(InvestigationStrategy):
    """Depth-first investigation strategy."""
    
    def __init__(self, max_depth: int = 5):
        self.max_depth = max_depth
        self._exploration_stack: List[tuple[str, int]] = []
        self._explored: Set[str] = set()
    
    @property
    def name(self) -> str:
        return "depth_first"
    
    def plan_next_phase(
        self,
        current_state: Dict[str, Any],
        completed_phases: Set[str]
    ) -> Optional[Dict[str, Any]]:
        """Plan next phase in depth-first manner."""
        entities = current_state.get("entities", {})
        
        # Initial extraction if no entities
        if not entities and not self._exploration_stack:
            return {
                "name": "initial_extraction",
                "type": AnalysisType.ENTITY_EXTRACTION,
                "parameters": current_state.get("initial_context", {})
            }
        
        # Add new entities to stack
        for entity_id, entity in entities.items():
            if entity_id not in self._explored:
                depth = entity.get("depth", 0)
                if depth < self.max_depth:
                    self._exploration_stack.append((entity_id, depth))
                    self._explored.add(entity_id)
        
        # Explore from stack (LIFO for depth-first)
        while self._exploration_stack:
            entity_id, depth = self._exploration_stack.pop()
            
            phase_name = f"explore_{entity_id}_depth_{depth}"
            if phase_name not in completed_phases:
                return {
                    "name": phase_name,
                    "type": AnalysisType.ENTITY_EXTRACTION,
                    "parameters": {
                        "entity_id": entity_id,
                        "depth": depth + 1,
                        "context": f"Deep exploration of {entities.get(entity_id, {}).get('name', entity_id)}"
                    }
                }
        
        return None


class HypothesisDrivenStrategy(InvestigationStrategy):
    """Hypothesis-driven investigation strategy."""
    
    def __init__(self, llm_provider: Optional[ILLMProvider] = None):
        self.llm_provider = llm_provider
        self._hypotheses: List[Dict[str, Any]] = []
        self._tested_hypotheses: Set[str] = set()
    
    @property 
    def name(self) -> str:
        return "hypothesis_driven"
    
    async def generate_hypotheses(
        self,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate hypotheses using LLM."""
        if not self.llm_provider:
            return []
        
        prompt = f"""
        Based on the following investigation context, generate hypotheses to test:
        
        Context: {json.dumps(context, indent=2)}
        
        Generate 2-3 specific, testable hypotheses about the entities and their relationships.
        
        Return as JSON:
        {{
            "hypotheses": [
                {{
                    "id": "h1",
                    "description": "hypothesis description",
                    "confidence": 0.0-1.0,
                    "required_evidence": ["type of evidence needed"]
                }}
            ]
        }}
        """
        
        try:
            response = await self.llm_provider.complete(
                prompt=prompt,
                system_prompt="You are an investigation assistant generating testable hypotheses.",
                temperature=0.7
            )
            
            result = json.loads(response)
            return result.get("hypotheses", [])
            
        except Exception as e:
            logger.error(f"Failed to generate hypotheses: {e}")
            return []
    
    def plan_next_phase(
        self,
        current_state: Dict[str, Any],
        completed_phases: Set[str]
    ) -> Optional[Dict[str, Any]]:
        """Plan next phase based on hypotheses."""
        # Generate hypotheses if not done
        if not self._hypotheses and "hypothesis_generation" not in completed_phases:
            return {
                "name": "hypothesis_generation",
                "type": "custom",
                "action": "generate_hypotheses",
                "parameters": current_state
            }
        
        # Test each hypothesis
        for hypothesis in self._hypotheses:
            h_id = hypothesis["id"]
            if h_id not in self._tested_hypotheses:
                self._tested_hypotheses.add(h_id)
                
                # Determine analysis type based on hypothesis
                if "relationship" in hypothesis["description"].lower():
                    analysis_type = AnalysisType.RELATIONSHIP_MAPPING
                elif "anomaly" in hypothesis["description"].lower():
                    analysis_type = AnalysisType.ANOMALY_DETECTION
                elif "community" in hypothesis["description"].lower():
                    analysis_type = AnalysisType.COMMUNITY_DETECTION
                else:
                    analysis_type = AnalysisType.ENTITY_EXTRACTION
                
                return {
                    "name": f"test_hypothesis_{h_id}",
                    "type": analysis_type,
                    "parameters": {
                        "hypothesis": hypothesis,
                        "context": current_state
                    }
                }
        
        return None
    
    def update_hypotheses(
        self,
        hypothesis_id: str,
        result: Dict[str, Any]
    ) -> None:
        """Update hypothesis based on test results."""
        for hypothesis in self._hypotheses:
            if hypothesis["id"] == hypothesis_id:
                # Check if evidence supports hypothesis
                if self._evaluate_hypothesis(hypothesis, result):
                    hypothesis["confirmed"] = True
                else:
                    hypothesis["confirmed"] = False
                break
    
    def _evaluate_hypothesis(
        self,
        hypothesis: Dict[str, Any],
        result: Dict[str, Any]
    ) -> bool:
        """Evaluate if result supports hypothesis."""
        # Simple evaluation based on presence of expected evidence
        required_evidence = hypothesis.get("required_evidence", [])
        
        for evidence_type in required_evidence:
            if "relationship" in evidence_type.lower():
                if result.get("relationships"):
                    return True
            elif "anomaly" in evidence_type.lower():
                if result.get("anomalies"):
                    return False  # Hypothesis was about no anomaly
            
        # Default: check if any substantial data was found
        return bool(result.get("entities") or result.get("relationships"))