"""
A/B Testing Framework for LLM Model Comparison

Provides statistical analysis and comparison tools for evaluating
different models, prompts, and configurations.
"""

import json
import time
import hashlib
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
import numpy as np
from scipy import stats
from concurrent.futures import ThreadPoolExecutor, as_completed

from .ai_extractor import AIExtractor
from .llm_evaluation import LLMEvaluator, GroundTruthExample, EvaluationMetrics
from .response_validation import ResponseValidator, ValidationResult
from .models import ExtractedEntities


@dataclass
class TestVariant:
    """Configuration for a test variant."""
    name: str
    extractor: AIExtractor
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ABTestResult:
    """Result from an A/B test comparison."""
    variant_name: str
    sample_size: int
    metrics: Dict[str, float]
    confidence_intervals: Dict[str, Tuple[float, float]]
    cost_per_sample: Decimal
    avg_latency_ms: float
    validation_score: float
    errors: List[str] = field(default_factory=list)


@dataclass
class StatisticalSignificance:
    """Statistical significance analysis results."""
    metric: str
    variant_a: str
    variant_b: str
    p_value: float
    effect_size: float
    is_significant: bool
    confidence_level: float
    recommendation: str


class ABTestingFramework:
    """Framework for A/B testing LLM configurations."""
    
    def __init__(
        self,
        evaluator: Optional[LLMEvaluator] = None,
        validator: Optional[ResponseValidator] = None,
        confidence_level: float = 0.95,
        min_sample_size: int = 30
    ):
        """Initialize A/B testing framework.
        
        Args:
            evaluator: LLM evaluator instance
            validator: Response validator instance
            confidence_level: Statistical confidence level
            min_sample_size: Minimum samples for significance
        """
        self.evaluator = evaluator or LLMEvaluator()
        self.validator = validator or ResponseValidator()
        self.confidence_level = confidence_level
        self.min_sample_size = min_sample_size
        self.test_history = []
        
    def run_ab_test(
        self,
        variants: List[TestVariant],
        test_samples: List[GroundTruthExample],
        metrics_to_track: Optional[List[str]] = None,
        parallel: bool = True,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """Run A/B test comparing multiple variants.
        
        Args:
            variants: Test variants to compare
            test_samples: Ground truth samples
            metrics_to_track: Specific metrics to focus on
            parallel: Whether to run tests in parallel
            verbose: Print progress
            
        Returns:
            Complete test results and analysis
        """
        if metrics_to_track is None:
            metrics_to_track = ['f1_score', 'precision', 'recall', 'latency_ms', 'cost']
        
        # Ensure sufficient sample size
        if len(test_samples) < self.min_sample_size:
            raise ValueError(
                f"Insufficient samples: {len(test_samples)} < {self.min_sample_size}"
            )
        
        # Run tests for each variant
        variant_results = {}
        
        for variant in variants:
            if verbose:
                print(f"\nTesting variant: {variant.name}")
            
            results = self._test_variant(
                variant,
                test_samples,
                parallel,
                verbose
            )
            
            variant_results[variant.name] = results
        
        # Perform statistical analysis
        significance_tests = self._perform_significance_tests(
            variant_results,
            metrics_to_track
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            variant_results,
            significance_tests
        )
        
        # Create summary
        summary = {
            'test_date': datetime.now().isoformat(),
            'sample_size': len(test_samples),
            'variants_tested': len(variants),
            'variant_results': variant_results,
            'significance_tests': significance_tests,
            'recommendations': recommendations,
            'best_variant_by_metric': self._find_best_variants(variant_results)
        }
        
        self.test_history.append(summary)
        
        return summary
    
    def run_prompt_comparison(
        self,
        base_extractor: AIExtractor,
        prompts: Dict[str, str],
        test_samples: List[GroundTruthExample],
        verbose: bool = False
    ) -> Dict[str, Any]:
        """Compare different prompts using the same model.
        
        Args:
            base_extractor: Base extractor configuration
            prompts: Dict of prompt_name -> prompt_text
            test_samples: Test samples
            verbose: Print progress
            
        Returns:
            Prompt comparison results
        """
        # Create variants for each prompt
        variants = []
        
        for prompt_name, prompt_text in prompts.items():
            # Create extractor with custom prompt
            extractor = AIExtractor(
                provider=base_extractor.provider_name,
                api_key=base_extractor.provider.api_key,
                model=base_extractor.provider.model
            )
            
            # Override extract method to use custom prompt
            original_extract = extractor.extract_entities
            
            def extract_with_prompt(transcript, custom_prompt=None):
                return original_extract(transcript, prompt_text)
            
            extractor.extract_entities = extract_with_prompt
            
            variants.append(TestVariant(
                name=prompt_name,
                extractor=extractor,
                config={'prompt': prompt_text}
            ))
        
        # Run A/B test
        return self.run_ab_test(variants, test_samples, verbose=verbose)
    
    def run_model_comparison(
        self,
        models: Dict[str, Dict[str, Any]],
        test_samples: List[GroundTruthExample],
        verbose: bool = False
    ) -> Dict[str, Any]:
        """Compare different models.
        
        Args:
            models: Dict of model_name -> model_config
            test_samples: Test samples
            verbose: Print progress
            
        Returns:
            Model comparison results
        """
        variants = []
        
        for model_name, config in models.items():
            extractor = AIExtractor(
                provider=config['provider'],
                api_key=config['api_key'],
                model=config.get('model', model_name)
            )
            
            variants.append(TestVariant(
                name=model_name,
                extractor=extractor,
                config=config
            ))
        
        return self.run_ab_test(variants, test_samples, verbose=verbose)
    
    def _test_variant(
        self,
        variant: TestVariant,
        samples: List[GroundTruthExample],
        parallel: bool,
        verbose: bool
    ) -> ABTestResult:
        """Test a single variant."""
        results = []
        costs = []
        latencies = []
        validation_scores = []
        errors = []
        
        # Function to test single sample
        def test_sample(sample):
            try:
                # Time the extraction
                start_time = time.time()
                extracted = variant.extractor.extract_entities(sample.transcript)
                latency_ms = (time.time() - start_time) * 1000
                
                # Evaluate
                metrics = self.evaluator.evaluate_extraction(
                    extracted,
                    sample,
                    extraction_time_ms=latency_ms
                )
                
                # Validate
                validation = self.validator.validate_response(
                    extracted,
                    sample.transcript
                )
                
                # Estimate cost (simplified)
                tokens = len(sample.transcript) // 4
                cost = Decimal(tokens) * Decimal("0.001")  # Placeholder
                
                return {
                    'metrics': metrics,
                    'validation': validation,
                    'cost': cost,
                    'latency_ms': latency_ms,
                    'success': True
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e)
                }
        
        # Run tests
        if parallel:
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(test_sample, s) for s in samples]
                
                for future in as_completed(futures):
                    result = future.result()
                    if result['success']:
                        results.append(result['metrics'])
                        costs.append(result['cost'])
                        latencies.append(result['latency_ms'])
                        validation_scores.append(result['validation'].quality_score)
                    else:
                        errors.append(result['error'])
        else:
            for sample in samples:
                if verbose and len(results) % 10 == 0:
                    print(f"  Progress: {len(results)}/{len(samples)}")
                    
                result = test_sample(sample)
                if result['success']:
                    results.append(result['metrics'])
                    costs.append(result['cost'])
                    latencies.append(result['latency_ms'])
                    validation_scores.append(result['validation'].quality_score)
                else:
                    errors.append(result['error'])
        
        # Calculate aggregate metrics
        if results:
            aggregate_metrics = {
                'f1_score': np.mean([r.f1_score for r in results]),
                'precision': np.mean([r.precision for r in results]),
                'recall': np.mean([r.recall for r in results]),
                'accuracy': np.mean([r.accuracy for r in results]),
                'confidence_correlation': np.mean([r.confidence_correlation for r in results])
            }
            
            # Calculate confidence intervals
            confidence_intervals = {}
            for metric, values in aggregate_metrics.items():
                metric_values = [getattr(r, metric) for r in results]
                ci = self._calculate_confidence_interval(metric_values)
                confidence_intervals[metric] = ci
            
            return ABTestResult(
                variant_name=variant.name,
                sample_size=len(results),
                metrics=aggregate_metrics,
                confidence_intervals=confidence_intervals,
                cost_per_sample=Decimal(np.mean([float(c) for c in costs])),
                avg_latency_ms=np.mean(latencies),
                validation_score=np.mean(validation_scores),
                errors=errors
            )
        else:
            return ABTestResult(
                variant_name=variant.name,
                sample_size=0,
                metrics={},
                confidence_intervals={},
                cost_per_sample=Decimal("0"),
                avg_latency_ms=0,
                validation_score=0,
                errors=errors
            )
    
    def _calculate_confidence_interval(
        self,
        data: List[float]
    ) -> Tuple[float, float]:
        """Calculate confidence interval for data."""
        if not data:
            return (0, 0)
        
        mean = np.mean(data)
        std_err = stats.sem(data)
        interval = std_err * stats.t.ppf((1 + self.confidence_level) / 2, len(data) - 1)
        
        return (mean - interval, mean + interval)
    
    def _perform_significance_tests(
        self,
        results: Dict[str, ABTestResult],
        metrics: List[str]
    ) -> List[StatisticalSignificance]:
        """Perform statistical significance tests between variants."""
        significance_results = []
        variant_names = list(results.keys())
        
        # Compare each pair of variants
        for i in range(len(variant_names)):
            for j in range(i + 1, len(variant_names)):
                variant_a = variant_names[i]
                variant_b = variant_names[j]
                
                result_a = results[variant_a]
                result_b = results[variant_b]
                
                # Test each metric
                for metric in metrics:
                    if metric in result_a.metrics and metric in result_b.metrics:
                        sig_result = self._test_significance(
                            variant_a, variant_b,
                            result_a, result_b,
                            metric
                        )
                        significance_results.append(sig_result)
        
        return significance_results
    
    def _test_significance(
        self,
        variant_a: str,
        variant_b: str,
        result_a: ABTestResult,
        result_b: ABTestResult,
        metric: str
    ) -> StatisticalSignificance:
        """Test statistical significance between two variants."""
        # Get metric values
        value_a = result_a.metrics[metric]
        value_b = result_b.metrics[metric]
        
        # Calculate effect size (Cohen's d)
        pooled_std = np.sqrt((
            result_a.sample_size * 0.1**2 + 
            result_b.sample_size * 0.1**2
        ) / (result_a.sample_size + result_b.sample_size))
        
        effect_size = (value_b - value_a) / pooled_std if pooled_std > 0 else 0
        
        # Perform t-test (simplified - assumes equal variance)
        # In production, would need actual sample data
        t_stat = effect_size * np.sqrt(
            result_a.sample_size * result_b.sample_size / 
            (result_a.sample_size + result_b.sample_size)
        )
        
        df = result_a.sample_size + result_b.sample_size - 2
        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df))
        
        # Determine significance
        is_significant = p_value < (1 - self.confidence_level)
        
        # Generate recommendation
        if is_significant:
            if value_b > value_a:
                recommendation = f"{variant_b} significantly outperforms {variant_a} on {metric}"
            else:
                recommendation = f"{variant_a} significantly outperforms {variant_b} on {metric}"
        else:
            recommendation = f"No significant difference between variants on {metric}"
        
        return StatisticalSignificance(
            metric=metric,
            variant_a=variant_a,
            variant_b=variant_b,
            p_value=p_value,
            effect_size=effect_size,
            is_significant=is_significant,
            confidence_level=self.confidence_level,
            recommendation=recommendation
        )
    
    def _generate_recommendations(
        self,
        results: Dict[str, ABTestResult],
        significance_tests: List[StatisticalSignificance]
    ) -> Dict[str, Any]:
        """Generate recommendations based on test results."""
        recommendations = {
            'overall_winner': None,
            'reasoning': [],
            'metric_specific': {},
            'cost_performance': None,
            'implementation_notes': []
        }
        
        # Find overall winner based on multiple factors
        scores = {}
        
        for variant_name, result in results.items():
            # Calculate composite score
            score = 0
            
            # Quality metrics (weighted)
            if 'f1_score' in result.metrics:
                score += result.metrics['f1_score'] * 3
            if 'precision' in result.metrics:
                score += result.metrics['precision'] * 2
            if 'recall' in result.metrics:
                score += result.metrics['recall'] * 2
            
            # Validation score
            score += result.validation_score * 2
            
            # Penalize for errors
            error_penalty = len(result.errors) * 0.1
            score -= error_penalty
            
            # Consider cost (inverse relationship)
            if result.cost_per_sample > 0:
                cost_factor = 1 / float(result.cost_per_sample)
                score += cost_factor * 0.5
            
            scores[variant_name] = score
        
        # Determine winner
        if scores:
            overall_winner = max(scores.items(), key=lambda x: x[1])[0]
            recommendations['overall_winner'] = overall_winner
            recommendations['reasoning'].append(
                f"{overall_winner} has the best composite score considering quality, cost, and reliability"
            )
        
        # Analyze significant differences
        significant_wins = defaultdict(list)
        for test in significance_tests:
            if test.is_significant:
                if test.effect_size > 0:
                    significant_wins[test.variant_b].append(test.metric)
                else:
                    significant_wins[test.variant_a].append(test.metric)
        
        # Metric-specific recommendations
        for metric in ['f1_score', 'precision', 'recall']:
            metric_values = {
                name: result.metrics.get(metric, 0)
                for name, result in results.items()
            }
            if metric_values:
                best_for_metric = max(metric_values.items(), key=lambda x: x[1])[0]
                recommendations['metric_specific'][metric] = best_for_metric
        
        # Cost-performance analysis
        cost_performance = []
        for name, result in results.items():
            if result.cost_per_sample > 0 and 'f1_score' in result.metrics:
                value_per_dollar = result.metrics['f1_score'] / float(result.cost_per_sample)
                cost_performance.append((name, value_per_dollar))
        
        if cost_performance:
            best_value = max(cost_performance, key=lambda x: x[1])
            recommendations['cost_performance'] = best_value[0]
            recommendations['reasoning'].append(
                f"{best_value[0]} provides best quality per dollar spent"
            )
        
        # Implementation notes
        if overall_winner:
            winner_result = results[overall_winner]
            
            if winner_result.avg_latency_ms > 1000:
                recommendations['implementation_notes'].append(
                    "Consider caching or async processing due to high latency"
                )
            
            if winner_result.validation_score < 0.8:
                recommendations['implementation_notes'].append(
                    "Additional validation or post-processing may be needed"
                )
            
            if len(winner_result.errors) > 0:
                recommendations['implementation_notes'].append(
                    f"Address error cases: {len(winner_result.errors)} errors encountered"
                )
        
        return recommendations
    
    def _find_best_variants(
        self,
        results: Dict[str, ABTestResult]
    ) -> Dict[str, str]:
        """Find best variant for each metric."""
        best_by_metric = {}
        
        metrics = ['f1_score', 'precision', 'recall', 'validation_score']
        
        for metric in metrics:
            metric_values = {}
            
            for name, result in results.items():
                if metric == 'validation_score':
                    metric_values[name] = result.validation_score
                elif metric in result.metrics:
                    metric_values[name] = result.metrics[metric]
            
            if metric_values:
                best = max(metric_values.items(), key=lambda x: x[1])
                best_by_metric[metric] = best[0]
        
        # Add cost efficiency
        cost_values = {
            name: 1 / float(result.cost_per_sample) if result.cost_per_sample > 0 else 0
            for name, result in results.items()
        }
        if cost_values:
            best_cost = max(cost_values.items(), key=lambda x: x[1])
            best_by_metric['cost_efficiency'] = best_cost[0]
        
        # Add speed
        speed_values = {
            name: 1 / result.avg_latency_ms if result.avg_latency_ms > 0 else 0
            for name, result in results.items()
        }
        if speed_values:
            fastest = max(speed_values.items(), key=lambda x: x[1])
            best_by_metric['speed'] = fastest[0]
        
        return best_by_metric
    
    def generate_ab_test_report(
        self,
        test_results: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> str:
        """Generate comprehensive A/B test report."""
        report = []
        
        # Header
        report.append("# A/B Test Report")
        report.append(f"Date: {test_results['test_date']}")
        report.append(f"Sample Size: {test_results['sample_size']}")
        report.append(f"Variants Tested: {test_results['variants_tested']}")
        report.append("")
        
        # Summary
        report.append("## Summary")
        rec = test_results['recommendations']
        if rec['overall_winner']:
            report.append(f"**Recommended Variant: {rec['overall_winner']}**")
            for reason in rec['reasoning']:
                report.append(f"- {reason}")
        report.append("")
        
        # Variant Results
        report.append("## Variant Performance")
        for variant_name, result in test_results['variant_results'].items():
            report.append(f"\n### {variant_name}")
            report.append(f"- Sample Size: {result.sample_size}")
            report.append(f"- Avg Cost: ${result.cost_per_sample:.4f}")
            report.append(f"- Avg Latency: {result.avg_latency_ms:.1f}ms")
            report.append(f"- Validation Score: {result.validation_score:.3f}")
            
            if result.metrics:
                report.append("\nMetrics:")
                for metric, value in result.metrics.items():
                    ci = result.confidence_intervals.get(metric, (0, 0))
                    report.append(f"- {metric}: {value:.3f} (CI: {ci[0]:.3f}-{ci[1]:.3f})")
            
            if result.errors:
                report.append(f"\nErrors: {len(result.errors)}")
        
        # Statistical Significance
        report.append("\n## Statistical Analysis")
        significant_results = [s for s in test_results['significance_tests'] if s.is_significant]
        
        if significant_results:
            report.append("\nSignificant Differences:")
            for sig in significant_results:
                report.append(f"- {sig.recommendation} (p={sig.p_value:.4f}, effect size={sig.effect_size:.3f})")
        else:
            report.append("No statistically significant differences found.")
        
        # Best by Metric
        report.append("\n## Best Variant by Metric")
        for metric, variant in test_results['best_variant_by_metric'].items():
            report.append(f"- {metric}: {variant}")
        
        # Implementation Notes
        if rec['implementation_notes']:
            report.append("\n## Implementation Considerations")
            for note in rec['implementation_notes']:
                report.append(f"- {note}")
        
        report_text = "\n".join(report)
        
        # Save if path provided
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report_text)
        
        return report_text