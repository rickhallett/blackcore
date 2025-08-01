#!/usr/bin/env python3
"""Monitor the progress of all three query engine development agents."""

import json
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import os

# Colors for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def clear_screen():
    """Clear terminal screen."""
    os.system('clear' if os.name == 'posix' else 'cls')

def load_status() -> Dict:
    """Load current status from coordination file."""
    status_file = Path("blackcore/minimal/query_engine/.coordination/status.json")
    if not status_file.exists():
        return None
    
    try:
        with open(status_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading status: {e}")
        return None

def calculate_progress(agent_data: Dict) -> float:
    """Calculate progress percentage for an agent."""
    # Simple heuristic based on completed modules
    expected_modules = {
        'agent_a': ['DataLoader', 'JSONDataLoader', 'FilterEngine', 'BasicFilters', 'SortingEngine'],
        'agent_b': ['TextSearchEngine', 'BasicSearch', 'RelationshipResolver', 'NLPParser'],
        'agent_c': ['MemoryCache', 'CacheManager', 'QueryOptimizer', 'StreamingExporter']
    }
    
    agent_key = next((k for k in expected_modules.keys() if k in agent_data.get('name', '').lower()), 'agent_a')
    completed = len(agent_data.get('completed_modules', []))
    expected = len(expected_modules.get(agent_key, []))
    
    return (completed / expected * 100) if expected > 0 else 0

def format_time_ago(timestamp_str: str) -> str:
    """Format timestamp as 'X minutes ago'."""
    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.utcnow()
        delta = now - timestamp.replace(tzinfo=None)
        
        if delta.total_seconds() < 60:
            return f"{int(delta.total_seconds())}s ago"
        elif delta.total_seconds() < 3600:
            return f"{int(delta.total_seconds() / 60)}m ago"
        else:
            return f"{int(delta.total_seconds() / 3600)}h ago"
    except:
        return "unknown"

def display_agent_status(agent_key: str, agent_data: Dict, color: str):
    """Display status for a single agent."""
    progress = calculate_progress(agent_data)
    name = agent_data.get('name', agent_key)
    status = agent_data.get('status', 'unknown')
    current_task = agent_data.get('current_task', 'none')
    completed = agent_data.get('completed_modules', [])
    interfaces = agent_data.get('interfaces_ready', [])
    
    # Status emoji
    status_emoji = {
        'working': '🔨',
        'starting': '🚀',
        'blocked': '🚫',
        'completed': '✅',
        'error': '❌'
    }.get(status, '❓')
    
    print(f"{color}{Colors.BOLD}━━━ {name} {status_emoji} ━━━{Colors.RESET}")
    print(f"{color}Status:{Colors.RESET} {status}")
    print(f"{color}Progress:{Colors.RESET} [{'█' * int(progress/10)}{'░' * (10-int(progress/10))}] {progress:.0f}%")
    print(f"{color}Current Task:{Colors.RESET} {current_task}")
    print(f"{color}Completed Modules:{Colors.RESET} {', '.join(completed) if completed else 'None yet'}")
    
    if interfaces:
        print(f"{color}Interfaces Ready:{Colors.RESET}")
        for interface in interfaces:
            print(f"  • {interface.get('name', 'Unknown')} v{interface.get('version', '?')}")
    
    # Metrics if available
    metrics = agent_data.get('metrics', {})
    if metrics:
        print(f"{color}Performance Metrics:{Colors.RESET}")
        for metric, value in metrics.items():
            print(f"  • {metric}: {value}")
    
    print()

def display_integration_status(status: Dict):
    """Display cross-agent integration status."""
    print(f"{Colors.CYAN}{Colors.BOLD}━━━ Integration Status ━━━{Colors.RESET}")
    
    # Check dependencies
    agent_a_ready = any('DataLoader' in m for m in status.get('agent_a', {}).get('completed_modules', []))
    agent_b_ready = any('TextSearchEngine' in m for m in status.get('agent_b', {}).get('completed_modules', []))
    
    if agent_a_ready:
        print(f"{Colors.GREEN}✓ DataLoader available - Agent B can use real data{Colors.RESET}")
    else:
        print(f"{Colors.YELLOW}⏳ DataLoader pending - Agent B using mocks{Colors.RESET}")
    
    if agent_b_ready:
        print(f"{Colors.GREEN}✓ SearchEngine available - Agent C can optimize{Colors.RESET}")
    else:
        print(f"{Colors.YELLOW}⏳ SearchEngine pending - Agent C working independently{Colors.RESET}")
    
    print()

def count_files_created() -> Dict[str, int]:
    """Count files created in each agent's directories."""
    base_path = Path("blackcore/minimal/query_engine")
    
    counts = {
        'agent_a': sum(1 for _ in base_path.glob("loaders/**/*.py")) + 
                   sum(1 for _ in base_path.glob("filters/**/*.py")) +
                   sum(1 for _ in base_path.glob("sorting/**/*.py")),
        'agent_b': sum(1 for _ in base_path.glob("search/**/*.py")) +
                   sum(1 for _ in base_path.glob("relationships/**/*.py")) +
                   sum(1 for _ in base_path.glob("nlp/**/*.py")),
        'agent_c': sum(1 for _ in base_path.glob("cache/**/*.py")) +
                   sum(1 for _ in base_path.glob("optimization/**/*.py")) +
                   sum(1 for _ in base_path.glob("export/**/*.py"))
    }
    
    return counts

def main():
    """Main monitoring loop."""
    print(f"{Colors.BOLD}Query Engine Agent Monitor{Colors.RESET}")
    print("Press Ctrl+C to exit\n")
    
    try:
        while True:
            clear_screen()
            
            # Header
            print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
            print(f"{Colors.BOLD}Query Engine Development Progress Monitor{Colors.RESET}")
            print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
            
            # Load status
            status = load_status()
            if not status:
                print(f"{Colors.RED}No status file found. Have you run launch-agents.sh?{Colors.RESET}")
                time.sleep(5)
                continue
            
            # Last update
            last_update = format_time_ago(status.get('last_update', ''))
            print(f"Last Update: {last_update}\n")
            
            # Display each agent
            display_agent_status('agent_a', status.get('agent_a', {}), Colors.RED)
            display_agent_status('agent_b', status.get('agent_b', {}), Colors.GREEN)
            display_agent_status('agent_c', status.get('agent_c', {}), Colors.BLUE)
            
            # Integration status
            display_integration_status(status)
            
            # File counts
            file_counts = count_files_created()
            print(f"{Colors.MAGENTA}{Colors.BOLD}━━━ File Creation Progress ━━━{Colors.RESET}")
            print(f"Agent A: {file_counts['agent_a']} files")
            print(f"Agent B: {file_counts['agent_b']} files")
            print(f"Agent C: {file_counts['agent_c']} files")
            print(f"Total: {sum(file_counts.values())} files\n")
            
            # Footer
            print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
            print("Refreshing every 5 seconds...")
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Monitoring stopped.{Colors.RESET}")
        sys.exit(0)

if __name__ == "__main__":
    main()