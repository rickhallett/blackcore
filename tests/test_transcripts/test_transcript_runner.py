#!/usr/bin/env python3
"""
Test runner for validating entity extraction from mock transcripts.

This script processes test transcripts and compares extracted entities
against expected results to validate the framework's extraction capabilities.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Set
from dataclasses import dataclass
from collections import defaultdict

# Add the blackcore module to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from blackcore.minimal.transcript_processor import TranscriptProcessor
from blackcore.minimal.config import ConfigManager


@dataclass
class ExtractionResult:
    """Results from entity extraction test."""
    transcript_id: str
    total_expected: int
    total_found: int
    matches: Dict[str, List[str]]
    missing: Dict[str, List[str]]
    unexpected: Dict[str, List[str]]
    accuracy: float


class TranscriptTestRunner:
    """Test runner for transcript entity extraction validation."""
    
    def __init__(self, test_dir: Path = None):
        """Initialize test runner."""
        self.test_dir = test_dir or Path(__file__).parent
        self.results: List[ExtractionResult] = []
        
        # Initialize the transcript processor
        config_manager = ConfigManager()
        config = config_manager.load()
        self.processor = TranscriptProcessor(config)
    
    def load_test_transcripts(self) -> List[Dict[str, Any]]:
        """Load all test transcript files."""
        transcripts = []
        
        for file_path in self.test_dir.glob("test_transcript_*.json"):
            with open(file_path, 'r', encoding='utf-8') as f:
                transcript = json.load(f)
                transcripts.append(transcript)
                
        return sorted(transcripts, key=lambda x: x['transcript_id'])
    
    def extract_entities_from_content(self, content: str) -> Dict[str, Set[str]]:
        """Extract entities using the framework."""
        # Create a minimal transcript format for processing
        transcript_data = {
            "content": content,
            "metadata": {}
        }
        
        # Process the transcript
        result = self.processor.process_transcript(transcript_data, dry_run=True)
        
        # Organize extracted entities by type
        extracted = defaultdict(set)
        
        if result and result.entities:
            for entity in result.entities:
                entity_type = entity.entity_type.lower()
                entity_name = entity.name
                extracted[entity_type].add(entity_name)
        
        return dict(extracted)
    
    def normalize_entity_name(self, name: str) -> str:
        """Normalize entity names for comparison."""
        return name.lower().strip()
    
    def compare_entities(self, expected: Dict[str, List], extracted: Dict[str, Set[str]]) -> ExtractionResult:
        """Compare expected vs extracted entities."""
        matches = defaultdict(list)
        missing = defaultdict(list)
        unexpected = defaultdict(list)
        
        # Process expected entities
        for entity_type, entity_list in expected.items():
            if entity_type in ['relationships', 'test_scenarios', 'financial_data']:
                continue  # Skip non-entity sections
                
            extracted_type = extracted.get(entity_type, set())
            
            for entity in entity_list:
                if isinstance(entity, dict):
                    entity_name = entity.get('name', '')
                else:
                    entity_name = str(entity)
                
                normalized_name = self.normalize_entity_name(entity_name)
                
                # Check if entity was found (with normalization)
                found = False
                for extracted_name in extracted_type:
                    if self.normalize_entity_name(extracted_name) == normalized_name:
                        matches[entity_type].append(entity_name)
                        found = True
                        break
                
                if not found:
                    missing[entity_type].append(entity_name)
        
        # Check for unexpected entities
        for entity_type, extracted_set in extracted.items():
            expected_type = expected.get(entity_type, [])
            expected_names = set()
            
            for entity in expected_type:
                if isinstance(entity, dict):
                    expected_names.add(self.normalize_entity_name(entity.get('name', '')))
                else:
                    expected_names.add(self.normalize_entity_name(str(entity)))
            
            for extracted_name in extracted_set:
                if self.normalize_entity_name(extracted_name) not in expected_names:
                    unexpected[entity_type].append(extracted_name)
        
        # Calculate accuracy
        total_expected = sum(len(v) for k, v in expected.items() 
                           if k not in ['relationships', 'test_scenarios', 'financial_data'])
        total_found = sum(len(v) for v in matches.values())
        accuracy = (total_found / total_expected * 100) if total_expected > 0 else 0
        
        return ExtractionResult(
            transcript_id="",
            total_expected=total_expected,
            total_found=total_found,
            matches=dict(matches),
            missing=dict(missing),
            unexpected=dict(unexpected),
            accuracy=accuracy
        )
    
    def run_test(self, transcript: Dict[str, Any]) -> ExtractionResult:
        """Run extraction test on a single transcript."""
        transcript_id = transcript['transcript_id']
        content = transcript['content']
        expected = transcript['expected_entities']
        
        print(f"\nTesting transcript: {transcript_id} - {transcript['title']}")
        
        # Extract entities
        extracted = self.extract_entities_from_content(content)
        
        # Compare results
        result = self.compare_entities(expected, extracted)
        result.transcript_id = transcript_id
        
        return result
    
    def print_result(self, result: ExtractionResult):
        """Print test results for a transcript."""
        print(f"\n{'='*60}")
        print(f"Results for {result.transcript_id}:")
        print(f"{'='*60}")
        print(f"Accuracy: {result.accuracy:.1f}% ({result.total_found}/{result.total_expected})")
        
        if result.matches:
            print("\n✅ Successfully Extracted:")
            for entity_type, entities in result.matches.items():
                print(f"  {entity_type}: {len(entities)} entities")
                for entity in entities[:3]:  # Show first 3
                    print(f"    - {entity}")
                if len(entities) > 3:
                    print(f"    ... and {len(entities) - 3} more")
        
        if result.missing:
            print("\n❌ Missing Entities:")
            for entity_type, entities in result.missing.items():
                print(f"  {entity_type}: {len(entities)} missing")
                for entity in entities:
                    print(f"    - {entity}")
        
        if result.unexpected:
            print("\n⚠️  Unexpected Entities:")
            for entity_type, entities in result.unexpected.items():
                print(f"  {entity_type}: {len(entities)} unexpected")
                for entity in entities[:3]:
                    print(f"    - {entity}")
                if len(entities) > 3:
                    print(f"    ... and {len(entities) - 3} more")
    
    def run_all_tests(self):
        """Run tests on all transcripts."""
        transcripts = self.load_test_transcripts()
        
        if not transcripts:
            print("No test transcripts found!")
            return
        
        print(f"Found {len(transcripts)} test transcripts")
        
        for transcript in transcripts:
            try:
                result = self.run_test(transcript)
                self.results.append(result)
                self.print_result(result)
            except Exception as e:
                print(f"\n❌ Error testing {transcript['transcript_id']}: {str(e)}")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print overall test summary."""
        print(f"\n{'='*60}")
        print("OVERALL TEST SUMMARY")
        print(f"{'='*60}")
        
        total_accuracy = sum(r.accuracy for r in self.results) / len(self.results)
        total_expected = sum(r.total_expected for r in self.results)
        total_found = sum(r.total_found for r in self.results)
        
        print(f"Total Transcripts Tested: {len(self.results)}")
        print(f"Overall Accuracy: {total_accuracy:.1f}%")
        print(f"Total Entities Expected: {total_expected}")
        print(f"Total Entities Found: {total_found}")
        
        # Per-transcript summary
        print("\nPer-Transcript Results:")
        for result in self.results:
            status = "✅" if result.accuracy >= 80 else "⚠️" if result.accuracy >= 60 else "❌"
            print(f"  {status} {result.transcript_id}: {result.accuracy:.1f}% accuracy")
        
        # Entity type summary
        entity_type_stats = defaultdict(lambda: {"expected": 0, "found": 0})
        
        for result in self.results:
            for entity_type, entities in result.matches.items():
                entity_type_stats[entity_type]["found"] += len(entities)
            
            # Count expected from missing + matches
            for entity_type, entities in result.missing.items():
                entity_type_stats[entity_type]["expected"] += len(entities)
            for entity_type, entities in result.matches.items():
                entity_type_stats[entity_type]["expected"] += len(entities)
        
        print("\nEntity Type Performance:")
        for entity_type, stats in sorted(entity_type_stats.items()):
            accuracy = (stats["found"] / stats["expected"] * 100) if stats["expected"] > 0 else 0
            print(f"  {entity_type}: {accuracy:.1f}% ({stats['found']}/{stats['expected']})")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test entity extraction on mock transcripts")
    parser.add_argument("--transcript", help="Test specific transcript ID")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    
    args = parser.parse_args()
    
    runner = TranscriptTestRunner()
    
    if args.transcript:
        # Test specific transcript
        transcripts = runner.load_test_transcripts()
        transcript = next((t for t in transcripts if t['transcript_id'] == args.transcript), None)
        
        if transcript:
            result = runner.run_test(transcript)
            runner.print_result(result)
        else:
            print(f"Transcript {args.transcript} not found!")
    else:
        # Run all tests
        runner.run_all_tests()


if __name__ == "__main__":
    main()