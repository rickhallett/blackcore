"""
LLM Entity Analyzer

AI-powered entity resolution using Large Language Models for sophisticated
disambiguation of complex intelligence data with context-aware analysis.
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import os

# Try to import LLM libraries
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logging.warning("Anthropic library not available")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI library not available")

logger = logging.getLogger(__name__)


@dataclass
class LLMAnalysisResult:
    """Result of LLM entity analysis."""
    confidence_score: float
    recommended_action: str  # 'merge', 'separate', 'needs_human_review'
    reasoning: str
    key_evidence: List[str]
    risk_assessment: str  # 'low', 'medium', 'high'
    processing_time: float
    model_used: str
    raw_response: str


class LLMEntityAnalyzer:
    """
    AI-powered entity analyzer using multiple LLM providers.
    
    Provides sophisticated entity resolution with context-aware analysis,
    confidence scoring, and detailed explanations for intelligence data.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the LLM analyzer."""
        self.config = config or self._load_default_config()
        
        # Initialize LLM clients
        self.clients = {}
        self._initialize_clients()
        
        # Statistics
        self.stats = {
            "total_analyses": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "model_usage": {},
            "average_processing_time": 0.0,
            "confidence_distribution": {}
        }
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 60 / self.config.get("max_requests_per_minute", 10)
        
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration."""
        return {
            "primary_model": "claude-3-5-sonnet-20241022",
            "fallback_model": "gpt-4",
            "max_requests_per_minute": 10,
            "enable_cross_validation": False,
            "context_window_size": 4000,
            "temperature": 0.1,
            "max_tokens": 1000
        }
        
    def _initialize_clients(self):
        """Initialize LLM API clients."""
        # Anthropic Claude
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if ANTHROPIC_AVAILABLE and anthropic_key:
            try:
                self.clients['anthropic'] = anthropic.Anthropic(api_key=anthropic_key)
                logger.info("✅ Anthropic Claude client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic client: {e}")
                
        # OpenAI GPT
        openai_key = os.getenv('OPENAI_API_KEY')
        if OPENAI_AVAILABLE and openai_key:
            try:
                self.clients['openai'] = openai.OpenAI(api_key=openai_key)
                logger.info("✅ OpenAI GPT client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
                
        if not self.clients:
            logger.warning("⚠️  No LLM clients available - AI analysis will be disabled")
            
    def analyze_entity_pair(self, entity_a: Dict[str, Any], entity_b: Dict[str, Any], 
                          entity_type: str) -> Optional[LLMAnalysisResult]:
        """
        Analyze a pair of entities using AI for sophisticated disambiguation.
        
        Args:
            entity_a: First entity to analyze
            entity_b: Second entity to analyze
            entity_type: Type of entities being compared
            
        Returns:
            LLMAnalysisResult with AI analysis or None if unavailable
        """
        if not self.clients:
            logger.debug("No LLM clients available for analysis")
            return None
            
        start_time = time.time()
        
        # Rate limiting
        self._enforce_rate_limit()
        
        try:
            # Generate appropriate prompt for entity type
            prompt = self._generate_prompt(entity_a, entity_b, entity_type)
            
            # Analyze with primary model
            result = self._analyze_with_model(prompt, self.config["primary_model"])
            
            # Cross-validation with secondary model if enabled
            if self.config.get("enable_cross_validation", False) and len(self.clients) > 1:
                secondary_result = self._analyze_with_model(prompt, self.config["fallback_model"])
                result = self._combine_results(result, secondary_result)
                
            # Update statistics
            self.stats["total_analyses"] += 1
            self.stats["successful_analyses"] += 1
            
            processing_time = time.time() - start_time
            self.stats["average_processing_time"] = (
                (self.stats["average_processing_time"] * (self.stats["successful_analyses"] - 1) + processing_time) 
                / self.stats["successful_analyses"]
            )
            
            # Track confidence distribution
            confidence_bucket = self._get_confidence_bucket(result.confidence_score)
            self.stats["confidence_distribution"][confidence_bucket] = (
                self.stats["confidence_distribution"].get(confidence_bucket, 0) + 1
            )
            
            logger.debug(f"LLM analysis completed in {processing_time:.2f}s with {result.confidence_score:.1f}% confidence")
            
            return result
            
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            self.stats["total_analyses"] += 1
            self.stats["failed_analyses"] += 1
            return None
            
    def _enforce_rate_limit(self):
        """Enforce rate limiting between API requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()
        
    def _generate_prompt(self, entity_a: Dict[str, Any], entity_b: Dict[str, Any], 
                        entity_type: str) -> str:
        """Generate appropriate prompt for entity type."""
        
        # Get entity-specific prompt template
        if entity_type == "People & Contacts":
            return self._generate_person_prompt(entity_a, entity_b)
        elif entity_type == "Organizations & Bodies":
            return self._generate_organization_prompt(entity_a, entity_b)
        elif entity_type == "Key Places & Events":
            return self._generate_event_prompt(entity_a, entity_b)
        else:
            return self._generate_generic_prompt(entity_a, entity_b, entity_type)
            
    def _generate_person_prompt(self, person_a: Dict[str, Any], person_b: Dict[str, Any]) -> str:
        """Generate prompt for person entity analysis."""
        return f"""You are an intelligence analyst specializing in entity resolution. Analyze these two person records and determine if they represent the same individual.

Record A: {json.dumps(person_a, indent=2)}

Record B: {json.dumps(person_b, indent=2)}

Analysis Guidelines:
- This is sensitive intelligence data requiring high accuracy
- Consider aliases, nicknames, and operational names
- Analyze organizational connections and relationship patterns
- Look for temporal consistency in roles and activities
- Consider the possibility of deliberate misdirection or cover identities
- Weight exact matches (email, phone) very heavily
- Consider name variations (Tony/Anthony, Pete/Peter, etc.)

Provide analysis in the following JSON format:
{{
    "confidence_score": <0-100>,
    "recommended_action": "<merge|separate|needs_human_review>",
    "reasoning": "<detailed explanation of your assessment>",
    "key_evidence": ["<evidence point 1>", "<evidence point 2>", "..."],
    "risk_assessment": "<low|medium|high>",
    "potential_concerns": "<any concerns about merging these records>"
}}

Risk Assessment Guidelines:
- High risk: Conflicting information, different time periods, security concerns
- Medium risk: Some uncertainty, missing key data points
- Low risk: Strong evidence, minimal conflicts"""
        
    def _generate_organization_prompt(self, org_a: Dict[str, Any], org_b: Dict[str, Any]) -> str:
        """Generate prompt for organization entity analysis."""
        return f"""You are an intelligence analyst specializing in organizational entity resolution. Analyze these two organization records and determine if they represent the same entity.

Record A: {json.dumps(org_a, indent=2)}

Record B: {json.dumps(org_b, indent=2)}

Analysis Guidelines:
- Consider name variations, abbreviations, and legal entity changes
- Analyze address and contact information overlap
- Consider key personnel connections and organizational relationships
- Look for temporal consistency and organizational evolution
- Consider parent/subsidiary relationships and mergers
- Weight website and email domain matches heavily
- Consider operational name changes and rebranding

Provide analysis in the following JSON format:
{{
    "confidence_score": <0-100>,
    "recommended_action": "<merge|separate|needs_human_review>",
    "reasoning": "<detailed explanation of your assessment>",
    "key_evidence": ["<evidence point 1>", "<evidence point 2>", "..."],
    "risk_assessment": "<low|medium|high>",
    "organizational_relationship": "<same_entity|parent_subsidiary|affiliated|separate|unknown>"
}}

Consider:
- Exact website/email domain matches = very strong evidence
- Key people overlaps = strong supporting evidence
- Name abbreviations (STC → Swanage Town Council) = strong evidence
- Address similarities = moderate evidence
- Category/type mismatches = potential concern"""
        
    def _generate_event_prompt(self, event_a: Dict[str, Any], event_b: Dict[str, Any]) -> str:
        """Generate prompt for event/place entity analysis."""
        return f"""You are an intelligence analyst specializing in event and location entity resolution. Analyze these two records and determine if they represent the same event or place.

Record A: {json.dumps(event_a, indent=2)}

Record B: {json.dumps(event_b, indent=2)}

Analysis Guidelines:
- Consider temporal proximity for events (same event described differently)
- Analyze location and venue consistency
- Look for participant overlap in people involved
- Consider different perspectives of the same event
- Look for location aliases and informal names
- Consider event naming variations and descriptions

Provide analysis in the following JSON format:
{{
    "confidence_score": <0-100>,
    "recommended_action": "<merge|separate|needs_human_review>",
    "reasoning": "<detailed explanation of your assessment>",
    "key_evidence": ["<evidence point 1>", "<evidence point 2>", "..."],
    "risk_assessment": "<low|medium|high>",
    "temporal_analysis": "<same_time|close_proximity|different_times|no_dates>",
    "spatial_analysis": "<same_location|nearby|different_locations|unclear>"
}}

Special Considerations:
- Events on same date at same location = very strong evidence
- Same participants/people involved = strong evidence
- Similar descriptions of activities = moderate evidence
- Location name variations (Shore Road vs Shore Rd) = consider as same"""
        
    def _generate_generic_prompt(self, entity_a: Dict[str, Any], entity_b: Dict[str, Any], 
                                 entity_type: str) -> str:
        """Generate generic prompt for other entity types."""
        return f"""You are an intelligence analyst specializing in entity resolution. Analyze these two {entity_type} records and determine if they represent the same entity.

Record A: {json.dumps(entity_a, indent=2)}

Record B: {json.dumps(entity_b, indent=2)}

Analysis Guidelines:
- This is sensitive intelligence data requiring high accuracy
- Look for exact matches in key identifying fields
- Consider variations in naming and descriptions
- Analyze any relationship or contextual information
- Consider temporal consistency

Provide analysis in the following JSON format:
{{
    "confidence_score": <0-100>,
    "recommended_action": "<merge|separate|needs_human_review>",
    "reasoning": "<detailed explanation of your assessment>",
    "key_evidence": ["<evidence point 1>", "<evidence point 2>", "..."],
    "risk_assessment": "<low|medium|high>"
}}"""
        
    def _analyze_with_model(self, prompt: str, model_name: str) -> LLMAnalysisResult:
        """Analyze with a specific model."""
        start_time = time.time()
        
        # Determine which client to use
        if model_name.startswith('claude') and 'anthropic' in self.clients:
            result = self._analyze_with_claude(prompt, model_name)
        elif model_name.startswith('gpt') and 'openai' in self.clients:
            result = self._analyze_with_openai(prompt, model_name)
        else:
            # Use any available client
            if 'anthropic' in self.clients:
                result = self._analyze_with_claude(prompt, self.config["primary_model"])
            elif 'openai' in self.clients:
                result = self._analyze_with_openai(prompt, self.config["fallback_model"])
            else:
                raise Exception("No LLM clients available")
                
        result.processing_time = time.time() - start_time
        result.model_used = model_name
        
        # Update model usage stats
        self.stats["model_usage"][model_name] = self.stats["model_usage"].get(model_name, 0) + 1
        
        return result
        
    def _analyze_with_claude(self, prompt: str, model_name: str) -> LLMAnalysisResult:
        """Analyze using Anthropic Claude."""
        try:
            response = self.clients['anthropic'].messages.create(
                model=model_name,
                max_tokens=self.config["max_tokens"],
                temperature=self.config["temperature"],
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            raw_response = response.content[0].text
            return self._parse_llm_response(raw_response, model_name)
            
        except Exception as e:
            logger.error(f"Claude analysis failed: {e}")
            raise
            
    def _analyze_with_openai(self, prompt: str, model_name: str) -> LLMAnalysisResult:
        """Analyze using OpenAI GPT."""
        try:
            response = self.clients['openai'].chat.completions.create(
                model=model_name,
                messages=[{
                    "role": "user", 
                    "content": prompt
                }],
                max_tokens=self.config["max_tokens"],
                temperature=self.config["temperature"]
            )
            
            raw_response = response.choices[0].message.content
            return self._parse_llm_response(raw_response, model_name)
            
        except Exception as e:
            logger.error(f"OpenAI analysis failed: {e}")
            raise
            
    def _parse_llm_response(self, raw_response: str, model_name: str) -> LLMAnalysisResult:
        """Parse LLM response into structured result."""
        try:
            # Try to extract JSON from response
            json_start = raw_response.find('{')
            json_end = raw_response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = raw_response[json_start:json_end]
                analysis = json.loads(json_str)
            else:
                raise ValueError("No valid JSON found in response")
                
            return LLMAnalysisResult(
                confidence_score=float(analysis.get("confidence_score", 0)),
                recommended_action=analysis.get("recommended_action", "needs_human_review"),
                reasoning=analysis.get("reasoning", ""),
                key_evidence=analysis.get("key_evidence", []),
                risk_assessment=analysis.get("risk_assessment", "medium"),
                processing_time=0.0,  # Will be set by caller
                model_used=model_name,
                raw_response=raw_response
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            
            # Fallback: try to extract basic information
            confidence = self._extract_confidence_from_text(raw_response)
            action = self._extract_action_from_text(raw_response)
            
            return LLMAnalysisResult(
                confidence_score=confidence,
                recommended_action=action,
                reasoning=raw_response[:500],  # First 500 chars as reasoning
                key_evidence=[],
                risk_assessment="medium",
                processing_time=0.0,
                model_used=model_name,
                raw_response=raw_response
            )
            
    def _extract_confidence_from_text(self, text: str) -> float:
        """Try to extract confidence score from unstructured text."""
        import re
        
        # Look for percentage patterns
        patterns = [
            r'confidence[:\s]*(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%\s*confidence',
            r'score[:\s]*(\d+(?:\.\d+)?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
                    
        return 50.0  # Default medium confidence
        
    def _extract_action_from_text(self, text: str) -> str:
        """Try to extract recommended action from unstructured text."""
        text_lower = text.lower()
        
        if 'merge' in text_lower and 'not' not in text_lower:
            return 'merge'
        elif 'separate' in text_lower:
            return 'separate'
        elif any(phrase in text_lower for phrase in ['human review', 'manual review', 'uncertain']):
            return 'needs_human_review'
        else:
            return 'needs_human_review'
            
    def _combine_results(self, primary: LLMAnalysisResult, secondary: LLMAnalysisResult) -> LLMAnalysisResult:
        """Combine results from multiple models for cross-validation."""
        # Average confidence scores
        combined_confidence = (primary.confidence_score + secondary.confidence_score) / 2
        
        # Use more conservative action
        if primary.recommended_action != secondary.recommended_action:
            combined_action = 'needs_human_review'
        else:
            combined_action = primary.recommended_action
            
        # Combine evidence
        combined_evidence = list(set(primary.key_evidence + secondary.key_evidence))
        
        # Use higher risk assessment
        risk_levels = {'low': 1, 'medium': 2, 'high': 3}
        primary_risk = risk_levels.get(primary.risk_assessment, 2)
        secondary_risk = risk_levels.get(secondary.risk_assessment, 2)
        combined_risk_level = max(primary_risk, secondary_risk)
        combined_risk = {1: 'low', 2: 'medium', 3: 'high'}[combined_risk_level]
        
        return LLMAnalysisResult(
            confidence_score=combined_confidence,
            recommended_action=combined_action,
            reasoning=f"Primary: {primary.reasoning}\n\nSecondary: {secondary.reasoning}",
            key_evidence=combined_evidence,
            risk_assessment=combined_risk,
            processing_time=primary.processing_time + secondary.processing_time,
            model_used=f"{primary.model_used} + {secondary.model_used}",
            raw_response=f"Primary:\n{primary.raw_response}\n\nSecondary:\n{secondary.raw_response}"
        )
        
    def _get_confidence_bucket(self, confidence: float) -> str:
        """Get confidence bucket for statistics."""
        if confidence >= 90:
            return "high (90%+)"
        elif confidence >= 70:
            return "medium (70-90%)"
        elif confidence >= 50:
            return "low (50-70%)"
        else:
            return "very_low (<50%)"
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        success_rate = (self.stats["successful_analyses"] / max(self.stats["total_analyses"], 1)) * 100
        
        return {
            "total_analyses": self.stats["total_analyses"],
            "successful_analyses": self.stats["successful_analyses"],
            "failed_analyses": self.stats["failed_analyses"],
            "success_rate": success_rate,
            "average_processing_time": self.stats["average_processing_time"],
            "model_usage": self.stats["model_usage"],
            "confidence_distribution": self.stats["confidence_distribution"],
            "available_models": list(self.clients.keys()),
            "configuration": self.config
        }