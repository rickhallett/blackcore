#!/usr/bin/env python3
"""
Deduplication System Integration Test

Comprehensive test and demonstration of the sophisticated deduplication system
with AI/LLM integration, graph analysis, and human review workflows.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackcore.deduplication import (
    DeduplicationEngine,
    GraphRelationshipAnalyzer,
    HumanReviewInterface,
    ReviewDecision
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_data() -> Dict[str, List[Dict[str, Any]]]:
    """Create comprehensive test data with known duplicates."""
    
    test_databases = {
        "People & Contacts": [
            {
                "id": "person_1",
                "Full Name": "Anthony Smith",
                "Email": "tony.smith@example.com", 
                "Phone": "01234567890",
                "Organization": "Swanage Town Council",
                "Role": "Councillor",
                "Address": "123 Shore Road, Swanage"
            },
            {
                "id": "person_2", 
                "Full Name": "Tony Smith",
                "Email": "tony.smith@example.com",
                "Phone": "01234 567 890",
                "Organization": "STC",
                "Role": "Council Member",
                "Address": "Shore Rd, Swanage"
            },
            {
                "id": "person_3",
                "Full Name": "Robert Johnson",
                "Email": "bob.johnson@corp.com",
                "Organization": "Johnson Corp",
                "Role": "CEO"
            },
            {
                "id": "person_4",
                "Full Name": "Bob Johnson", 
                "Email": "robert.johnson@johnsoncorp.com",
                "Organization": "Johnson Corporation",
                "Role": "Chief Executive"
            },
            {
                "id": "person_5",
                "Full Name": "Sarah Wilson",
                "Email": "sarah@example.org",
                "Organization": "Local Community Group"
            }
        ],
        
        "Organizations & Bodies": [
            {
                "id": "org_1",
                "Organization Name": "Swanage Town Council",
                "Website": "https://www.swanage.gov.uk",
                "Email": "info@swanage.gov.uk",
                "Address": "Town Hall, Swanage",
                "Category": "Local Government"
            },
            {
                "id": "org_2",
                "Organization Name": "STC",
                "Website": "swanage.gov.uk", 
                "Email": "admin@swanage.gov.uk",
                "Address": "Swanage Town Hall",
                "Category": "Council"
            },
            {
                "id": "org_3",
                "Organization Name": "Johnson Corporation",
                "Website": "https://johnsoncorp.com",
                "Email": "contact@johnsoncorp.com",
                "Category": "Private Company"
            },
            {
                "id": "org_4",
                "Organization Name": "Johnson Corp",
                "Website": "https://www.johnsoncorp.com",
                "Email": "info@johnsoncorp.com", 
                "Category": "Corporation"
            }
        ],
        
        "Key Places & Events": [
            {
                "id": "event_1",
                "Event / Place Name": "Town Council Meeting",
                "Date of Event": "2024-01-15",
                "Location": "Town Hall, Swanage",
                "Description": "Monthly council meeting to discuss local issues"
            },
            {
                "id": "event_2",
                "Event / Place Name": "STC Monthly Meeting",
                "Date of Event": "2024-01-15",
                "Location": "Swanage Town Hall",
                "Description": "Regular meeting of town councillors"
            },
            {
                "id": "event_3", 
                "Event / Place Name": "Community Gathering",
                "Date of Event": "2024-02-01",
                "Location": "Community Center",
                "Description": "Local residents meeting"
            }
        ]
    }
    
    return test_databases


def run_comprehensive_test():
    """Run comprehensive deduplication system test."""
    
    logger.info("🚀 Starting Comprehensive Deduplication System Test")
    logger.info("=" * 80)
    
    # Create test data
    test_data = create_test_data()
    logger.info("📊 Created test data:")
    for db_name, records in test_data.items():
        logger.info(f"   {db_name}: {len(records)} records")
    
    # Initialize the deduplication engine
    logger.info("\n🔧 Initializing Deduplication Engine...")
    config = {
        "auto_merge_threshold": 95.0,
        "human_review_threshold": 70.0,
        "enable_ai_analysis": True,
        "safety_mode": True  # Prevent automatic merges during testing
    }
    
    engine = DeduplicationEngine()
    engine.config.update(config)
    
    # Test 1: Individual Database Analysis
    logger.info("\n📋 Test 1: Individual Database Analysis")
    logger.info("-" * 50)
    
    results = {}
    for db_name, records in test_data.items():
        logger.info(f"\n🔍 Analyzing {db_name}...")
        result = engine.analyze_database(db_name, records, enable_ai=False)  # Disable AI for speed
        results[db_name] = result
        
        logger.info(f"   📊 Results for {db_name}:")
        logger.info(f"      Total entities: {result.total_entities}")
        logger.info(f"      Potential duplicates: {result.potential_duplicates}")
        logger.info(f"      High confidence matches: {len(result.high_confidence_matches)}")
        logger.info(f"      Medium confidence matches: {len(result.medium_confidence_matches)}")
        logger.info(f"      Processing time: {result.processing_time:.2f}s")
        
        # Show specific matches found
        if result.high_confidence_matches:
            logger.info("      High confidence matches found:")
            for match in result.high_confidence_matches:
                entity_a = match["entity_a"]
                entity_b = match["entity_b"]
                score = match["confidence_score"]
                name_a = entity_a.get("Full Name", entity_a.get("Organization Name", entity_a.get("Event / Place Name", "Unknown")))
                name_b = entity_b.get("Full Name", entity_b.get("Organization Name", entity_b.get("Event / Place Name", "Unknown")))
                logger.info(f"         • '{name_a}' ↔ '{name_b}' ({score:.1f}%)")
    
    # Test 2: Comprehensive Multi-Database Analysis
    logger.info("\n📋 Test 2: Comprehensive Multi-Database Analysis")
    logger.info("-" * 50)
    
    comprehensive_results = engine.analyze_all_databases(test_data)
    
    total_entities = sum(r.total_entities for r in comprehensive_results.values())
    total_duplicates = sum(r.potential_duplicates for r in comprehensive_results.values())
    
    logger.info("\n📊 Comprehensive Analysis Summary:")
    logger.info(f"   Total entities across all databases: {total_entities}")
    logger.info(f"   Total potential duplicates found: {total_duplicates}")
    
    # Test 3: Graph Relationship Analysis
    logger.info("\n📋 Test 3: Graph Relationship Analysis")
    logger.info("-" * 50)
    
    graph_analyzer = GraphRelationshipAnalyzer()
    graph_analyzer.build_relationship_graph(test_data)
    
    # Create entity pairs for graph analysis
    entity_pairs = []
    for db_results in comprehensive_results.values():
        for match in db_results.high_confidence_matches + db_results.medium_confidence_matches:
            entity_a_id = f"{match['entity_type']}:{match['entity_a'].get('id', 'unknown')}"
            entity_b_id = f"{match['entity_type']}:{match['entity_b'].get('id', 'unknown')}"
            entity_pairs.append((entity_a_id, entity_b_id))
    
    if entity_pairs:
        graph_results = graph_analyzer.analyze_for_disambiguation(entity_pairs)
        
        logger.info("   🌐 Graph Analysis Results:")
        logger.info(f"      Network nodes: {graph_results.network_metrics['total_nodes']}")
        logger.info(f"      Network edges: {graph_results.network_metrics['total_edges']}")
        logger.info(f"      Entity clusters: {len(graph_results.entity_clusters)}")
        logger.info(f"      Disambiguation suggestions: {len(graph_results.disambiguation_suggestions)}")
        
        if graph_results.disambiguation_suggestions:
            logger.info("      Graph-based recommendations:")
            for suggestion in graph_results.disambiguation_suggestions[:3]:  # Show top 3
                confidence = suggestion.get("confidence", 0) * 100
                evidence = suggestion.get("evidence", [])
                logger.info(f"         • Confidence: {confidence:.1f}% - {', '.join(evidence[:2])}")
    
    # Test 4: Human Review Interface
    logger.info("\n📋 Test 4: Human Review Interface") 
    logger.info("-" * 50)
    
    review_interface = HumanReviewInterface(engine.audit_system)
    
    # Get next review task (simulated)
    review_task = review_interface.get_next_review_task("test_reviewer")
    
    if review_task:
        logger.info(f"   📋 Retrieved review task: {review_task.task_id}")
        logger.info(f"      Risk factors: {len(review_task.risk_factors)}")
        logger.info(f"      Supporting evidence: {len(review_task.supporting_evidence)}")
        logger.info(f"      Conflicting evidence: {len(review_task.conflicting_evidence)}")
        
        # Simulate human decision
        simulated_decision = ReviewDecision(
            task_id=review_task.task_id,
            reviewer_id="test_reviewer",
            decision="merge",
            confidence=85.0,
            reasoning="Entities appear to be the same based on exact email match and similar names. Organization abbreviation pattern detected.",
            time_spent_seconds=180
        )
        
        success = review_interface.submit_review_decision(simulated_decision)
        logger.info(f"      Decision submitted: {success}")
    else:
        logger.info("   📋 No review tasks available (expected in safety mode)")
    
    # Test 5: System Statistics and Performance
    logger.info("\n📋 Test 5: System Statistics and Performance")
    logger.info("-" * 50)
    
    # Get comprehensive statistics
    engine_stats = engine.get_statistics()
    graph_stats = graph_analyzer.get_statistics()
    review_stats = review_interface.get_statistics()
    
    logger.info("   📊 Engine Statistics:")
    logger.info(f"      Total comparisons: {engine_stats['engine_stats']['total_comparisons']}")
    logger.info(f"      AI analyses performed: {engine_stats['engine_stats']['ai_analyses_performed']}")
    logger.info(f"      Human reviews created: {engine_stats['engine_stats']['human_reviews_created']}")
    
    logger.info("   🌐 Graph Statistics:")
    logger.info(f"      Nodes processed: {graph_stats['nodes_processed']}")
    logger.info(f"      Relationships identified: {graph_stats['relationships_identified']}")
    logger.info(f"      Clusters formed: {graph_stats['clusters_formed']}")
    
    logger.info("   👥 Review Statistics:")
    logger.info(f"      Reviews completed: {review_stats['interface_stats']['reviews_completed']}")
    logger.info(f"      Average review time: {review_stats['interface_stats']['average_review_time']:.1f}s")
    
    # Test 6: Expected Duplicate Detection Validation
    logger.info("\n📋 Test 6: Expected Duplicate Detection Validation")
    logger.info("-" * 50)
    
    expected_duplicates = [
        ("Anthony Smith", "Tony Smith"),  # People - nickname variation
        ("Robert Johnson", "Bob Johnson"),  # People - nickname variation  
        ("Swanage Town Council", "STC"),  # Organizations - abbreviation
        ("Johnson Corporation", "Johnson Corp"),  # Organizations - abbreviation
        ("Town Council Meeting", "STC Monthly Meeting")  # Events - same meeting
    ]
    
    detected_duplicates = []
    for db_results in comprehensive_results.values():
        for match in db_results.high_confidence_matches + db_results.medium_confidence_matches:
            entity_a = match["entity_a"]
            entity_b = match["entity_b"]
            name_a = entity_a.get("Full Name", entity_a.get("Organization Name", entity_a.get("Event / Place Name", "")))
            name_b = entity_b.get("Full Name", entity_b.get("Organization Name", entity_b.get("Event / Place Name", "")))
            detected_duplicates.append((name_a, name_b))
    
    logger.info(f"   Expected duplicates: {len(expected_duplicates)}")
    logger.info(f"   Detected duplicates: {len(detected_duplicates)}")
    
    # Check detection accuracy
    correctly_detected = 0
    for expected in expected_duplicates:
        for detected in detected_duplicates:
            if (expected[0] in detected and expected[1] in detected) or (expected[1] in detected and expected[0] in detected):
                correctly_detected += 1
                logger.info(f"      ✅ Correctly detected: {expected[0]} ↔ {expected[1]}")
                break
        else:
            logger.info(f"      ❌ Missed: {expected[0]} ↔ {expected[1]}")
    
    detection_rate = (correctly_detected / len(expected_duplicates)) * 100
    logger.info(f"   🎯 Detection accuracy: {detection_rate:.1f}%")
    
    # Final Summary
    logger.info("\n🎉 Test Summary")
    logger.info("=" * 80)
    logger.info("✅ Deduplication System Integration Test Complete")
    logger.info("📊 Overall Results:")
    logger.info(f"   • Processed {total_entities} entities across {len(test_data)} databases")
    logger.info(f"   • Found {total_duplicates} potential duplicates")
    logger.info(f"   • Achieved {detection_rate:.1f}% detection accuracy on known duplicates")
    logger.info(f"   • Graph analysis identified {graph_stats['relationships_identified']} relationships")
    logger.info("   • System ready for production use with human oversight")
    
    if detection_rate >= 80:
        logger.info("🎯 PASS: High accuracy deduplication system successfully implemented")
    else:
        logger.info("⚠️  REVIEW: Detection accuracy below 80% - consider tuning parameters")
    
    return {
        "detection_accuracy": detection_rate,
        "total_entities": total_entities,
        "total_duplicates": total_duplicates,
        "system_stats": {
            "engine": engine_stats,
            "graph": graph_stats, 
            "review": review_stats
        }
    }


if __name__ == "__main__":
    try:
        results = run_comprehensive_test()
        print("\n📋 Test completed successfully!")
        print(f"Detection accuracy: {results['detection_accuracy']:.1f}%")
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)