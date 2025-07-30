"""
Standard Mode CLI for Blackcore Deduplication Engine.

Provides an interactive, user-friendly interface for deduplication with
guided workflows, real-time progress tracking, and match review capabilities.
"""

import asyncio
import json
import sys
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import signal

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich import print as rprint

from .ui_components import UIComponents, ProgressTracker, MatchReviewDisplay
from .config_wizard import ConfigurationWizard
from .async_engine import AsyncDeduplicationEngine, ProgressUpdate
from ..review_interface import ReviewDecision


class StandardModeCLI:
    """
    Interactive CLI for deduplication in Standard Mode.
    
    Features:
    - Guided configuration
    - Real-time progress tracking
    - Interactive match review
    - Keyboard navigation
    - Async operations
    """
    
    def __init__(self):
        """Initialize the Standard Mode CLI."""
        self.console = Console()
        self.ui = UIComponents()
        self.config_wizard = ConfigurationWizard(self.console)
        self.engine = None
        self.current_results = None
        self.review_decisions = []
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_interrupt)
        
    def _handle_interrupt(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        if self.engine:
            self.engine.cancel()
        self.console.print("\n[yellow]Operation cancelled by user[/yellow]")
        
    async def run(self):
        """Main entry point for the CLI."""
        try:
            # Show welcome screen
            await self._show_welcome()
            
            # Main menu loop
            while True:
                choice = await self._show_main_menu()
                
                if choice == "1":
                    await self._new_analysis()
                elif choice == "2":
                    await self._configure_settings()
                elif choice == "3":
                    await self._view_statistics()
                elif choice == "4":
                    await self._show_help()
                elif choice == "5":
                    break
                else:
                    self.console.print("[red]Invalid choice, please try again[/red]")
                    
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Exiting...[/yellow]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
            raise
        finally:
            if self.engine:
                await self.engine.shutdown()
                
    async def _show_welcome(self):
        """Show welcome screen."""
        self.console.clear()
        welcome_panel = self.ui.create_welcome_panel()
        self.console.print(welcome_panel)
        
        # Wait for user input
        await asyncio.get_event_loop().run_in_executor(None, input)
        
    async def _show_main_menu(self) -> str:
        """Show main menu and get user choice."""
        self.console.clear()
        menu_panel = self.ui.create_main_menu()
        self.console.print(menu_panel)
        
        # Get user choice
        choice = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: Prompt.ask("\n[cyan]Enter your choice[/cyan]", choices=["1", "2", "3", "4", "5"])
        )
        
        return choice
        
    async def _new_analysis(self):
        """Run a new deduplication analysis."""
        self.console.clear()
        self.console.print(Panel(
            "[bold cyan]New Deduplication Analysis[/bold cyan]",
            border_style="cyan"
        ))
        
        # Load available databases
        databases = await self._load_databases()
        if not databases:
            self.console.print("[red]No databases found to analyze[/red]")
            await asyncio.sleep(2)
            return
            
        # Configure analysis
        config = await self.config_wizard.run_wizard(
            {name: len(records) for name, records in databases.items()}
        )
        
        # Filter selected databases
        if "databases" in config:
            selected_dbs = {
                name: records 
                for name, records in databases.items() 
                if name in config["databases"]
            }
        else:
            selected_dbs = databases
            
        # Initialize engine
        self.engine = AsyncDeduplicationEngine(config)
        self.engine.update_config(config)
        
        # Run analysis
        results = await self._run_analysis(selected_dbs)
        
        if results:
            self.current_results = results
            
            # Show summary
            await self._show_analysis_summary(results)
            
            # Offer to review matches
            if await self._prompt_review_matches():
                await self._review_matches(results)
                
    async def _load_databases(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load available databases."""
        # Get the module's parent directory (blackcore package root)
        module_path = Path(__file__).parent.parent.parent
        json_dir = module_path / "models" / "json"
        
        databases = {}
        
        if json_dir.exists():
            for json_file in json_dir.glob("*.json"):
                # Skip backup files
                if "backup" in json_file.name:
                    continue
                    
                try:
                    with open(json_file) as f:
                        data = json.load(f)
                        # Extract database name and records
                        for db_name, records in data.items():
                            if isinstance(records, list):
                                databases[db_name] = records
                except Exception as e:
                    self.console.print(f"[yellow]Warning: Could not load {json_file}: {e}[/yellow]")
        else:
            self.console.print(f"[yellow]Warning: JSON directory not found at {json_dir}[/yellow]")
                    
        return databases
        
    async def _run_analysis(
        self,
        databases: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Run the deduplication analysis with progress tracking."""
        self.console.clear()
        
        # Create progress tracker
        tracker = ProgressTracker(self.console)
        
        # Progress callback
        async def on_progress(update: ProgressUpdate):
            await tracker.update_progress(update)
            
        try:
            # Run analysis with progress tracking
            async for _ in tracker.track_progress():
                results = await self.engine.analyze_databases_async(
                    databases,
                    progress_callback=on_progress
                )
                
            return results
            
        except asyncio.CancelledError:
            self.console.print("\n[yellow]Analysis cancelled[/yellow]")
            return None
        except Exception as e:
            self.console.print(f"\n[red]Analysis failed: {e}[/red]")
            return None
            
    async def _show_analysis_summary(self, results: Dict[str, Any]):
        """Show analysis summary."""
        self.console.clear()
        
        # Calculate totals
        total_entities = 0
        total_duplicates = 0
        high_confidence = 0
        medium_confidence = 0
        low_confidence = 0
        
        for db_result in results.values():
            total_entities += db_result.total_entities
            total_duplicates += db_result.potential_duplicates
            high_confidence += len(db_result.high_confidence_matches)
            medium_confidence += len(db_result.medium_confidence_matches)
            low_confidence += len(db_result.low_confidence_matches)
            
        summary = f"""[bold cyan]Analysis Complete![/bold cyan]

[bold]Summary:[/bold]
• Total entities analyzed: {total_entities:,}
• Potential duplicates found: {total_duplicates:,}

[bold]Confidence Distribution:[/bold]
• [green]High confidence (>90%):[/green] {high_confidence}
• [yellow]Medium confidence (70-90%):[/yellow] {medium_confidence}
• [red]Low confidence (<70%):[/red] {low_confidence}

[bold]For Review:[/bold]
• {high_confidence} high confidence matches (in safety mode)
• {medium_confidence} medium confidence matches 
• {low_confidence} low confidence matches (optional review)

[bold]Total matches available for review:[/bold] {high_confidence + medium_confidence + low_confidence}"""
        
        self.console.print(Panel(
            summary,
            title="Analysis Summary",
            border_style="green",
            padding=(1, 2)
        ))
        
        # Wait for user
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: Prompt.ask("\n[cyan]Press Enter to continue[/cyan]")
        )
        
    async def _prompt_review_matches(self) -> bool:
        """Prompt user to review matches."""
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: Confirm.ask("\n[yellow]Would you like to review the matches?[/yellow]", default=True)
        )
        
    async def _review_matches(self, results: Dict[str, Any]):
        """Interactive match review interface."""
        # Collect all matches that need review
        matches_to_review = []
        
        for db_name, db_result in results.items():
            # Add medium confidence matches (these need review)
            for match in db_result.medium_confidence_matches:
                match["database"] = db_name
                matches_to_review.append(match)
                
            # Optionally add high confidence matches if in safety mode
            if self.engine.engine.config.get("safety_mode", True):
                for match in db_result.high_confidence_matches:
                    match["database"] = db_name
                    matches_to_review.append(match)
                    
            # Add low confidence matches for manual review
            # (User explicitly said they want to review them)
            for match in db_result.low_confidence_matches:
                match["database"] = db_name
                matches_to_review.append(match)
                    
        if not matches_to_review:
            self.console.print("[yellow]No matches require review[/yellow]")
            await asyncio.sleep(2)
            return
            
        # Create review display
        review_display = MatchReviewDisplay(self.console)
        
        # Review loop
        current_index = 0
        self.review_decisions = []
        
        # Track primary entity selections for each match
        primary_selections = {}
        
        while current_index < len(matches_to_review):
            match = matches_to_review[current_index]
            match_id = f"{match.get('entity_a', {}).get('id', '')}_{match.get('entity_b', {}).get('id', '')}"
            
            # Get or set primary entity for this match
            if match_id not in primary_selections:
                primary_selections[match_id] = "A"
            match["primary_entity"] = primary_selections[match_id]
            
            # Clear and show match
            self.console.clear()
            layout = review_display.create_match_comparison(
                match,
                current_index + 1,
                len(matches_to_review)
            )
            self.console.print(layout)
            
            # Get user action
            action = await self._get_review_action()
            
            if action == "a":  # Approve
                reasoning = f"User approved merge with Entity {match['primary_entity']} as primary"
                self._record_decision(match, "merge", reasoning)
                current_index += 1
            elif action == "r":  # Reject
                self._record_decision(match, "separate", "User rejected - not duplicates")
                current_index += 1
            elif action == "d":  # Defer
                self._record_decision(match, "defer", "User deferred decision")
                current_index += 1
            elif action == "s":  # Swap primary
                # Toggle primary entity
                primary_selections[match_id] = "B" if primary_selections[match_id] == "A" else "A"
                self.console.print(f"\n[yellow]Primary entity swapped to: {primary_selections[match_id]}[/yellow]")
                await asyncio.sleep(1)
            elif action == "m":  # Merge preview
                await self._show_merge_preview(match, review_display)
            elif action == "n":  # Next
                current_index = min(current_index + 1, len(matches_to_review) - 1)
            elif action == "p":  # Previous
                current_index = max(current_index - 1, 0)
            elif action == "e":  # Evidence
                await self._show_detailed_evidence(match)
            elif action == "h" or action == "?":  # Help
                await self._show_review_help(review_display)
            elif action == "q":  # Quit
                if await self._confirm_quit_review():
                    break
                    
        # Show review summary
        if self.review_decisions:
            await self._show_review_summary(review_display)
            
            # Ask if user wants to apply the decisions
            if await self._prompt_apply_decisions():
                await self._apply_review_decisions()
            
    async def _get_review_action(self) -> str:
        """Get review action from user."""
        valid_actions = ["a", "r", "d", "n", "p", "e", "s", "m", "h", "?", "q"]
        
        while True:
            action = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: Prompt.ask(
                    "\n[cyan]Action[/cyan]",
                    choices=valid_actions,
                    show_choices=False
                ).lower()
            )
            
            if action in valid_actions:
                return action
                
    def _record_decision(self, match: Dict[str, Any], decision: str, reasoning: str):
        """Record a review decision."""
        self.review_decisions.append({
            "match": match,
            "decision": decision,
            "reasoning": reasoning,
            "timestamp": datetime.now(),
            "reviewer": "cli_user"
        })
        
    async def _show_detailed_evidence(self, match: Dict[str, Any]):
        """Show detailed evidence for a match."""
        self.console.clear()
        
        # Create detailed evidence panel
        evidence_lines = [
            f"[bold]Database:[/bold] {match.get('database', 'Unknown')}",
            f"[bold]Entity Type:[/bold] {match.get('entity_type', 'Unknown')}",
            f"[bold]Overall Confidence:[/bold] {match.get('confidence_score', 0):.1f}%",
            ""
        ]
        
        # Field-by-field comparison
        scores = match.get("similarity_scores", {})
        if scores:
            evidence_lines.append("[bold]Field Similarity Scores:[/bold]")
            for field, score_data in scores.items():
                if isinstance(score_data, dict):
                    evidence_lines.append(
                        f"  {field}: {score_data.get('composite', 0):.1f}% "
                        f"(exact: {score_data.get('exact', 0)}, "
                        f"fuzzy: {score_data.get('fuzzy', 0):.1f})"
                    )
                    
        # AI analysis
        ai = match.get("ai_analysis", {})
        if ai:
            evidence_lines.append("\n[bold]AI Analysis:[/bold]")
            evidence_lines.append(f"  Model: {ai.get('model', 'Unknown')}")
            evidence_lines.append(f"  Confidence: {ai.get('confidence_score', 0):.1f}%")
            evidence_lines.append(f"  Reasoning: {ai.get('reasoning', 'N/A')}")
            evidence_lines.append(f"  Risk: {ai.get('risk_assessment', 'Unknown')}")
            
        panel = Panel(
            "\n".join(evidence_lines),
            title="Detailed Evidence",
            border_style="blue",
            padding=(1, 2)
        )
        
        self.console.print(panel)
        
        # Wait for user
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: Prompt.ask("\n[cyan]Press Enter to continue[/cyan]")
        )
        
    async def _show_merge_preview(self, match: Dict[str, Any], review_display: MatchReviewDisplay):
        """Show merge preview."""
        self.console.clear()
        
        preview_panel = review_display.create_merge_preview(
            match.get("entity_a", {}),
            match.get("entity_b", {}),
            match.get("primary_entity", "A")
        )
        self.console.print(preview_panel)
        
        # Wait for user
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: Prompt.ask("\n[cyan]Press Enter to continue[/cyan]")
        )
        
    async def _show_review_help(self, review_display: MatchReviewDisplay):
        """Show review help."""
        self.console.clear()
        help_panel = review_display.display_help()
        self.console.print(help_panel)
        
        # Wait for user
        await asyncio.get_event_loop().run_in_executor(None, input)
        
    async def _confirm_quit_review(self) -> bool:
        """Confirm quit review session."""
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: Confirm.ask(
                "\n[yellow]Quit review session? (Progress will be saved)[/yellow]",
                default=False
            )
        )
        
    async def _show_review_summary(self, review_display: MatchReviewDisplay):
        """Show review session summary."""
        self.console.clear()
        
        # Count decisions
        approved = sum(1 for d in self.review_decisions if d["decision"] == "merge")
        rejected = sum(1 for d in self.review_decisions if d["decision"] == "separate")
        deferred = sum(1 for d in self.review_decisions if d["decision"] == "defer")
        
        summary_panel = review_display.display_review_summary(
            len(self.review_decisions),
            approved,
            rejected,
            deferred
        )
        
        self.console.print(summary_panel)
        
        # Wait for user
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: Prompt.ask("\n[cyan]Press Enter to continue[/cyan]")
        )
        
    async def _prompt_apply_decisions(self) -> bool:
        """Prompt user to apply the review decisions."""
        approved_count = sum(1 for d in self.review_decisions if d["decision"] == "merge")
        
        if approved_count == 0:
            self.console.print("\n[yellow]No merges were approved. Nothing to apply.[/yellow]")
            await asyncio.sleep(2)
            return False
            
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: Confirm.ask(
                f"\n[yellow]Apply {approved_count} approved merge(s)?[/yellow]",
                default=True
            )
        )
        
    async def _apply_review_decisions(self):
        """Apply the review decisions (execute merges)."""
        self.console.clear()
        self.console.print(Panel(
            "[bold cyan]Applying Review Decisions[/bold cyan]",
            border_style="cyan"
        ))
        
        # Import merge executor
        from ..merge_proposals import MergeExecutor
        
        # Initialize merge executor with config
        merge_config = {}
        if self.engine and hasattr(self.engine, 'engine') and hasattr(self.engine.engine, 'config'):
            merge_config = self.engine.engine.config.copy()
        merge_executor = MergeExecutor(merge_config)
        
        # Process approved merges
        approved_merges = [d for d in self.review_decisions if d["decision"] == "merge"]
        
        if not approved_merges:
            self.console.print("[yellow]No merges to apply[/yellow]")
            return
            
        # Create progress
        from rich.progress import Progress, SpinnerColumn, TextColumn
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task(
                f"Applying {len(approved_merges)} merge(s)...",
                total=len(approved_merges)
            )
            
            success_count = 0
            error_count = 0
            
            for decision in approved_merges:
                match = decision["match"]
                
                # Determine primary and secondary based on user selection
                primary_entity_selection = match.get("primary_entity", "A")
                
                if primary_entity_selection == "A":
                    primary = match.get("entity_a", {})
                    secondary = match.get("entity_b", {})
                else:
                    # User selected B as primary
                    primary = match.get("entity_b", {})
                    secondary = match.get("entity_a", {})
                
                # Create merge proposal
                proposal = merge_executor.create_proposal(
                    primary_entity=primary,
                    secondary_entity=secondary,
                    confidence_score=match.get("confidence_score", 0),
                    evidence=match.get("evidence", {}),
                    entity_type=match.get("entity_type", ""),
                    ai_analysis=match.get("ai_analysis")
                )
                
                # Execute merge
                result = merge_executor.execute_merge(proposal, auto_approved=True)
                
                if result.success:
                    success_count += 1
                    self.console.print(
                        f"[green]✓[/green] Merged: {primary.get('Full Name', 'Unknown')} "
                        f"with {secondary.get('Full Name', 'Unknown')}"
                    )
                else:
                    error_count += 1
                    self.console.print(
                        f"[red]✗[/red] Failed to merge: {primary.get('Full Name', 'Unknown')} - "
                        f"{', '.join(result.errors)}"
                    )
                    
                progress.update(task, advance=1)
                
        # Show final summary
        self.console.print(f"\n[bold]Merge Summary:[/bold]")
        self.console.print(f"[green]Successful merges:[/green] {success_count}")
        if error_count > 0:
            self.console.print(f"[red]Failed merges:[/red] {error_count}")
            
        # Save audit trail
        if success_count > 0:
            self.console.print("\n[dim]Audit trail has been saved[/dim]")
            
        # Wait for user
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: Prompt.ask("\n[cyan]Press Enter to continue[/cyan]")
        )
        
    async def _configure_settings(self):
        """Configure settings."""
        config = await self.config_wizard.run_wizard()
        
        # Save configuration
        if await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: Confirm.ask("\n[yellow]Save configuration?[/yellow]", default=True)
        ):
            self.config_wizard.save_config(config)
            
    async def _view_statistics(self):
        """View deduplication statistics."""
        self.console.clear()
        
        if not self.engine:
            self.console.print("[yellow]No analysis has been run yet[/yellow]")
            await asyncio.sleep(2)
            return
            
        stats = self.engine.get_statistics()
        
        stats_text = f"""[bold cyan]Deduplication Statistics[/bold cyan]

[bold]Engine Statistics:[/bold]
• Total comparisons: {stats.get('engine_stats', {}).get('total_comparisons', 0):,}
• AI analyses performed: {stats.get('engine_stats', {}).get('ai_analyses_performed', 0)}
• Human reviews created: {stats.get('engine_stats', {}).get('human_reviews_created', 0)}

[bold]Current Session:[/bold]
• Review decisions made: {len(self.review_decisions)}"""
        
        self.console.print(Panel(
            stats_text,
            title="Statistics",
            border_style="blue",
            padding=(1, 2)
        ))
        
        # Wait for user
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: Prompt.ask("\n[cyan]Press Enter to continue[/cyan]")
        )
        
    async def _show_help(self):
        """Show help documentation."""
        self.console.clear()
        
        help_text = """[bold cyan]Blackcore Deduplication - Help[/bold cyan]

[bold]Overview:[/bold]
The deduplication engine uses a 4-layer approach to identify duplicates:
1. Fuzzy matching for initial detection
2. AI analysis for complex cases
3. Graph analysis for relationships
4. Human review for uncertain matches

[bold]Workflow:[/bold]
1. Select databases to analyze
2. Configure thresholds and settings
3. Run analysis (with progress tracking)
4. Review matches interactively
5. Decisions are saved for audit

[bold]Tips:[/bold]
• Start with default thresholds (90% auto, 70% review)
• Enable AI for better accuracy (requires API keys)
• Use keyboard shortcuts for efficient review
• All operations are safe - no automatic changes

[bold]Support:[/bold]
See documentation at: dedupe-engine-commands.md"""
        
        self.console.print(Panel(
            help_text,
            title="Help",
            border_style="blue",
            padding=(1, 2)
        ))
        
        # Wait for user
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: Prompt.ask("\n[cyan]Press Enter to continue[/cyan]")
        )


def main():
    """Entry point for the Standard Mode CLI."""
    cli = StandardModeCLI()
    asyncio.run(cli.run())


if __name__ == "__main__":
    main()