"""
LLM Evaluation Framework for Entity Extraction Quality

Provides comprehensive evaluation metrics, ground truth comparison,
and quality assessment for LLM-based entity extraction.
"""

import json
import time
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from pathlib import Path
import numpy as np

from .models import ExtractedEntities, ExtractedEntity, EntityType, ExtractedRelationship
from .ai_extractor import AIExtractor


@dataclass
class EntityMatch:
    """Represents a match between predicted and ground truth entities."""
    predicted: ExtractedEntity
    ground_truth: ExtractedEntity
    score: float
    match_type: str  # exact, partial, false_positive, false_negative


@dataclass
class EvaluationMetrics:
    """Comprehensive metrics for entity extraction evaluation."""
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    
    # Per entity type metrics
    type_metrics: Dict[EntityType, Dict[str, float]] = field(default_factory=dict)
    
    # Confidence calibration
    confidence_correlation: float = 0.0
    avg_confidence: float = 0.0
    
    # Performance metrics
    extraction_time_ms: float = 0.0
    tokens_used: int = 0
    
    # Detailed breakdowns
    confusion_matrix: Dict[str, Dict[str, int]] = field(default_factory=dict)
    error_analysis: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class GroundTruthExample:
    """Ground truth example for evaluation."""
    transcript: str
    entities: List[ExtractedEntity]
    relationships: List[ExtractedRelationship]
    metadata: Dict[str, Any] = field(default_factory=dict)
    

class LLMEvaluator:
    """Evaluates LLM entity extraction quality against ground truth."""
    
    def __init__(self, similarity_threshold: float = 0.8):
        """Initialize evaluator with similarity threshold."""
        self.similarity_threshold = similarity_threshold
        self.evaluation_history: List[Dict[str, Any]] = []
        
    def evaluate_extraction(
        self,
        predicted: ExtractedEntities,
        ground_truth: GroundTruthExample,
        extraction_time_ms: float = 0.0,
        tokens_used: int = 0
    ) -> EvaluationMetrics:
        """Evaluate predicted entities against ground truth.
        
        Args:
            predicted: Extracted entities from LLM
            ground_truth: Ground truth example
            extraction_time_ms: Time taken for extraction
            tokens_used: Number of tokens used
            
        Returns:
            Comprehensive evaluation metrics
        """
        # Match entities
        matches = self._match_entities(predicted.entities, ground_truth.entities)
        
        # Calculate basic metrics
        true_positives = sum(1 for m in matches if m.match_type in ['exact', 'partial'])
        false_positives = sum(1 for m in matches if m.match_type == 'false_positive')
        false_negatives = sum(1 for m in matches if m.match_type == 'false_negative')
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        accuracy = true_positives / len(matches) if matches else 0
        
        # Calculate per-type metrics
        type_metrics = self._calculate_type_metrics(matches)
        
        # Calculate confidence calibration
        confidence_correlation = self._calculate_confidence_correlation(matches)
        avg_confidence = np.mean([e.confidence for e in predicted.entities]) if predicted.entities else 0
        
        # Build confusion matrix
        confusion_matrix = self._build_confusion_matrix(matches)
        
        # Analyze errors
        error_analysis = self._analyze_errors(matches, predicted, ground_truth)
        
        return EvaluationMetrics(
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            accuracy=accuracy,
            type_metrics=type_metrics,
            confidence_correlation=confidence_correlation,
            avg_confidence=avg_confidence,
            extraction_time_ms=extraction_time_ms,
            tokens_used=tokens_used,
            confusion_matrix=confusion_matrix,
            error_analysis=error_analysis
        )
    
    def evaluate_batch(
        self,
        extractor: AIExtractor,
        ground_truth_examples: List[GroundTruthExample],
        verbose: bool = False
    ) -> Dict[str, Any]:
        """Evaluate extractor on multiple examples.
        
        Args:
            extractor: AI extractor to evaluate
            ground_truth_examples: List of ground truth examples
            verbose: Whether to print progress
            
        Returns:
            Aggregated evaluation results
        """
        all_metrics = []
        total_time = 0
        total_tokens = 0
        
        for i, example in enumerate(ground_truth_examples):
            if verbose:
                print(f"Evaluating example {i+1}/{len(ground_truth_examples)}...")
            
            # Extract entities
            start_time = time.time()
            predicted = extractor.extract_entities(example.transcript)
            extraction_time = (time.time() - start_time) * 1000  # ms
            
            # Evaluate
            metrics = self.evaluate_extraction(
                predicted,
                example,
                extraction_time_ms=extraction_time,
                tokens_used=0  # Would need to track from extractor
            )
            
            all_metrics.append(metrics)
            total_time += extraction_time
            total_tokens += metrics.tokens_used
        
        # Aggregate results
        return self._aggregate_metrics(all_metrics, total_time, total_tokens)
    
    def _match_entities(
        self,
        predicted: List[ExtractedEntity],
        ground_truth: List[ExtractedEntity]
    ) -> List[EntityMatch]:
        """Match predicted entities to ground truth."""
        matches = []
        matched_gt = set()
        
        # Match predicted to ground truth
        for pred in predicted:
            best_match = None
            best_score = 0
            
            for i, gt in enumerate(ground_truth):
                if i in matched_gt:
                    continue
                    
                score = self._calculate_entity_similarity(pred, gt)
                if score > best_score and score >= self.similarity_threshold:
                    best_match = i
                    best_score = score
            
            if best_match is not None:
                matched_gt.add(best_match)
                match_type = 'exact' if best_score >= 0.95 else 'partial'
                matches.append(EntityMatch(
                    predicted=pred,
                    ground_truth=ground_truth[best_match],
                    score=best_score,
                    match_type=match_type
                ))
            else:
                matches.append(EntityMatch(
                    predicted=pred,
                    ground_truth=None,
                    score=0,
                    match_type='false_positive'
                ))
        
        # Add false negatives
        for i, gt in enumerate(ground_truth):
            if i not in matched_gt:
                matches.append(EntityMatch(
                    predicted=None,
                    ground_truth=gt,
                    score=0,
                    match_type='false_negative'
                ))
        
        return matches
    
    def _calculate_entity_similarity(
        self,
        entity1: ExtractedEntity,
        entity2: ExtractedEntity
    ) -> float:
        """Calculate similarity between two entities."""
        if entity1.type != entity2.type:
            return 0.0
        
        # Name similarity (simple for now, could use more sophisticated methods)
        name_similarity = self._string_similarity(entity1.name, entity2.name)
        
        # Property overlap
        if entity1.properties and entity2.properties:
            common_keys = set(entity1.properties.keys()) & set(entity2.properties.keys())
            if common_keys:
                prop_matches = sum(
                    1 for k in common_keys 
                    if entity1.properties.get(k) == entity2.properties.get(k)
                )
                prop_similarity = prop_matches / len(common_keys)
            else:
                prop_similarity = 0
        else:
            prop_similarity = 0.5  # Neutral if no properties
        
        # Weight name more heavily
        return 0.7 * name_similarity + 0.3 * prop_similarity
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate simple string similarity."""
        s1_lower = s1.lower()
        s2_lower = s2.lower()
        
        if s1_lower == s2_lower:
            return 1.0
        
        # Check if one contains the other
        if s1_lower in s2_lower or s2_lower in s1_lower:
            return 0.8
        
        # Simple character overlap
        chars1 = set(s1_lower.split())
        chars2 = set(s2_lower.split())
        if chars1 and chars2:
            overlap = len(chars1 & chars2) / len(chars1 | chars2)
            return overlap
        
        return 0.0
    
    def _calculate_type_metrics(
        self,
        matches: List[EntityMatch]
    ) -> Dict[EntityType, Dict[str, float]]:
        """Calculate metrics per entity type."""
        type_metrics = {}
        
        for entity_type in EntityType:
            type_matches = [
                m for m in matches 
                if (m.predicted and m.predicted.type == entity_type) or
                   (m.ground_truth and m.ground_truth.type == entity_type)
            ]
            
            if not type_matches:
                continue
            
            tp = sum(1 for m in type_matches if m.match_type in ['exact', 'partial'])
            fp = sum(1 for m in type_matches if m.match_type == 'false_positive')
            fn = sum(1 for m in type_matches if m.match_type == 'false_negative')
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            type_metrics[entity_type] = {
                'precision': precision,
                'recall': recall,
                'f1_score': f1,
                'support': len(type_matches)
            }
        
        return type_metrics
    
    def _calculate_confidence_correlation(
        self,
        matches: List[EntityMatch]
    ) -> float:
        """Calculate correlation between confidence and correctness."""
        confidences = []
        correct = []
        
        for match in matches:
            if match.predicted:
                confidences.append(match.predicted.confidence)
                correct.append(1 if match.match_type in ['exact', 'partial'] else 0)
        
        if len(confidences) < 2:
            return 0.0
        
        # Simple correlation coefficient
        return np.corrcoef(confidences, correct)[0, 1]
    
    def _build_confusion_matrix(
        self,
        matches: List[EntityMatch]
    ) -> Dict[str, Dict[str, int]]:
        """Build confusion matrix for entity types."""
        matrix = defaultdict(lambda: defaultdict(int))
        
        for match in matches:
            if match.match_type in ['exact', 'partial']:
                pred_type = match.predicted.type.value
                true_type = match.ground_truth.type.value
                matrix[true_type][pred_type] += 1
            elif match.match_type == 'false_positive':
                pred_type = match.predicted.type.value
                matrix['none'][pred_type] += 1
            elif match.match_type == 'false_negative':
                true_type = match.ground_truth.type.value
                matrix[true_type]['none'] += 1
        
        return dict(matrix)
    
    def _analyze_errors(
        self,
        matches: List[EntityMatch],
        predicted: ExtractedEntities,
        ground_truth: GroundTruthExample
    ) -> Dict[str, List[str]]:
        """Analyze extraction errors."""
        errors = defaultdict(list)
        
        for match in matches:
            if match.match_type == 'false_positive':
                errors['false_positives'].append(
                    f"{match.predicted.type.value}: {match.predicted.name}"
                )
            elif match.match_type == 'false_negative':
                errors['false_negatives'].append(
                    f"{match.ground_truth.type.value}: {match.ground_truth.name}"
                )
            elif match.match_type == 'partial':
                errors['partial_matches'].append(
                    f"{match.predicted.name} ≈ {match.ground_truth.name} (score: {match.score:.2f})"
                )
        
        # Check for type mismatches
        for match in matches:
            if match.match_type in ['exact', 'partial'] and match.predicted.type != match.ground_truth.type:
                errors['type_mismatches'].append(
                    f"{match.ground_truth.name}: {match.ground_truth.type.value} → {match.predicted.type.value}"
                )
        
        return dict(errors)
    
    def _aggregate_metrics(
        self,
        metrics_list: List[EvaluationMetrics],
        total_time: float,
        total_tokens: int
    ) -> Dict[str, Any]:
        """Aggregate metrics from multiple evaluations."""
        if not metrics_list:
            return {}
        
        # Average basic metrics
        avg_metrics = {
            'precision': np.mean([m.precision for m in metrics_list]),
            'recall': np.mean([m.recall for m in metrics_list]),
            'f1_score': np.mean([m.f1_score for m in metrics_list]),
            'accuracy': np.mean([m.accuracy for m in metrics_list]),
            'confidence_correlation': np.mean([m.confidence_correlation for m in metrics_list]),
            'avg_confidence': np.mean([m.avg_confidence for m in metrics_list]),
        }
        
        # Aggregate per-type metrics
        all_type_metrics = defaultdict(list)
        for m in metrics_list:
            for entity_type, type_metric in m.type_metrics.items():
                all_type_metrics[entity_type].append(type_metric)
        
        avg_type_metrics = {}
        for entity_type, metric_list in all_type_metrics.items():
            avg_type_metrics[entity_type.value] = {
                'precision': np.mean([m['precision'] for m in metric_list]),
                'recall': np.mean([m['recall'] for m in metric_list]),
                'f1_score': np.mean([m['f1_score'] for m in metric_list]),
                'support': sum([m['support'] for m in metric_list])
            }
        
        # Performance metrics
        performance_metrics = {
            'total_examples': len(metrics_list),
            'total_time_ms': total_time,
            'avg_time_ms': total_time / len(metrics_list),
            'total_tokens': total_tokens,
            'avg_tokens': total_tokens / len(metrics_list) if len(metrics_list) > 0 else 0
        }
        
        # Aggregate error analysis
        all_errors = defaultdict(list)
        for m in metrics_list:
            for error_type, errors in m.error_analysis.items():
                all_errors[error_type].extend(errors)
        
        return {
            'overall_metrics': avg_metrics,
            'type_metrics': avg_type_metrics,
            'performance': performance_metrics,
            'error_summary': {
                error_type: {
                    'count': len(errors),
                    'examples': errors[:5]  # First 5 examples
                }
                for error_type, errors in all_errors.items()
            }
        }
    
    def save_evaluation_report(
        self,
        results: Dict[str, Any],
        output_path: Path,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Save evaluation results to JSON report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'evaluator_config': {
                'similarity_threshold': self.similarity_threshold
            },
            'results': results,
            'metadata': metadata or {}
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
    
    def compare_models(
        self,
        models: List[Tuple[str, AIExtractor]],
        ground_truth_examples: List[GroundTruthExample],
        verbose: bool = False
    ) -> Dict[str, Any]:
        """Compare multiple models on the same dataset.
        
        Args:
            models: List of (name, extractor) tuples
            ground_truth_examples: Test dataset
            verbose: Whether to print progress
            
        Returns:
            Comparison results
        """
        comparison_results = {}
        
        for model_name, extractor in models:
            if verbose:
                print(f"\nEvaluating model: {model_name}")
            
            results = self.evaluate_batch(extractor, ground_truth_examples, verbose)
            comparison_results[model_name] = results
        
        # Add comparison summary
        comparison_results['summary'] = self._create_comparison_summary(comparison_results)
        
        return comparison_results
    
    def _create_comparison_summary(
        self,
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create summary comparing model results."""
        summary = {
            'best_f1_score': None,
            'best_precision': None,
            'best_recall': None,
            'fastest_model': None,
            'most_cost_effective': None
        }
        
        model_names = [k for k in results.keys() if k != 'summary']
        
        if not model_names:
            return summary
        
        # Find best metrics
        f1_scores = {
            name: results[name]['overall_metrics']['f1_score'] 
            for name in model_names
        }
        summary['best_f1_score'] = max(f1_scores.items(), key=lambda x: x[1])
        
        precision_scores = {
            name: results[name]['overall_metrics']['precision']
            for name in model_names
        }
        summary['best_precision'] = max(precision_scores.items(), key=lambda x: x[1])
        
        recall_scores = {
            name: results[name]['overall_metrics']['recall']
            for name in model_names
        }
        summary['best_recall'] = max(recall_scores.items(), key=lambda x: x[1])
        
        # Find fastest
        avg_times = {
            name: results[name]['performance']['avg_time_ms']
            for name in model_names
        }
        summary['fastest_model'] = min(avg_times.items(), key=lambda x: x[1])
        
        return summary


class GroundTruthBuilder:
    """Helper class to build ground truth datasets."""
    
    @staticmethod
    def from_json(json_path: Path) -> List[GroundTruthExample]:
        """Load ground truth from JSON file."""
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        examples = []
        for item in data:
            entities = [
                ExtractedEntity(
                    name=e['name'],
                    type=EntityType(e['type']),
                    properties=e.get('properties', {}),
                    context=e.get('context', ''),
                    confidence=e.get('confidence', 1.0)
                )
                for e in item['entities']
            ]
            
            relationships = [
                ExtractedRelationship(
                    source_entity=r['source_entity'],
                    source_type=EntityType(r['source_type']),
                    target_entity=r['target_entity'],
                    target_type=EntityType(r['target_type']),
                    relationship_type=r['relationship_type']
                )
                for r in item.get('relationships', [])
            ]
            
            examples.append(GroundTruthExample(
                transcript=item['transcript'],
                entities=entities,
                relationships=relationships,
                metadata=item.get('metadata', {})
            ))
        
        return examples
    
    @staticmethod
    def save_to_json(examples: List[GroundTruthExample], output_path: Path):
        """Save ground truth examples to JSON."""
        data = []
        for example in examples:
            data.append({
                'transcript': example.transcript,
                'entities': [
                    {
                        'name': e.name,
                        'type': e.type.value,
                        'properties': e.properties,
                        'context': e.context,
                        'confidence': e.confidence
                    }
                    for e in example.entities
                ],
                'relationships': [
                    {
                        'source_entity': r.source_entity,
                        'source_type': r.source_type.value,
                        'target_entity': r.target_entity,
                        'target_type': r.target_type.value,
                        'relationship_type': r.relationship_type
                    }
                    for r in example.relationships
                ],
                'metadata': example.metadata
            })
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)