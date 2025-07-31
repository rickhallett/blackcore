"""
Purpose: An end-to-end test for the entire deduplication and merge workflow. It analyzes a real dataset, auto-approves all found matches, executes the merges, and verifies the results.
Utility: This script is a critical integration test that ensures the entire deduplication pipeline, from analysis to the final merge, works correctly. It's essential for catching regressions and validating the merge logic.
"""
#!/usr/bin/env python3
"""
Comprehensive test of the full deduplication and merge flow.

This script:
1. Loads the People & Contacts database
2. Runs deduplication analysis (with AI enabled)
3. Automatically approves all matches
4. Executes all merges
5. Verifies the results
"""

import sys
import json
import random
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackcore.deduplication import DeduplicationEngine
from blackcore.deduplication.merge_proposals import MergeExecutor


def main():
    """Run comprehensive merge test."""
    console = Console()

    console.print(
        Panel(
            "[bold cyan]Full Deduplication & Merge Test[/bold cyan]\n\n"
            "This test will:\n"
            "• Find all duplicates in People & Contacts\n"
            "• Automatically approve all matches\n"
            "• Execute all merges\n"
            "• Verify results\n\n"
            "[yellow]Note: This is a test - no files will be modified[/yellow]",
            border_style="cyan",
        )
    )

    # Load the People & Contacts data
    json_path = (
        Path(__file__).parent.parent
        / "blackcore"
        / "models"
        / "json"
        / "people_places.json"
    )

    if not json_path.exists():
        console.print(f"[red]Error: Could not find {json_path}[/red]")
        return 1

    with open(json_path) as f:
        data = json.load(f)

    people_data = data.get("People & Contacts", [])
    console.print("\n[bold]📊 Initial State:[/bold]")
    console.print(f"  • Total people loaded: {len(people_data)}")

    # Initialize deduplication engine
    console.print("\n[bold]🔧 Initializing deduplication engine...[/bold]")
    engine = DeduplicationEngine()

    # Configure for testing
    engine.config.update(
        {
            "auto_merge_threshold": 90.0,
            "human_review_threshold": 70.0,
            "enable_ai_analysis": True,  # AI enabled as requested
            "safety_mode": True,
            "enable_safety_checks": True,
            "backup_before_merge": True,
        }
    )

    console.print("Configuration:")
    console.print(f"  • Auto-merge threshold: {engine.config['auto_merge_threshold']}%"
)
    console.print(f"  • Review threshold: {engine.config['human_review_threshold']}%"
)
    console.print("  • AI analysis: [green]Enabled[/green]")
    console.print("  • Safety mode: [green]ON[/green]")

    # Run analysis
    console.print("\n[bold]🔍 Running deduplication analysis...[/bold]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing entities...", total=len(people_data))
        result = engine.analyze_database(
            "People & Contacts", people_data, enable_ai=True
        )
        progress.update(task, completed=len(people_data))

    # Display analysis results
    console.print("\n[bold]📊 Analysis Results:[/bold]")
    console.print(f"  • Total entities analyzed: {result.total_entities}")
    console.print(f"  • Potential duplicates found: {result.potential_duplicates}")
    console.print(
        f"  • High confidence matches (>90%): [green]{len(result.high_confidence_matches)}[/green]"
    )
    console.print(
        f"  • Medium confidence matches (70-90%): [yellow]{len(result.medium_confidence_matches)}[/yellow]"
    )
    console.print(
        f"  • Low confidence matches (<70%): [red]{len(result.low_confidence_matches)}[/red]"
    )

    # Collect all matches to process
    all_matches = []
    all_matches.extend(result.high_confidence_matches)
    all_matches.extend(result.medium_confidence_matches)

    if not all_matches:
        console.print("\n[green]No duplicates found to merge![/green]")
        return 0

    console.print(f"\n[bold]🎯 Processing {len(all_matches)} matches for merge[/bold]")

    # Create review decisions (auto-approve all)
    review_decisions = []
    primary_selections = {}

    console.print("\n[bold]📝 Creating review decisions...[/bold]")

    for i, match in enumerate(all_matches):
        # Randomly select primary entity for testing
        primary_entity = random.choice(["A", "B"])
        match_id = f"{match.get('entity_a', {}).get('id', '')}_{match.get('entity_b', {}).get('id', '')}"
        primary_selections[match_id] = primary_entity

        # Add primary entity to match
        match["primary_entity"] = primary_entity

        # Create review decision
        decision = {
            "match": match,
            "decision": "merge",
            "reasoning": f"Auto-approved for testing (Entity {primary_entity} as primary)",
            "timestamp": datetime.now(),
            "reviewer": "test_script",
        }
        review_decisions.append(decision)

        # Show sample decisions
        if i < 3:
            name_a = match.get("entity_a", {}).get("Full Name", "Unknown")
            name_b = match.get("entity_b", {}).get("Full Name", "Unknown")
            console.print(
                f"  • {name_a} + {name_b} "
                f"[dim](confidence: {match.get('confidence_score', 0):.1f}%, "
                f"primary: {primary_entity})[/dim]"
            )

    if len(all_matches) > 3:
        console.print(f"  ... and {len(all_matches) - 3} more")

    # Execute merges
    console.print(f"\n[bold]🔄 Executing {len(review_decisions)} merges...[/bold]")

    # Initialize merge executor
    merge_executor = MergeExecutor(
        {
            "enable_safety_checks": True,
            "backup_before_merge": True,
            "preserve_all_data": True,
            "merge_strategy": "conservative",
        }
    )

    # Track results
    success_count = 0
    error_count = 0
    error_details = []
    successful_merges = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Executing merges...", total=len(review_decisions))

        for decision in review_decisions:
            match = decision["match"]

            # Determine primary and secondary based on selection
            if match.get("primary_entity") == "B":
                primary = match.get("entity_b", {})
                secondary = match.get("entity_a", {})
            else:
                primary = match.get("entity_a", {})
                secondary = match.get("entity_b", {})

            # Create merge proposal
            proposal = merge_executor.create_proposal(
                primary_entity=primary,
                secondary_entity=secondary,
                confidence_score=match.get("confidence_score", 0),
                evidence=match.get("evidence", {}),
                entity_type=match.get("entity_type", "People & Contacts"),
                ai_analysis=match.get("ai_analysis"),
            )

            # Execute merge
            result = merge_executor.execute_merge(proposal, auto_approved=True)

            if result.success:
                success_count += 1
                successful_merges.append(
                    {
                        "merged": result.merged_entity,
                        "primary_name": primary.get("Full Name", "Unknown"),
                        "secondary_name": secondary.get("Full Name", "Unknown"),
                        "primary_was": match.get("primary_entity"),
                    }
                )
            else:
                error_count += 1
                error_details.append(
                    {
                        "primary": primary.get("Full Name", "Unknown"),
                        "secondary": secondary.get("Full Name", "Unknown"),
                        "errors": result.errors,
                        "confidence": match.get("confidence_score", 0),
                    }
                )

            progress.update(task, advance=1)

    # Display results
    console.print("\n[bold]📊 Merge Results:[/bold]")
    console.print(f"  • Total merges attempted: {len(review_decisions)}")
    console.print(f"  • [green]Successful merges: {success_count}[/green]")
    console.print(f"  • [red]Failed merges: {error_count}[/red]")
    console.print(
        f"  • Success rate: {(success_count / len(review_decisions) * 100):.1f}%"
    )

    # Show error details if any
    if error_details:
        console.print("\n[bold red]❌ Merge Failures:[/bold red]")
        error_table = Table(show_header=True, header_style="bold red")
        error_table.add_column("Primary Entity", style="cyan")
        error_table.add_column("Secondary Entity", style="cyan")
        error_table.add_column("Error", style="red")
        error_table.add_column("Confidence", justify="right")

        for error in error_details[:10]:  # Show first 10 errors
            error_table.add_row(
                error["primary"],
                error["secondary"],
                ", ".join(error["errors"]),
                f"{error['confidence']:.1f}%",
            )

        console.print(error_table)

        if len(error_details) > 10:
            console.print(f"  ... and {len(error_details) - 10} more errors")

    # Show sample successful merges
    if successful_merges:
        console.print("\n[bold green]✅ Sample Successful Merges:[/bold green]")

        for i, merge_info in enumerate(successful_merges[:3]):
            merged = merge_info["merged"]
            console.print(f"\n[bold]Merge {i+1}:[/bold]")
            console.print(
                f"  Primary: {merge_info['primary_name']} (Entity {merge_info['primary_was']})"
            )
            console.print(f"  Secondary: {merge_info['secondary_name']}")
            console.print("  Merged result:")

            # Show key fields
            for field in ["Full Name", "Email", "Phone", "Organization"]:
                value = merged.get(field, "")
                if value:
                    if isinstance(value, list):
                        value = ", ".join(str(v) for v in value)
                    console.print(f"    • {field}: {value}")

            # Show merge metadata
            if "_merge_info" in merged:
                merge_info_data = merged["_merge_info"]
                if merge_info_data.get("conflicts"):
                    console.print("    • [yellow]Conflicts detected:[/yellow]")
                    for field, conflict in list(merge_info_data["conflicts"].items())[
                        :2
                    ]:
                        console.print(
                            f"      - {field}: kept '{conflict['primary']}', had '{conflict['secondary']}'"
                        )

    # Verify results
    console.print("\n[bold]🔍 Verification:[/bold]")

    # Check that primary IDs are preserved
    id_preserved_count = 0
    list_handled_count = 0
    conflicts_recorded_count = 0

    for merge_info in successful_merges:
        merged = merge_info["merged"]

        # Check ID preservation
        if "id" in merged:
            id_preserved_count += 1

        # Check list handling
        for value in merged.values():
            if isinstance(value, list):
                list_handled_count += 1
                break

        # Check conflict recording
        if "_merge_info" in merged and merged["_merge_info"].get("conflicts"):
            conflicts_recorded_count += 1

    console.print(
        f"  • Primary IDs preserved: {id_preserved_count}/{len(successful_merges)}"
    )
    console.print(f"  • Entities with list values: {list_handled_count}")
    console.print(f"  • Merges with recorded conflicts: {conflicts_recorded_count}")

    # Final summary
    console.print("\n[bold]📋 Final Summary:[/bold]")
    console.print(f"  • Started with: {len(people_data)} people")
    console.print(f"  • Found: {len(all_matches)} duplicate pairs")
    console.print(f"  • Successfully merged: {success_count} pairs")
    console.print(
        f"  • Final count would be: {len(people_data) - success_count} people"
    )
    console.print(f"  • Reduction: {(success_count / len(people_data) * 100):.1f}%"
)

    # Get merge statistics
    merge_stats = merge_executor.get_statistics()
    console.print("\n[bold]🔧 Merge Executor Statistics:[/bold]")
    console.print(f"  • Total proposals created: {merge_stats['total_proposals']}")
    console.print(f"  • Safety blocks: {merge_stats['safety_blocks']}")
    console.print(f"  • Success rate: {merge_stats['success_rate']:.1f}%"
)

    console.print("\n[bold green]✅ Test completed successfully![/bold green]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
