"""Event sourcing system with causal ordering and async handlers."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

import msgpack
import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class EventStatus(str, Enum):
    """Event processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Event:
    """Immutable event with causal tracking."""
    event_type: str
    entity_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    causality: List[str] = field(default_factory=list)  # Parent event IDs
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING
    
    def pack(self) -> bytes:
        """Serialize event to bytes."""
        return msgpack.packb({
            "event_id": self.event_id,
            "event_type": self.event_type,
            "entity_id": self.entity_id,
            "data": self.data,
            "timestamp": self.timestamp,
            "causality": self.causality,
            "metadata": self.metadata,
            "status": self.status.value
        })
    
    @classmethod
    def unpack(cls, data: bytes) -> Event:
        """Deserialize event from bytes."""
        unpacked = msgpack.unpackb(data)
        unpacked["status"] = EventStatus(unpacked["status"])
        return cls(**unpacked)
    
    def caused_by(self, *events: Event) -> Event:
        """Mark this event as caused by other events."""
        for event in events:
            if event.event_id not in self.causality:
                self.causality.append(event.event_id)
        return self


class EventHandler:
    """Base class for event handlers."""
    
    def __init__(self, handler_id: Optional[str] = None):
        self.handler_id = handler_id or str(uuid.uuid4())
        self.event_types: Set[str] = set()
        self.priority: int = 0  # Higher = processed first
        
    async def handle(self, event: Event) -> Any:
        """Handle event asynchronously."""
        raise NotImplementedError
    
    def can_handle(self, event: Event) -> bool:
        """Check if handler can process event."""
        return event.event_type in self.event_types


class EventStore:
    """Persistent event storage with indexing."""
    
    def __init__(self):
        self.events: Dict[str, Event] = {}
        self.by_entity: Dict[str, List[str]] = defaultdict(list)
        self.by_type: Dict[str, List[str]] = defaultdict(list)
        self.causal_graph: Dict[str, Set[str]] = defaultdict(set)  # event -> caused events
        
    def append(self, event: Event) -> None:
        """Append event to store."""
        self.events[event.event_id] = event
        
        # Update indices
        if event.entity_id:
            self.by_entity[event.entity_id].append(event.event_id)
        self.by_type[event.event_type].append(event.event_id)
        
        # Update causal graph
        for parent_id in event.causality:
            self.causal_graph[parent_id].add(event.event_id)
    
    def get_event(self, event_id: str) -> Optional[Event]:
        """Get event by ID."""
        return self.events.get(event_id)
    
    def get_entity_events(
        self, 
        entity_id: str,
        event_types: Optional[List[str]] = None,
        since: Optional[float] = None
    ) -> List[Event]:
        """Get all events for an entity."""
        event_ids = self.by_entity.get(entity_id, [])
        events = []
        
        for event_id in event_ids:
            event = self.events.get(event_id)
            if event:
                if event_types and event.event_type not in event_types:
                    continue
                if since and event.timestamp < since:
                    continue
                events.append(event)
        
        return sorted(events, key=lambda e: e.timestamp)
    
    def get_causal_chain(self, event_id: str) -> List[Event]:
        """Get all events in causal chain."""
        chain = []
        visited = set()
        
        def traverse(eid: str):
            if eid in visited:
                return
            visited.add(eid)
            
            event = self.events.get(eid)
            if event:
                # Add parents first (DFS)
                for parent_id in event.causality:
                    traverse(parent_id)
                chain.append(event)
        
        traverse(event_id)
        return chain
    
    def get_effects(self, event_id: str) -> List[Event]:
        """Get all events caused by this event."""
        effects = []
        visited = set()
        
        def traverse(eid: str):
            if eid in visited:
                return
            visited.add(eid)
            
            for child_id in self.causal_graph.get(eid, []):
                event = self.events.get(child_id)
                if event:
                    effects.append(event)
                    traverse(child_id)
        
        traverse(event_id)
        return effects


class EventBus:
    """Async event bus with handler registration and processing."""
    
    def __init__(self, event_store: Optional[EventStore] = None):
        self.handlers: List[EventHandler] = []
        self.event_store = event_store or EventStore()
        self.processing_queue: asyncio.Queue[Event] = asyncio.Queue()
        self.middleware: List[Callable] = []
        self._running = False
        self._workers: List[asyncio.Task] = []
        
    def register_handler(self, handler: EventHandler) -> None:
        """Register event handler."""
        self.handlers.append(handler)
        self.handlers.sort(key=lambda h: h.priority, reverse=True)
        
    def add_middleware(self, middleware: Callable) -> None:
        """Add processing middleware."""
        self.middleware.append(middleware)
    
    def emit(self, event: Event) -> None:
        """Emit event for processing."""
        # Store event immediately
        self.event_store.append(event)
        
        # Queue for async processing
        asyncio.create_task(self.processing_queue.put(event))
        
        logger.info(
            "event_emitted",
            event_id=event.event_id,
            event_type=event.event_type,
            entity_id=event.entity_id
        )
    
    async def process_event(self, event: Event) -> None:
        """Process single event through handlers."""
        event.status = EventStatus.PROCESSING
        
        try:
            # Apply middleware
            for middleware in self.middleware:
                event = await middleware(event)
                if event is None:
                    return  # Middleware cancelled event
            
            # Find and execute handlers
            results = []
            for handler in self.handlers:
                if handler.can_handle(event):
                    try:
                        result = await handler.handle(event)
                        results.append((handler.handler_id, result))
                    except Exception as e:
                        logger.error(
                            "handler_error",
                            handler_id=handler.handler_id,
                            event_id=event.event_id,
                            error=str(e)
                        )
            
            event.status = EventStatus.COMPLETED
            event.metadata["handler_results"] = results
            
        except Exception as e:
            event.status = EventStatus.FAILED
            event.metadata["error"] = str(e)
            logger.error(
                "event_processing_failed",
                event_id=event.event_id,
                error=str(e)
            )
    
    async def _worker(self) -> None:
        """Worker coroutine for processing events."""
        while self._running:
            try:
                # Wait for event with timeout
                event = await asyncio.wait_for(
                    self.processing_queue.get(),
                    timeout=1.0
                )
                await self.process_event(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error("worker_error", error=str(e))
    
    async def start(self, num_workers: int = 4) -> None:
        """Start event processing workers."""
        self._running = True
        self._workers = [
            asyncio.create_task(self._worker())
            for _ in range(num_workers)
        ]
        logger.info("event_bus_started", num_workers=num_workers)
    
    async def stop(self) -> None:
        """Stop event processing."""
        self._running = False
        await asyncio.gather(*self._workers, return_exceptions=True)
        logger.info("event_bus_stopped")
    
    def query_events(
        self,
        entity_id: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        since: Optional[float] = None
    ) -> List[Event]:
        """Query events from store."""
        if entity_id:
            return self.event_store.get_entity_events(
                entity_id, event_types, since
            )
        
        # Query all events matching criteria
        events = []
        for event in self.event_store.events.values():
            if event_types and event.event_type not in event_types:
                continue
            if since and event.timestamp < since:
                continue
            events.append(event)
        
        return sorted(events, key=lambda e: e.timestamp)


class SagaHandler(EventHandler):
    """Long-running process handler for complex workflows."""
    
    def __init__(self, saga_id: str):
        super().__init__(saga_id)
        self.state: Dict[str, Any] = {}
        self.completed_steps: Set[str] = set()
        
    async def handle(self, event: Event) -> Any:
        """Handle event as part of saga."""
        step_name = f"{event.event_type}_{event.entity_id}"
        
        if step_name in self.completed_steps:
            return  # Idempotent
        
        result = await self.process_step(event)
        self.completed_steps.add(step_name)
        
        return result
    
    async def process_step(self, event: Event) -> Any:
        """Process individual saga step."""
        raise NotImplementedError