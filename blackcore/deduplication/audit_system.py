"""
Deduplication Audit System

Comprehensive audit trail and human review system for deduplication operations
with complete tracking, rollback capabilities, and quality assurance.
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import uuid

logger = logging.getLogger(__name__)


@dataclass
class ReviewTask:
    """A human review task for potential duplicates."""
    task_id: str
    database_name: str
    entity_pair: Dict[str, Any]
    priority: str  # 'high', 'medium', 'low'
    status: str  # 'pending', 'in_progress', 'completed', 'cancelled'
    created_at: datetime
    assigned_to: Optional[str] = None
    completed_at: Optional[datetime] = None
    decision: Optional[str] = None  # 'merge', 'separate', 'defer'
    reviewer_notes: Optional[str] = None
    confidence: Optional[float] = None
    ai_analysis: Optional[Dict[str, Any]] = None


@dataclass
class AuditRecord:
    """A complete audit record for a deduplication operation."""
    audit_id: str
    operation_type: str  # 'merge', 'separate', 'review_completed'
    database_name: str
    entity_ids: List[str]
    decision_maker: str  # 'system' or user ID
    timestamp: datetime
    confidence_score: float
    evidence: Dict[str, Any]
    before_state: Dict[str, Any]
    after_state: Dict[str, Any]
    rollback_info: Dict[str, Any]
    ai_analysis: Optional[Dict[str, Any]] = None


class DeduplicationAudit:
    """
    Comprehensive audit system for deduplication operations.
    
    Provides complete tracking of all decisions, human reviews, and changes
    with rollback capabilities and quality assurance workflows.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the audit system."""
        self.db_path = db_path or "deduplication_audit.db"
        self.init_database()
        
        # Statistics
        self.stats = {
            "total_reviews_created": 0,
            "completed_reviews": 0,
            "pending_reviews": 0,
            "merge_operations": 0,
            "separate_operations": 0,
            "rollback_operations": 0
        }
        
    def init_database(self):
        """Initialize the audit database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS review_tasks (
                        task_id TEXT PRIMARY KEY,
                        database_name TEXT NOT NULL,
                        entity_pair TEXT NOT NULL,
                        priority TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        assigned_to TEXT,
                        completed_at TEXT,
                        decision TEXT,
                        reviewer_notes TEXT,
                        confidence REAL,
                        ai_analysis TEXT
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS audit_records (
                        audit_id TEXT PRIMARY KEY,
                        operation_type TEXT NOT NULL,
                        database_name TEXT NOT NULL,
                        entity_ids TEXT NOT NULL,
                        decision_maker TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        confidence_score REAL NOT NULL,
                        evidence TEXT NOT NULL,
                        before_state TEXT NOT NULL,
                        after_state TEXT NOT NULL,
                        rollback_info TEXT NOT NULL,
                        ai_analysis TEXT
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS quality_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        metric_type TEXT NOT NULL,
                        metric_value REAL NOT NULL,
                        details TEXT
                    )
                ''')
                
                # Create indexes for performance
                conn.execute('CREATE INDEX IF NOT EXISTS idx_review_status ON review_tasks(status)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_review_priority ON review_tasks(priority)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_records(timestamp)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_audit_database ON audit_records(database_name)')
                
                conn.commit()
                logger.info("✅ Audit database initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize audit database: {e}")
            raise
            
    def create_review_task(self, database_name: str, entity_pair: Dict[str, Any], 
                          priority: str = "medium", ai_analysis: Optional[Dict[str, Any]] = None) -> str:
        """Create a new human review task."""
        task_id = str(uuid.uuid4())
        
        task = ReviewTask(
            task_id=task_id,
            database_name=database_name,
            entity_pair=entity_pair,
            priority=priority,
            status="pending",
            created_at=datetime.now(),
            ai_analysis=ai_analysis
        )
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO review_tasks 
                    (task_id, database_name, entity_pair, priority, status, created_at, ai_analysis)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task.task_id,
                    task.database_name,
                    json.dumps(task.entity_pair),
                    task.priority,
                    task.status,
                    task.created_at.isoformat(),
                    json.dumps(task.ai_analysis) if task.ai_analysis else None
                ))
                
                conn.commit()
                
            self.stats["total_reviews_created"] += 1
            self.stats["pending_reviews"] += 1
            
            logger.info(f"📋 Created review task {task_id} for {database_name}")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to create review task: {e}")
            raise
            
    def assign_review_task(self, task_id: str, reviewer_id: str) -> bool:
        """Assign a review task to a reviewer."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    UPDATE review_tasks 
                    SET assigned_to = ?, status = 'in_progress'
                    WHERE task_id = ? AND status = 'pending'
                ''', (reviewer_id, task_id))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"📋 Assigned task {task_id} to {reviewer_id}")
                    return True
                else:
                    logger.warning(f"Task {task_id} not found or not available for assignment")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to assign review task: {e}")
            return False
            
    def complete_review_task(self, task_id: str, reviewer_id: str, decision: str, 
                           confidence: float, notes: Optional[str] = None) -> bool:
        """Complete a review task with a decision."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    UPDATE review_tasks 
                    SET status = 'completed', completed_at = ?, decision = ?, 
                        reviewer_notes = ?, confidence = ?
                    WHERE task_id = ? AND assigned_to = ?
                ''', (
                    datetime.now().isoformat(),
                    decision,
                    notes,
                    confidence,
                    task_id,
                    reviewer_id
                ))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    
                    # Update statistics
                    self.stats["completed_reviews"] += 1
                    self.stats["pending_reviews"] -= 1
                    
                    # Create audit record for the decision
                    self._create_review_audit_record(task_id, reviewer_id, decision, confidence)
                    
                    logger.info(f"✅ Completed review task {task_id} with decision: {decision}")
                    return True
                else:
                    logger.warning(f"Task {task_id} not found or not assigned to {reviewer_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to complete review task: {e}")
            return False
            
    def _create_review_audit_record(self, task_id: str, reviewer_id: str, decision: str, confidence: float):
        """Create audit record for completed review."""
        try:
            # Get task details
            task = self.get_review_task(task_id)
            if not task:
                return
                
            audit_id = str(uuid.uuid4())
            
            audit_record = AuditRecord(
                audit_id=audit_id,
                operation_type="review_completed",
                database_name=task.database_name,
                entity_ids=[
                    str(task.entity_pair.get("entity_a", {}).get("id", "unknown")),
                    str(task.entity_pair.get("entity_b", {}).get("id", "unknown"))
                ],
                decision_maker=reviewer_id,
                timestamp=datetime.now(),
                confidence_score=confidence,
                evidence={"review_task_id": task_id, "decision": decision},
                before_state={"status": "pending_review"},
                after_state={"status": "reviewed", "decision": decision},
                rollback_info={"review_task_id": task_id},
                ai_analysis=task.ai_analysis
            )
            
            self._save_audit_record(audit_record)
            
        except Exception as e:
            logger.error(f"Failed to create review audit record: {e}")
            
    def create_merge_audit_record(self, database_name: str, primary_entity: Dict[str, Any], 
                                secondary_entity: Dict[str, Any], decision_maker: str,
                                confidence_score: float, evidence: Dict[str, Any],
                                ai_analysis: Optional[Dict[str, Any]] = None) -> str:
        """Create audit record for a merge operation."""
        audit_id = str(uuid.uuid4())
        
        audit_record = AuditRecord(
            audit_id=audit_id,
            operation_type="merge",
            database_name=database_name,
            entity_ids=[
                str(primary_entity.get("id", "unknown")),
                str(secondary_entity.get("id", "unknown"))
            ],
            decision_maker=decision_maker,
            timestamp=datetime.now(),
            confidence_score=confidence_score,
            evidence=evidence,
            before_state={
                "primary_entity": primary_entity,
                "secondary_entity": secondary_entity
            },
            after_state={
                "merged_entity": primary_entity,  # Will be updated after merge
                "archived_entity": secondary_entity
            },
            rollback_info={
                "original_entities": [primary_entity, secondary_entity],
                "merge_timestamp": datetime.now().isoformat()
            },
            ai_analysis=ai_analysis
        )
        
        self._save_audit_record(audit_record)
        self.stats["merge_operations"] += 1
        
        logger.info(f"📝 Created merge audit record {audit_id}")
        return audit_id
        
    def _save_audit_record(self, record: AuditRecord):
        """Save audit record to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO audit_records 
                    (audit_id, operation_type, database_name, entity_ids, decision_maker,
                     timestamp, confidence_score, evidence, before_state, after_state,
                     rollback_info, ai_analysis)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record.audit_id,
                    record.operation_type,
                    record.database_name,
                    json.dumps(record.entity_ids),
                    record.decision_maker,
                    record.timestamp.isoformat(),
                    record.confidence_score,
                    json.dumps(record.evidence),
                    json.dumps(record.before_state),
                    json.dumps(record.after_state),
                    json.dumps(record.rollback_info),
                    json.dumps(record.ai_analysis) if record.ai_analysis else None
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save audit record: {e}")
            raise
            
    def get_pending_reviews(self, reviewer_id: Optional[str] = None, 
                          priority: Optional[str] = None) -> List[ReviewTask]:
        """Get pending review tasks."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = 'SELECT * FROM review_tasks WHERE status = ?'
                params = ['pending']
                
                if reviewer_id:
                    query += ' AND assigned_to = ?'
                    params.append(reviewer_id)
                    
                if priority:
                    query += ' AND priority = ?'
                    params.append(priority)
                    
                query += ' ORDER BY created_at ASC'
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                tasks = []
                for row in rows:
                    task = ReviewTask(
                        task_id=row[0],
                        database_name=row[1],
                        entity_pair=json.loads(row[2]),
                        priority=row[3],
                        status=row[4],
                        created_at=datetime.fromisoformat(row[5]),
                        assigned_to=row[6],
                        completed_at=datetime.fromisoformat(row[7]) if row[7] else None,
                        decision=row[8],
                        reviewer_notes=row[9],
                        confidence=row[10],
                        ai_analysis=json.loads(row[11]) if row[11] else None
                    )
                    tasks.append(task)
                    
                return tasks
                
        except Exception as e:
            logger.error(f"Failed to get pending reviews: {e}")
            return []
            
    def get_review_task(self, task_id: str) -> Optional[ReviewTask]:
        """Get a specific review task."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT * FROM review_tasks WHERE task_id = ?', (task_id,))
                row = cursor.fetchone()
                
                if row:
                    return ReviewTask(
                        task_id=row[0],
                        database_name=row[1],
                        entity_pair=json.loads(row[2]),
                        priority=row[3],
                        status=row[4],
                        created_at=datetime.fromisoformat(row[5]),
                        assigned_to=row[6],
                        completed_at=datetime.fromisoformat(row[7]) if row[7] else None,
                        decision=row[8],
                        reviewer_notes=row[9],
                        confidence=row[10],
                        ai_analysis=json.loads(row[11]) if row[11] else None
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get review task: {e}")
            return None
            
    def get_audit_history(self, database_name: Optional[str] = None, 
                         operation_type: Optional[str] = None,
                         days_back: int = 30) -> List[AuditRecord]:
        """Get audit history with optional filters."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = 'SELECT * FROM audit_records WHERE timestamp >= ?'
                params = [(datetime.now() - timedelta(days=days_back)).isoformat()]
                
                if database_name:
                    query += ' AND database_name = ?'
                    params.append(database_name)
                    
                if operation_type:
                    query += ' AND operation_type = ?'
                    params.append(operation_type)
                    
                query += ' ORDER BY timestamp DESC'
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                records = []
                for row in rows:
                    record = AuditRecord(
                        audit_id=row[0],
                        operation_type=row[1],
                        database_name=row[2],
                        entity_ids=json.loads(row[3]),
                        decision_maker=row[4],
                        timestamp=datetime.fromisoformat(row[5]),
                        confidence_score=row[6],
                        evidence=json.loads(row[7]),
                        before_state=json.loads(row[8]),
                        after_state=json.loads(row[9]),
                        rollback_info=json.loads(row[10]),
                        ai_analysis=json.loads(row[11]) if row[11] else None
                    )
                    records.append(record)
                    
                return records
                
        except Exception as e:
            logger.error(f"Failed to get audit history: {e}")
            return []
            
    def rollback_operation(self, audit_id: str, rollback_reason: str) -> bool:
        """Rollback a previous operation."""
        try:
            # Get the audit record
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT * FROM audit_records WHERE audit_id = ?', (audit_id,))
                row = cursor.fetchone()
                
                if not row:
                    logger.error(f"Audit record {audit_id} not found")
                    return False
                    
                # Parse the audit record
                record = AuditRecord(
                    audit_id=row[0],
                    operation_type=row[1],
                    database_name=row[2],
                    entity_ids=json.loads(row[3]),
                    decision_maker=row[4],
                    timestamp=datetime.fromisoformat(row[5]),
                    confidence_score=row[6],
                    evidence=json.loads(row[7]),
                    before_state=json.loads(row[8]),
                    after_state=json.loads(row[9]),
                    rollback_info=json.loads(row[10]),
                    ai_analysis=json.loads(row[11]) if row[11] else None
                )
                
                # Create rollback audit record
                rollback_audit_id = str(uuid.uuid4())
                rollback_record = AuditRecord(
                    audit_id=rollback_audit_id,
                    operation_type="rollback",
                    database_name=record.database_name,
                    entity_ids=record.entity_ids,
                    decision_maker="system",  # System-initiated rollback
                    timestamp=datetime.now(),
                    confidence_score=100.0,  # High confidence in rollback
                    evidence={"original_audit_id": audit_id, "rollback_reason": rollback_reason},
                    before_state=record.after_state,
                    after_state=record.before_state,
                    rollback_info={"original_operation": record.operation_type},
                    ai_analysis=None
                )
                
                self._save_audit_record(rollback_record)
                self.stats["rollback_operations"] += 1
                
                logger.info(f"🔄 Rollback completed for operation {audit_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to rollback operation: {e}")
            return False
            
    def get_quality_metrics(self, days_back: int = 30) -> Dict[str, Any]:
        """Get quality metrics for the specified period."""
        try:
            start_date = (datetime.now() - timedelta(days=days_back)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                # Get review completion stats
                cursor = conn.execute('''
                    SELECT COUNT(*) as total, 
                           AVG(confidence) as avg_confidence,
                           decision
                    FROM review_tasks 
                    WHERE completed_at >= ? AND status = 'completed'
                    GROUP BY decision
                ''', (start_date,))
                
                review_stats = {}
                for row in cursor.fetchall():
                    review_stats[row[2]] = {
                        "count": row[0],
                        "avg_confidence": row[1] or 0
                    }
                    
                # Get audit operation stats
                cursor = conn.execute('''
                    SELECT operation_type, COUNT(*) as count, AVG(confidence_score) as avg_confidence
                    FROM audit_records 
                    WHERE timestamp >= ?
                    GROUP BY operation_type
                ''', (start_date,))
                
                operation_stats = {}
                for row in cursor.fetchall():
                    operation_stats[row[0]] = {
                        "count": row[1],
                        "avg_confidence": row[2] or 0
                    }
                    
                return {
                    "period_days": days_back,
                    "review_decisions": review_stats,
                    "operations": operation_stats,
                    "system_stats": self.stats.copy()
                }
                
        except Exception as e:
            logger.error(f"Failed to get quality metrics: {e}")
            return {}
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get audit system statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get review task counts by status
                cursor = conn.execute('SELECT status, COUNT(*) FROM review_tasks GROUP BY status')
                review_status_counts = dict(cursor.fetchall())
                
                # Get audit record counts by type
                cursor = conn.execute('SELECT operation_type, COUNT(*) FROM audit_records GROUP BY operation_type')
                audit_type_counts = dict(cursor.fetchall())
                
                return {
                    "review_tasks": review_status_counts,
                    "audit_records": audit_type_counts,
                    "runtime_stats": self.stats.copy(),
                    "database_path": self.db_path
                }
                
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return self.stats.copy()