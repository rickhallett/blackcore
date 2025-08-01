#!/usr/bin/env python3
"""Quick test of the Analytics API implementation."""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from blackcore.minimal.query_engine.analytics import (
    AnalyticsEngine, AnalyticsRequest, NetworkAnalysisRequest,
    TimelineRequest, NetworkAlgorithm, TimeGranularity
)
from datetime import datetime, timedelta


async def test_analytics_engine():
    """Test the analytics engine functionality."""
    print("Testing Analytics Engine...")
    
    # Initialize analytics engine
    engine = AnalyticsEngine(
        data_dir="blackcore/models/json",
        enable_caching=True
    )
    
    print(f"Available databases: {engine.get_available_databases()}")
    
    # Test overview analytics
    print("\n=== Testing Overview Analytics ===")
    try:
        request = AnalyticsRequest(
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow(),
            refresh_cache=True
        )
        
        overview = await engine.generate_overview(request)
        print(f"Overview generated in {overview.execution_time_ms:.2f}ms")
        print(f"Total entities: {overview.total_entities}")
        print(f"Recent activity: {overview.recent_activity}")
        print(f"Health status: {overview.health_indicators}")
        
    except Exception as e:
        print(f"Overview analytics error: {e}")
    
    # Test network analysis
    print("\n=== Testing Network Analysis ===")
    try:
        network_request = NetworkAnalysisRequest(
            algorithm=NetworkAlgorithm.CENTRALITY,
            max_depth=2,
            min_connections=1,
            refresh_cache=True
        )
        
        network = await engine.analyze_network(network_request)
        print(f"Network analysis completed in {network.execution_time_ms:.2f}ms")
        print(f"Nodes: {len(network.nodes)}, Edges: {len(network.edges)}")
        print(f"Communities: {len(network.communities)}")
        print(f"Network metrics: {network.metrics}")
        
    except Exception as e:
        print(f"Network analysis error: {e}")
    
    # Test timeline analysis
    print("\n=== Testing Timeline Analysis ===")
    try:
        timeline_request = TimelineRequest(
            start_date=datetime.utcnow() - timedelta(days=7),
            end_date=datetime.utcnow(),
            granularity=TimeGranularity.DAILY,
            metrics=["entity_count", "activity_level"],
            include_forecasting=False
        )
        
        timeline = await engine.generate_timeline(timeline_request)
        print(f"Timeline analysis completed in {timeline.execution_time_ms:.2f}ms")
        print(f"Timeline points: {len(timeline.timeline)}")
        print(f"Trends: {timeline.trends}")
        
    except Exception as e:
        print(f"Timeline analysis error: {e}")
    
    # Test system health
    print("\n=== Testing System Health ===")
    try:
        health = await engine.get_system_health()
        print(f"System health check completed in {health.execution_time_ms:.2f}ms")
        print(f"Overall health: {health.overall_health}")
        print(f"Uptime: {health.uptime_seconds:.0f} seconds")
        
    except Exception as e:
        print(f"System health error: {e}")
    
    # Cleanup
    await engine.cleanup()
    print("\nAnalytics engine test completed!")


def test_data_loading():
    """Test basic data loading functionality."""
    print("\n=== Testing Data Loading ===")
    
    engine = AnalyticsEngine(data_dir="blackcore/models/json")
    
    # Test database listing
    databases = engine.get_available_databases()
    print(f"Found {len(databases)} databases: {databases}")
    
    # Test loading a database
    for db_name in databases[:2]:  # Test first 2 databases
        try:
            data = engine._load_database(db_name)
            print(f"Database '{db_name}': {len(data)} records")
            
            if data:
                # Show sample fields
                sample = data[0]
                fields = list(sample.keys())[:5]  # First 5 fields
                print(f"  Sample fields: {fields}")
                
        except Exception as e:
            print(f"  Error loading {db_name}: {e}")


if __name__ == "__main__":
    print("BlackCore Analytics API Test")
    print("=" * 40)
    
    # Test data loading first
    test_data_loading()
    
    # Test analytics engine
    try:
        asyncio.run(test_analytics_engine())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()