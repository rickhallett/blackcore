# Webhook Support Specification

## Overview

Webhook support enables real-time synchronization between Notion and Blackcore by listening for changes and automatically updating the local cache.

## Goals

1. Receive real-time notifications of Notion changes
2. Update local JSON cache automatically
3. Trigger downstream processes (e.g., entity extraction)
4. Handle failures gracefully with retry logic
5. Maintain data consistency

## Architecture

### Webhook Receiver

```python
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
from enum import Enum

class WebhookEventType(Enum):
    PAGE_CREATED = "page.created"
    PAGE_UPDATED = "page.updated"
    PAGE_DELETED = "page.deleted"
    DATABASE_UPDATED = "database.updated"

class NotionWebhookPayload(BaseModel):
    event_type: WebhookEventType
    workspace_id: str
    database_id: Optional[str]
    page_id: Optional[str]
    user_id: str
    timestamp: datetime
    changes: Optional[Dict[str, Any]]

class WebhookConfig(BaseModel):
    secret: str  # For verifying webhook authenticity
    endpoint_url: str
    databases_to_watch: List[str]
    event_types: List[WebhookEventType]
    
app = FastAPI()

class WebhookReceiver:
    def __init__(self, config: WebhookConfig):
        self.config = config
        self.event_queue = asyncio.Queue()
        self.processors = {}
        
    def register_processor(self, event_type: WebhookEventType, processor):
        """Register a processor for specific event types"""
        self.processors[event_type] = processor
    
    async def handle_webhook(self, request: Request) -> Dict:
        # Verify webhook signature
        signature = request.headers.get("X-Notion-Signature")
        if not self._verify_signature(await request.body(), signature):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse payload
        payload = NotionWebhookPayload(**await request.json())
        
        # Filter events
        if payload.database_id not in self.config.databases_to_watch:
            return {"status": "ignored", "reason": "database not watched"}
        
        # Queue for processing
        await self.event_queue.put(payload)
        
        return {"status": "queued", "event_id": str(payload.timestamp)}
```

### Event Processors

```python
from abc import ABC, abstractmethod

class EventProcessor(ABC):
    @abstractmethod
    async def process(self, event: NotionWebhookPayload) -> bool:
        pass

class PageCreatedProcessor(EventProcessor):
    def __init__(self, notion_client, json_sync):
        self.notion = notion_client
        self.sync = json_sync
    
    async def process(self, event: NotionWebhookPayload) -> bool:
        # Fetch new page data
        page = await self.notion.get_page(event.page_id)
        
        # Update local cache
        database_name = self._get_database_name(event.database_id)
        self.sync.add_to_cache(database_name, page)
        
        # Trigger entity extraction if it's a transcript
        if database_name == "Intelligence & Transcripts":
            await self._trigger_processing(page)
        
        return True

class PageUpdatedProcessor(EventProcessor):
    def __init__(self, notion_client, json_sync):
        self.notion = notion_client
        self.sync = json_sync
        self.update_debouncer = Debouncer(seconds=5)
    
    async def process(self, event: NotionWebhookPayload) -> bool:
        # Debounce rapid updates
        if not await self.update_debouncer.should_process(event.page_id):
            return False
        
        # Fetch updated data
        page = await self.notion.get_page(event.page_id)
        
        # Update cache
        database_name = self._get_database_name(event.database_id)
        self.sync.update_in_cache(database_name, page)
        
        # Check if relationships changed
        if event.changes and "relations" in event.changes:
            await self._update_related_entities(page, event.changes["relations"])
        
        return True
```

### Event Queue Worker

```python
class EventQueueWorker:
    def __init__(self, receiver: WebhookReceiver):
        self.receiver = receiver
        self.running = False
        self.retry_queue = asyncio.Queue()
        
    async def start(self):
        self.running = True
        
        # Start main worker
        asyncio.create_task(self._process_events())
        
        # Start retry worker
        asyncio.create_task(self._process_retries())
    
    async def _process_events(self):
        while self.running:
            try:
                # Get event with timeout
                event = await asyncio.wait_for(
                    self.receiver.event_queue.get(), 
                    timeout=1.0
                )
                
                # Process event
                processor = self.receiver.processors.get(event.event_type)
                if processor:
                    try:
                        success = await processor.process(event)
                        if not success:
                            await self._schedule_retry(event)
                    except Exception as e:
                        logger.error(f"Error processing {event.event_type}: {e}")
                        await self._schedule_retry(event)
                        
            except asyncio.TimeoutError:
                continue
    
    async def _schedule_retry(self, event: NotionWebhookPayload, attempt: int = 1):
        if attempt > 3:
            logger.error(f"Max retries exceeded for {event.event_type}")
            return
        
        # Exponential backoff
        delay = 2 ** attempt
        await asyncio.sleep(delay)
        
        # Add retry metadata
        event.retry_attempt = attempt
        await self.retry_queue.put(event)
```

## Webhook Registration

```python
class WebhookManager:
    def __init__(self, notion_client, webhook_config):
        self.notion = notion_client
        self.config = webhook_config
    
    async def register_webhooks(self):
        """Register webhooks with Notion API"""
        for database_id in self.config.databases_to_watch:
            webhook = {
                "url": self.config.endpoint_url,
                "events": [e.value for e in self.config.event_types],
                "database_id": database_id,
                "secret": self.config.secret
            }
            
            response = await self.notion.create_webhook(webhook)
            logger.info(f"Registered webhook for {database_id}: {response['id']}")
    
    async def unregister_webhooks(self):
        """Clean up webhooks on shutdown"""
        webhooks = await self.notion.list_webhooks()
        for webhook in webhooks:
            if webhook["url"] == self.config.endpoint_url:
                await self.notion.delete_webhook(webhook["id"])
```

## Deployment Configuration

```yaml
# webhook_config.yaml
webhook:
  endpoint_url: "https://your-domain.com/webhooks/notion"
  secret: "${WEBHOOK_SECRET}"
  
  databases:
    - "Intelligence & Transcripts"
    - "People & Contacts"
    - "Actionable Tasks"
    - "Organizations & Bodies"
  
  events:
    - "page.created"
    - "page.updated"
    - "page.deleted"
  
  processing:
    queue_size: 1000
    workers: 4
    retry_attempts: 3
    retry_backoff: exponential
    
  debouncing:
    page_updates: 5s  # Ignore updates within 5 seconds
    
  triggers:
    new_transcript:
      action: "process_intelligence"
      async: true
    
    task_completed:
      action: "notify_assignee"
      async: false
```

## Local Development Setup

```python
# Local webhook testing with ngrok
class LocalWebhookTester:
    def __init__(self):
        self.ngrok_url = None
        
    async def setup_tunnel(self):
        """Setup ngrok tunnel for local testing"""
        import pyngrok
        
        # Start FastAPI on local port
        tunnel = pyngrok.ngrok.connect(8000)
        self.ngrok_url = tunnel.public_url
        
        print(f"Webhook URL: {self.ngrok_url}/webhooks/notion")
        
        # Update Notion webhook registration
        await self.register_with_notion(self.ngrok_url)
    
    async def simulate_webhook(self, event_type: str, page_id: str):
        """Simulate webhook for testing"""
        payload = {
            "event_type": event_type,
            "workspace_id": "test",
            "page_id": page_id,
            "timestamp": datetime.now().isoformat()
        }
        
        response = requests.post(
            "http://localhost:8000/webhooks/notion",
            json=payload,
            headers={"X-Notion-Signature": "test"}
        )
        
        return response.json()
```

## Error Handling

1. **Network Failures**: Exponential backoff retry
2. **Invalid Payloads**: Log and skip
3. **Rate Limits**: Queue and retry with delay
4. **Database Locks**: Implement optimistic locking
5. **Partial Updates**: Track update status per field

## Monitoring

```python
class WebhookMonitor:
    def __init__(self):
        self.metrics = {
            "events_received": 0,
            "events_processed": 0,
            "events_failed": 0,
            "processing_time": []
        }
    
    async def get_health(self) -> Dict:
        return {
            "status": "healthy",
            "queue_size": self.queue.qsize(),
            "metrics": self.metrics,
            "last_event": self.last_event_time
        }
```

## Testing Strategy

1. **Unit Tests**:
   - Webhook signature verification
   - Event filtering logic
   - Processor logic for each event type

2. **Integration Tests**:
   - End-to-end webhook flow
   - Cache update verification
   - Trigger execution

3. **Load Tests**:
   - Handle 1000 events/minute
   - Queue overflow handling
   - Memory usage under load

## Security Considerations

1. **Signature Verification**: Validate all webhooks
2. **Rate Limiting**: Prevent DoS attacks
3. **Input Validation**: Sanitize all inputs
4. **Secure Storage**: Encrypt webhook secrets
5. **Access Control**: Limit webhook endpoints

## Timeline

- Day 1: Basic webhook receiver
- Day 2: Event processors
- Day 3: Queue and retry logic
- Day 4: Testing and deployment setup