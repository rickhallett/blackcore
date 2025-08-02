"""
Cost-Aware Progressive Testing Strategy for LLM Integration

Implements intelligent testing that optimizes cost/quality trade-offs
with progressive model selection and early stopping.
"""

import json
import time
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

from .ai_extractor import AIExtractor
from .llm_evaluation import LLMEvaluator, GroundTruthExample, EvaluationMetrics
from .models import ExtractedEntities


class ModelTier(Enum):
    """Model tiers ordered by cost."""
    ULTRA_CHEAP = "ultra_cheap"     # e.g., Claude Haiku
    CHEAP = "cheap"                 # e.g., GPT-3.5-turbo
    MODERATE = "moderate"           # e.g., Claude Sonnet, GPT-4
    EXPENSIVE = "expensive"         # e.g., Claude Opus, GPT-4-turbo
    PREMIUM = "premium"             # e.g., GPT-4 with max tokens


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    name: str
    provider: str
    api_key: str
    tier: ModelTier
    cost_per_1k_input: Decimal
    cost_per_1k_output: Decimal
    avg_quality_score: float = 0.0  # Historical quality score
    avg_latency_ms: float = 0.0     # Historical latency
    

@dataclass
class TestCase:
    """Individual test case with complexity assessment."""
    id: str
    ground_truth: GroundTruthExample
    complexity: str  # simple, medium, complex
    priority: int = 1  # Higher priority tests run first
    estimated_tokens: int = 0
    

@dataclass
class TestResult:
    """Result from a single test execution."""
    test_id: str
    model_name: str
    metrics: EvaluationMetrics
    cost: Decimal
    latency_ms: float
    success: bool
    error: Optional[str] = None


class CostAwareTestingStrategy:
    """Implements cost-aware progressive testing for LLM operations."""
    
    # Default model configurations (example costs)
    DEFAULT_MODELS = {
        "claude-3-5-haiku-20241022": ModelConfig(
            name="claude-3-5-haiku-20241022",
            provider="claude",
            api_key="",  # Set from env
            tier=ModelTier.ULTRA_CHEAP,
            cost_per_1k_input=Decimal("0.001"),
            cost_per_1k_output=Decimal("0.005"),
            avg_quality_score=0.85
        ),
        "gpt-3.5-turbo": ModelConfig(
            name="gpt-3.5-turbo",
            provider="openai",
            api_key="",  # Set from env
            tier=ModelTier.CHEAP,
            cost_per_1k_input=Decimal("0.0005"),
            cost_per_1k_output=Decimal("0.0015"),
            avg_quality_score=0.80
        ),
        "claude-3-5-sonnet-20241022": ModelConfig(
            name="claude-3-5-sonnet-20241022",
            provider="claude",
            api_key="",  # Set from env
            tier=ModelTier.MODERATE,
            cost_per_1k_input=Decimal("0.003"),
            cost_per_1k_output=Decimal("0.015"),
            avg_quality_score=0.92
        ),
        "gpt-4-0125-preview": ModelConfig(
            name="gpt-4-0125-preview",
            provider="openai",
            api_key="",  # Set from env
            tier=ModelTier.EXPENSIVE,
            cost_per_1k_input=Decimal("0.01"),
            cost_per_1k_output=Decimal("0.03"),
            avg_quality_score=0.95
        )
    }
    
    def __init__(
        self,
        models: Optional[Dict[str, ModelConfig]] = None,
        budget_limit: Decimal = Decimal("10.00"),
        quality_threshold: float = 0.85,
        max_parallel: int = 3
    ):
        """Initialize cost-aware testing strategy.
        
        Args:
            models: Model configurations (uses defaults if None)
            budget_limit: Maximum budget for test run
            quality_threshold: Minimum acceptable quality score
            max_parallel: Maximum parallel test executions
        """
        self.models = models or self.DEFAULT_MODELS
        self.budget_limit = budget_limit
        self.quality_threshold = quality_threshold
        self.max_parallel = max_parallel
        self.spent_budget = Decimal("0.00")
        self.test_history: List[TestResult] = []
        self.evaluator = LLMEvaluator()
        
    def run_progressive_tests(
        self,
        test_cases: List[TestCase],
        early_stop_on_quality: bool = True,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """Run tests progressively from cheap to expensive models.
        
        Args:
            test_cases: List of test cases to run
            early_stop_on_quality: Stop testing if quality threshold met
            verbose: Print progress
            
        Returns:
            Test results and recommendations
        """
        results_by_tier = {}
        recommendations = {}
        
        # Sort test cases by priority and complexity
        sorted_tests = sorted(
            test_cases,
            key=lambda x: (-x.priority, x.complexity)
        )
        
        # Group models by tier
        models_by_tier = self._group_models_by_tier()
        
        # Progressive testing through tiers
        for tier in ModelTier:
            if tier not in models_by_tier:
                continue
                
            if verbose:
                print(f"\nTesting {tier.value} tier models...")
            
            tier_results = self._test_tier(
                models_by_tier[tier],
                sorted_tests,
                verbose
            )
            
            results_by_tier[tier.value] = tier_results
            
            # Check if we can stop early
            if early_stop_on_quality:
                avg_quality = self._calculate_tier_quality(tier_results)
                if avg_quality >= self.quality_threshold:
                    if verbose:
                        print(f"Quality threshold met at {tier.value} tier!")
                    break
            
            # Check budget
            if self.spent_budget >= self.budget_limit:
                if verbose:
                    print(f"Budget limit reached: ${self.spent_budget}")
                break
        
        # Generate recommendations
        recommendations = self._generate_recommendations(results_by_tier)
        
        return {
            'results_by_tier': results_by_tier,
            'recommendations': recommendations,
            'total_cost': float(self.spent_budget),
            'budget_remaining': float(self.budget_limit - self.spent_budget),
            'test_summary': self._create_test_summary(results_by_tier)
        }
    
    def estimate_test_cost(
        self,
        test_cases: List[TestCase],
        model_name: Optional[str] = None
    ) -> Dict[str, Decimal]:
        """Estimate cost before running tests.
        
        Args:
            test_cases: Test cases to estimate
            model_name: Specific model or None for all
            
        Returns:
            Cost estimates by model
        """
        estimates = {}
        
        models_to_estimate = (
            [self.models[model_name]] if model_name 
            else self.models.values()
        )
        
        for model in models_to_estimate:
            total_cost = Decimal("0.00")
            
            for test in test_cases:
                # Estimate tokens based on complexity
                input_tokens = self._estimate_input_tokens(test)
                output_tokens = self._estimate_output_tokens(test)
                
                cost = self._calculate_cost(
                    model,
                    input_tokens,
                    output_tokens
                )
                total_cost += cost
            
            estimates[model.name] = total_cost
        
        return estimates
    
    def run_cost_quality_analysis(
        self,
        test_cases: List[TestCase],
        sample_size: int = 10
    ) -> Dict[str, Any]:
        """Analyze cost vs quality trade-offs.
        
        Args:
            test_cases: Full test suite
            sample_size: Number of tests to sample
            
        Returns:
            Cost/quality analysis
        """
        # Sample test cases
        import random
        sampled_tests = random.sample(
            test_cases, 
            min(sample_size, len(test_cases))
        )
        
        analysis_results = {}
        
        for model_name, model_config in self.models.items():
            if self.spent_budget >= self.budget_limit:
                break
                
            # Create extractor
            extractor = AIExtractor(
                provider=model_config.provider,
                api_key=model_config.api_key,
                model=model_config.name
            )
            
            # Run sample tests
            model_results = []
            model_cost = Decimal("0.00")
            
            for test in sampled_tests:
                result = self._run_single_test(
                    extractor,
                    model_config,
                    test
                )
                
                if result.success:
                    model_results.append(result)
                    model_cost += result.cost
            
            # Calculate average metrics
            if model_results:
                avg_f1 = sum(r.metrics.f1_score for r in model_results) / len(model_results)
                avg_latency = sum(r.latency_ms for r in model_results) / len(model_results)
                
                analysis_results[model_name] = {
                    'avg_f1_score': avg_f1,
                    'avg_latency_ms': avg_latency,
                    'avg_cost_per_test': float(model_cost / len(model_results)),
                    'quality_per_dollar': avg_f1 / float(model_cost) if model_cost > 0 else 0,
                    'tier': model_config.tier.value
                }
        
        # Add recommendations
        best_quality = max(analysis_results.items(), key=lambda x: x[1]['avg_f1_score'])
        best_value = max(analysis_results.items(), key=lambda x: x[1]['quality_per_dollar'])
        fastest = min(analysis_results.items(), key=lambda x: x[1]['avg_latency_ms'])
        
        return {
            'analysis': analysis_results,
            'recommendations': {
                'best_quality': best_quality[0],
                'best_value': best_value[0],
                'fastest': fastest[0]
            }
        }
    
    def _group_models_by_tier(self) -> Dict[ModelTier, List[ModelConfig]]:
        """Group models by their cost tier."""
        grouped = {}
        for model in self.models.values():
            if model.tier not in grouped:
                grouped[model.tier] = []
            grouped[model.tier].append(model)
        return grouped
    
    def _test_tier(
        self,
        models: List[ModelConfig],
        test_cases: List[TestCase],
        verbose: bool
    ) -> List[TestResult]:
        """Test all models in a tier."""
        tier_results = []
        
        for model in models:
            if self.spent_budget >= self.budget_limit:
                break
                
            # Create extractor for model
            extractor = AIExtractor(
                provider=model.provider,
                api_key=model.api_key,
                model=model.name
            )
            
            # Run tests
            model_results = self._run_model_tests(
                extractor,
                model,
                test_cases,
                verbose
            )
            
            tier_results.extend(model_results)
        
        return tier_results
    
    def _run_model_tests(
        self,
        extractor: AIExtractor,
        model: ModelConfig,
        test_cases: List[TestCase],
        verbose: bool
    ) -> List[TestResult]:
        """Run tests for a specific model."""
        results = []
        
        # Use thread pool for parallel execution
        with ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
            # Submit test tasks
            future_to_test = {
                executor.submit(
                    self._run_single_test,
                    extractor,
                    model,
                    test
                ): test
                for test in test_cases
                if self.spent_budget < self.budget_limit
            }
            
            # Process completed tests
            for future in as_completed(future_to_test):
                test = future_to_test[future]
                
                try:
                    result = future.result()
                    results.append(result)
                    self.test_history.append(result)
                    
                    if verbose and result.success:
                        print(f"  ✓ {test.id}: F1={result.metrics.f1_score:.2f}, Cost=${result.cost}")
                    
                except Exception as e:
                    if verbose:
                        print(f"  ✗ {test.id}: {str(e)}")
                
                # Check budget after each test
                if self.spent_budget >= self.budget_limit:
                    break
        
        return results
    
    def _run_single_test(
        self,
        extractor: AIExtractor,
        model: ModelConfig,
        test: TestCase
    ) -> TestResult:
        """Run a single test case."""
        try:
            # Track timing
            start_time = time.time()
            
            # Extract entities
            predicted = extractor.extract_entities(test.ground_truth.transcript)
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Evaluate results
            metrics = self.evaluator.evaluate_extraction(
                predicted,
                test.ground_truth,
                extraction_time_ms=latency_ms
            )
            
            # Calculate cost
            input_tokens = self._estimate_input_tokens(test)
            output_tokens = len(json.dumps(predicted.dict())) // 4  # Rough estimate
            cost = self._calculate_cost(model, input_tokens, output_tokens)
            
            # Update budget
            self.spent_budget += cost
            
            return TestResult(
                test_id=test.id,
                model_name=model.name,
                metrics=metrics,
                cost=cost,
                latency_ms=latency_ms,
                success=True
            )
            
        except Exception as e:
            return TestResult(
                test_id=test.id,
                model_name=model.name,
                metrics=None,
                cost=Decimal("0.00"),
                latency_ms=0,
                success=False,
                error=str(e)
            )
    
    def _calculate_cost(
        self,
        model: ModelConfig,
        input_tokens: int,
        output_tokens: int
    ) -> Decimal:
        """Calculate cost for tokens."""
        input_cost = (Decimal(input_tokens) / 1000) * model.cost_per_1k_input
        output_cost = (Decimal(output_tokens) / 1000) * model.cost_per_1k_output
        return input_cost + output_cost
    
    def _estimate_input_tokens(self, test: TestCase) -> int:
        """Estimate input tokens based on test complexity."""
        base_tokens = len(test.ground_truth.transcript) // 4
        
        complexity_multiplier = {
            'simple': 1.2,
            'medium': 1.5,
            'complex': 2.0
        }.get(test.complexity, 1.5)
        
        return int(base_tokens * complexity_multiplier)
    
    def _estimate_output_tokens(self, test: TestCase) -> int:
        """Estimate output tokens based on expected entities."""
        # Rough estimate based on entity count
        expected_entities = len(test.ground_truth.entities)
        tokens_per_entity = 50  # Rough estimate
        return expected_entities * tokens_per_entity
    
    def _calculate_tier_quality(self, results: List[TestResult]) -> float:
        """Calculate average quality for a tier."""
        successful_results = [r for r in results if r.success]
        if not successful_results:
            return 0.0
        
        return sum(r.metrics.f1_score for r in successful_results) / len(successful_results)
    
    def _generate_recommendations(
        self,
        results_by_tier: Dict[str, List[TestResult]]
    ) -> Dict[str, Any]:
        """Generate recommendations based on test results."""
        recommendations = {
            'suggested_model': None,
            'reasoning': [],
            'alternative_strategies': []
        }
        
        # Find best performing tier within budget
        tier_summaries = []
        
        for tier, results in results_by_tier.items():
            successful = [r for r in results if r.success]
            if successful:
                avg_f1 = sum(r.metrics.f1_score for r in successful) / len(successful)
                avg_cost = sum(r.cost for r in successful) / len(successful)
                
                tier_summaries.append({
                    'tier': tier,
                    'avg_f1': avg_f1,
                    'avg_cost': float(avg_cost),
                    'meets_quality': avg_f1 >= self.quality_threshold
                })
        
        # Find cheapest tier that meets quality
        qualifying_tiers = [t for t in tier_summaries if t['meets_quality']]
        if qualifying_tiers:
            best_tier = min(qualifying_tiers, key=lambda x: x['avg_cost'])
            recommendations['suggested_model'] = best_tier['tier']
            recommendations['reasoning'].append(
                f"Tier {best_tier['tier']} meets quality threshold at lowest cost"
            )
        else:
            # Suggest highest quality within budget
            if tier_summaries:
                best_tier = max(tier_summaries, key=lambda x: x['avg_f1'])
                recommendations['suggested_model'] = best_tier['tier']
                recommendations['reasoning'].append(
                    f"No tier meets quality threshold; {best_tier['tier']} has best quality"
                )
        
        # Alternative strategies
        if self.spent_budget >= self.budget_limit * Decimal("0.8"):
            recommendations['alternative_strategies'].append(
                "Consider increasing budget or reducing test coverage"
            )
        
        if not qualifying_tiers:
            recommendations['alternative_strategies'].append(
                "Consider lowering quality threshold or using ensemble approach"
            )
        
        return recommendations
    
    def _create_test_summary(
        self,
        results_by_tier: Dict[str, List[TestResult]]
    ) -> Dict[str, Any]:
        """Create summary of test results."""
        summary = {
            'total_tests_run': sum(len(r) for r in results_by_tier.values()),
            'successful_tests': sum(
                len([t for t in r if t.success]) 
                for r in results_by_tier.values()
            ),
            'total_cost': float(self.spent_budget),
            'tiers_tested': list(results_by_tier.keys())
        }
        
        # Add quality summary
        quality_by_tier = {}
        for tier, results in results_by_tier.items():
            successful = [r for r in results if r.success]
            if successful:
                quality_by_tier[tier] = {
                    'avg_f1': sum(r.metrics.f1_score for r in successful) / len(successful),
                    'avg_precision': sum(r.metrics.precision for r in successful) / len(successful),
                    'avg_recall': sum(r.metrics.recall for r in successful) / len(successful)
                }
        
        summary['quality_by_tier'] = quality_by_tier
        
        return summary


class TestCaseBuilder:
    """Helper to build test cases with complexity assessment."""
    
    @staticmethod
    def assess_complexity(ground_truth: GroundTruthExample) -> str:
        """Assess test case complexity."""
        entity_count = len(ground_truth.entities)
        relationship_count = len(ground_truth.relationships)
        transcript_length = len(ground_truth.transcript)
        
        # Simple heuristic
        if entity_count <= 3 and relationship_count <= 1 and transcript_length < 500:
            return 'simple'
        elif entity_count <= 8 and relationship_count <= 5 and transcript_length < 2000:
            return 'medium'
        else:
            return 'complex'
    
    @staticmethod
    def build_test_cases(
        ground_truth_examples: List[GroundTruthExample],
        prioritize_by: str = 'complexity'
    ) -> List[TestCase]:
        """Build test cases from ground truth examples."""
        test_cases = []
        
        for i, example in enumerate(ground_truth_examples):
            complexity = TestCaseBuilder.assess_complexity(example)
            
            # Set priority based on strategy
            if prioritize_by == 'complexity':
                priority = {'simple': 1, 'medium': 2, 'complex': 3}.get(complexity, 2)
            else:
                priority = 1  # Default equal priority
            
            test_cases.append(TestCase(
                id=f"test_{i:04d}",
                ground_truth=example,
                complexity=complexity,
                priority=priority,
                estimated_tokens=len(example.transcript) // 4
            ))
        
        return test_cases