"""Investigation pipeline implementation."""

import asyncio
import logging
import uuid
import json
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from collections import defaultdict

from ..interfaces import (
    IInvestigationPipeline,
    ILLMProvider,
    IGraphBackend,
    AnalysisType,
    AnalysisRequest,
    AnalysisResult
)
from ..engine import AnalysisEngine

logger = logging.getLogger(__name__)


class InvestigationPhase:
    """Represents a phase in an investigation."""
    
    def __init__(
        self,
        name: str,
        analysis_type: AnalysisType,
        depends_on: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.analysis_type = analysis_type
        self.depends_on = depends_on or []
        self.parameters = parameters or {}
        self.result: Optional[AnalysisResult] = None
        self.status = "pending"
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None


class Investigation:
    """Represents an ongoing investigation."""
    
    def __init__(
        self,
        investigation_id: str,
        initial_context: Dict[str, Any],
        objectives: List[str]
    ):
        self.id = investigation_id
        self.initial_context = initial_context
        self.objectives = objectives
        self.phases: List[InvestigationPhase] = []
        self.evidence: List[Dict[str, Any]] = []
        self.status = "running"
        self.created_at = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.errors: List[str] = []
        self.adaptive_actions = 0
        
        # Collected data
        self.entities: Dict[str, Any] = {}
        self.relationships: List[Dict[str, Any]] = []
        self.findings: Dict[str, Any] = {}


class InvestigationPipeline(IInvestigationPipeline):
    """Multi-phase investigation pipeline."""
    
    def __init__(
        self,
        llm_provider: ILLMProvider,
        graph_backend: IGraphBackend,
        analysis_engine: Optional[AnalysisEngine] = None,
        strategy: Optional[Any] = None,
        adaptive: bool = False,
        continue_on_error: bool = False,
        timeout_seconds: Optional[int] = None,
        enable_parallel: bool = False,
        enable_persistence: bool = False,
        collect_metrics: bool = False
    ):
        self.llm_provider = llm_provider
        self.graph_backend = graph_backend
        self.analysis_engine = analysis_engine or AnalysisEngine(
            llm_provider=llm_provider,
            graph_backend=graph_backend
        )
        self.strategy = strategy
        self.adaptive = adaptive
        self.continue_on_error = continue_on_error
        self.timeout_seconds = timeout_seconds
        self.enable_parallel = enable_parallel
        self.enable_persistence = enable_persistence
        self.collect_metrics = collect_metrics
        
        # Active investigations
        self._investigations: Dict[str, Investigation] = {}
        
        # Metrics
        self._metrics = {
            "total_investigations": 0,
            "completed_investigations": 0,
            "failed_investigations": 0,
            "total_phases_executed": 0,
            "total_duration_ms": 0,
            "entities_discovered": 0,
            "relationships_discovered": 0,
            "errors": []
        }
    
    async def investigate(
        self,
        initial_context: Dict[str, Any],
        objectives: List[str],
        phases: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Run a multi-phase investigation."""
        start_time = datetime.now()
        investigation_id = str(uuid.uuid4())
        
        # Create investigation
        investigation = Investigation(
            investigation_id=investigation_id,
            initial_context=initial_context,
            objectives=objectives
        )
        
        self._investigations[investigation_id] = investigation
        
        if self.collect_metrics:
            self._metrics["total_investigations"] += 1
        
        try:
            # Apply timeout if configured
            if self.timeout_seconds:
                try:
                    await asyncio.wait_for(
                        self._run_investigation(investigation, phases),
                        timeout=self.timeout_seconds
                    )
                except asyncio.TimeoutError:
                    investigation.status = "timeout"
                    investigation.errors.append(f"Investigation timed out after {self.timeout_seconds} seconds")
            else:
                await self._run_investigation(investigation, phases)
            
            # Update metrics
            if self.collect_metrics:
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                self._metrics["total_duration_ms"] += duration_ms
                
                if investigation.status == "completed":
                    self._metrics["completed_investigations"] += 1
                else:
                    self._metrics["failed_investigations"] += 1
                
                self._metrics["entities_discovered"] += len(investigation.entities)
                self._metrics["relationships_discovered"] += len(investigation.relationships)
            
            # Build result
            result = self._build_investigation_result(investigation)
            
            return result
            
        except Exception as e:
            logger.error(f"Investigation failed: {e}", exc_info=True)
            investigation.status = "failed"
            investigation.errors.append(str(e))
            
            if self.collect_metrics:
                self._metrics["failed_investigations"] += 1
                self._metrics["errors"].append(str(e))
            
            return self._build_investigation_result(investigation)
    
    async def _run_investigation(
        self,
        investigation: Investigation,
        phases: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Run the investigation phases."""
        # Create default phases if not provided
        if not phases:
            phases = self._create_default_phases(investigation)
        
        # Convert to InvestigationPhase objects
        for phase_config in phases:
            phase = InvestigationPhase(
                name=phase_config.get("name", phase_config["type"]),
                analysis_type=phase_config.get("type", AnalysisType.ENTITY_EXTRACTION),
                depends_on=phase_config.get("depends_on", []),
                parameters=phase_config.get("parameters", {})
            )
            investigation.phases.append(phase)
        
        # Execute phases
        if self.enable_parallel:
            await self._execute_phases_parallel(investigation)
        else:
            await self._execute_phases_sequential(investigation)
        
        # Check if all phases completed successfully
        failed_phases = [p for p in investigation.phases if p.status == "failed"]
        if failed_phases and not self.continue_on_error:
            investigation.status = "failed"
        elif failed_phases:
            investigation.status = "completed_with_errors"
        else:
            investigation.status = "completed"
        
        investigation.completed_at = datetime.now()
    
    async def _execute_phases_sequential(self, investigation: Investigation) -> None:
        """Execute phases sequentially."""
        completed_phases: Set[str] = set()
        
        for phase in investigation.phases:
            # Check dependencies
            if not all(dep in completed_phases for dep in phase.depends_on):
                phase.status = "skipped"
                phase.result = AnalysisResult(
                    request=AnalysisRequest(
                        type=phase.analysis_type,
                        parameters=phase.parameters
                    ),
                    success=False,
                    data=None,
                    errors=["Dependencies not met"]
                )
                continue
            
            # Execute phase
            await self._execute_phase(investigation, phase)
            
            if phase.status == "completed":
                completed_phases.add(phase.name)
            elif not self.continue_on_error:
                break
            
            # Check for adaptive actions
            if self.adaptive and phase.result and phase.result.metadata.get("anomaly_detected"):
                await self._trigger_adaptive_phase(investigation, phase)
    
    async def _execute_phases_parallel(self, investigation: Investigation) -> None:
        """Execute independent phases in parallel."""
        completed_phases: Set[str] = set()
        pending_phases = list(investigation.phases)
        
        while pending_phases:
            # Find phases that can run now
            ready_phases = [
                phase for phase in pending_phases
                if all(dep in completed_phases for dep in phase.depends_on)
            ]
            
            if not ready_phases:
                # No phases ready, check for circular dependencies
                logger.error("No phases ready to execute - possible circular dependency")
                break
            
            # Execute ready phases in parallel
            tasks = [
                self._execute_phase(investigation, phase)
                for phase in ready_phases
            ]
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update completed phases
            for phase in ready_phases:
                if phase.status == "completed":
                    completed_phases.add(phase.name)
                pending_phases.remove(phase)
                
                if phase.status == "failed" and not self.continue_on_error:
                    # Cancel remaining phases
                    for p in pending_phases:
                        p.status = "cancelled"
                    return
    
    async def _execute_phase(
        self,
        investigation: Investigation,
        phase: InvestigationPhase
    ) -> None:
        """Execute a single investigation phase."""
        phase.status = "running"
        phase.started_at = datetime.now()
        
        try:
            # Build analysis request
            request = AnalysisRequest(
                type=phase.analysis_type,
                parameters=self._build_phase_parameters(investigation, phase),
                context=investigation.initial_context
            )
            
            # Execute analysis
            result = await self.analysis_engine.analyze(request)
            phase.result = result
            
            if result.success:
                phase.status = "completed"
                # Extract data from result
                self._process_phase_result(investigation, phase, result)
            else:
                phase.status = "failed"
                investigation.errors.extend(result.errors)
            
            if self.collect_metrics:
                self._metrics["total_phases_executed"] += 1
            
        except Exception as e:
            logger.error(f"Phase {phase.name} failed: {e}", exc_info=True)
            phase.status = "failed"
            phase.result = AnalysisResult(
                request=AnalysisRequest(
                    type=phase.analysis_type,
                    parameters=phase.parameters
                ),
                success=False,
                data=None,
                errors=[str(e)]
            )
            investigation.errors.append(f"Phase {phase.name} failed: {str(e)}")
        finally:
            phase.completed_at = datetime.now()
    
    def _build_phase_parameters(
        self,
        investigation: Investigation,
        phase: InvestigationPhase
    ) -> Dict[str, Any]:
        """Build parameters for a phase based on investigation context."""
        params = phase.parameters.copy()
        
        # Add discovered entities if needed
        if phase.analysis_type == AnalysisType.RELATIONSHIP_MAPPING:
            if "entity_ids" not in params:
                params["entity_ids"] = list(investigation.entities.keys())
        
        # Add context from previous phases
        if phase.analysis_type == AnalysisType.ANOMALY_DETECTION:
            if "entity_type" not in params and investigation.entities:
                # Infer entity type from discovered entities
                entity_types = set(e.get("type") for e in investigation.entities.values())
                if entity_types:
                    params["entity_type"] = list(entity_types)[0]
        
        return params
    
    def _process_phase_result(
        self,
        investigation: Investigation,
        phase: InvestigationPhase,
        result: AnalysisResult
    ) -> None:
        """Process and store phase results."""
        if not result.data:
            return
        
        # Extract entities
        if "entities" in result.data:
            for entity in result.data["entities"]:
                entity_id = entity.get("id", str(uuid.uuid4()))
                investigation.entities[entity_id] = entity
        
        # Extract relationships
        if "relationships" in result.data:
            investigation.relationships.extend(result.data["relationships"])
        
        # Store other findings
        investigation.findings[phase.name] = result.data
    
    async def _trigger_adaptive_phase(
        self,
        investigation: Investigation,
        trigger_phase: InvestigationPhase
    ) -> None:
        """Trigger an adaptive phase based on findings."""
        investigation.adaptive_actions += 1
        
        # Create adaptive phase
        adaptive_phase = InvestigationPhase(
            name=f"adaptive_{trigger_phase.name}",
            analysis_type=AnalysisType.ANOMALY_DETECTION,
            parameters={
                "triggered_by": trigger_phase.name,
                "context": trigger_phase.result.data if trigger_phase.result else {}
            }
        )
        
        investigation.phases.append(adaptive_phase)
        
        # Execute immediately
        await self._execute_phase(investigation, adaptive_phase)
    
    def _create_default_phases(
        self,
        investigation: Investigation
    ) -> List[Dict[str, Any]]:
        """Create default investigation phases."""
        return [
            {
                "name": "extract",
                "type": AnalysisType.ENTITY_EXTRACTION,
                "depends_on": []
            },
            {
                "name": "map",
                "type": AnalysisType.RELATIONSHIP_MAPPING,
                "depends_on": ["extract"]
            },
            {
                "name": "analyze",
                "type": AnalysisType.COMMUNITY_DETECTION,
                "depends_on": ["extract", "map"]
            }
        ]
    
    def _build_investigation_result(self, investigation: Investigation) -> Dict[str, Any]:
        """Build investigation result dictionary."""
        phases_data = []
        for phase in investigation.phases:
            phase_data = {
                "name": phase.name,
                "type": phase.analysis_type.value if isinstance(phase.analysis_type, AnalysisType) else str(phase.analysis_type),
                "status": phase.status,
                "success": phase.status == "completed",
                "started_at": phase.started_at.isoformat() if phase.started_at else None,
                "completed_at": phase.completed_at.isoformat() if phase.completed_at else None
            }
            
            if phase.result:
                phase_data["data"] = phase.result.data
                phase_data["errors"] = phase.result.errors
            
            phases_data.append(phase_data)
        
        result = {
            "investigation_id": investigation.id,
            "status": investigation.status,
            "created_at": investigation.created_at.isoformat(),
            "completed_at": investigation.completed_at.isoformat() if investigation.completed_at else None,
            "objectives": investigation.objectives,
            "phases": phases_data,
            "total_entities": len(investigation.entities),
            "total_relationships": len(investigation.relationships),
            "errors": investigation.errors,
            "adaptive_actions": investigation.adaptive_actions
        }
        
        # Add strategy info if available
        if self.strategy:
            result["strategy"] = getattr(self.strategy, "name", "custom")
            
            # Add hypothesis info for hypothesis-driven strategy
            if hasattr(self.strategy, "_hypotheses"):
                result["hypotheses"] = self.strategy._hypotheses
                
            # Add depth info for traversal strategies
            if hasattr(self.strategy, "_current_depth"):
                result["max_depth_reached"] = self.strategy._current_depth
        
        return result
    
    async def add_evidence(
        self,
        investigation_id: str,
        evidence: Dict[str, Any]
    ) -> bool:
        """Add evidence to an ongoing investigation."""
        if investigation_id not in self._investigations:
            logger.error(f"Investigation {investigation_id} not found")
            return False
        
        investigation = self._investigations[investigation_id]
        
        # Add timestamp if not present
        if "timestamp" not in evidence:
            evidence["timestamp"] = datetime.now().isoformat()
        
        investigation.evidence.append(evidence)
        
        # Trigger re-analysis if adaptive mode
        if self.adaptive and investigation.status == "running":
            # Create evidence analysis phase
            evidence_phase = InvestigationPhase(
                name=f"evidence_analysis_{len(investigation.evidence)}",
                analysis_type=AnalysisType.ENTITY_EXTRACTION,
                parameters={
                    "text": evidence.get("content", ""),
                    "evidence_type": evidence.get("type", "unknown")
                }
            )
            
            investigation.phases.append(evidence_phase)
            await self._execute_phase(investigation, evidence_phase)
        
        return True
    
    async def get_investigation(self, investigation_id: str) -> Optional[Dict[str, Any]]:
        """Get investigation details."""
        if investigation_id not in self._investigations:
            return None
        
        investigation = self._investigations[investigation_id]
        result = self._build_investigation_result(investigation)
        result["evidence"] = investigation.evidence
        
        return result
    
    async def save_state(self, investigation_id: str) -> Optional[Dict[str, Any]]:
        """Save investigation state for persistence."""
        if not self.enable_persistence:
            return None
        
        if investigation_id not in self._investigations:
            return None
        
        investigation = self._investigations[investigation_id]
        
        # Serialize investigation state
        state = {
            "id": investigation.id,
            "initial_context": investigation.initial_context,
            "objectives": investigation.objectives,
            "status": investigation.status,
            "created_at": investigation.created_at.isoformat(),
            "entities": investigation.entities,
            "relationships": investigation.relationships,
            "findings": investigation.findings,
            "evidence": investigation.evidence,
            "errors": investigation.errors,
            "adaptive_actions": investigation.adaptive_actions,
            "phases": []
        }
        
        # Serialize phases
        for phase in investigation.phases:
            phase_state = {
                "name": phase.name,
                "analysis_type": phase.analysis_type.value if isinstance(phase.analysis_type, AnalysisType) else str(phase.analysis_type),
                "depends_on": phase.depends_on,
                "parameters": phase.parameters,
                "status": phase.status
            }
            
            if phase.result:
                phase_state["result"] = phase.result.to_dict()
            
            state["phases"].append(phase_state)
        
        return state
    
    async def load_state(
        self,
        investigation_id: str,
        state: Dict[str, Any]
    ) -> bool:
        """Load investigation state from persistence."""
        if not self.enable_persistence:
            return False
        
        try:
            # Create investigation from state
            investigation = Investigation(
                investigation_id=state["id"],
                initial_context=state["initial_context"],
                objectives=state["objectives"]
            )
            
            # Restore fields
            investigation.status = state["status"]
            investigation.created_at = datetime.fromisoformat(state["created_at"])
            investigation.entities = state["entities"]
            investigation.relationships = state["relationships"]
            investigation.findings = state["findings"]
            investigation.evidence = state["evidence"]
            investigation.errors = state["errors"]
            investigation.adaptive_actions = state["adaptive_actions"]
            
            # Restore phases
            for phase_state in state["phases"]:
                phase = InvestigationPhase(
                    name=phase_state["name"],
                    analysis_type=AnalysisType(phase_state["analysis_type"]),
                    depends_on=phase_state["depends_on"],
                    parameters=phase_state["parameters"]
                )
                phase.status = phase_state["status"]
                
                if "result" in phase_state:
                    phase.result = AnalysisResult.from_dict(phase_state["result"])
                
                investigation.phases.append(phase)
            
            self._investigations[investigation_id] = investigation
            return True
            
        except Exception as e:
            logger.error(f"Failed to load investigation state: {e}", exc_info=True)
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get pipeline metrics."""
        if not self.collect_metrics:
            return {}
        
        metrics = self._metrics.copy()
        
        # Calculate averages
        if metrics["total_investigations"] > 0:
            metrics["average_duration_ms"] = (
                metrics["total_duration_ms"] / metrics["total_investigations"]
            )
            metrics["average_phases_per_investigation"] = (
                metrics["total_phases_executed"] / metrics["total_investigations"]
            )
        
        return metrics