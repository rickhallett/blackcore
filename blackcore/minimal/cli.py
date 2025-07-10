"""Command-line interface for minimal transcript processor."""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional

from .transcript_processor import TranscriptProcessor
from .config import ConfigManager
from .utils import (
    load_transcript_from_file,
    load_transcripts_from_directory,
    save_processing_result,
    create_sample_transcript,
    create_sample_config,
)
from .models import TranscriptInput


def process_single_transcript(args):
    """Process a single transcript file."""
    print(f"Processing transcript: {args.transcript}")

    # Load transcript
    try:
        transcript = load_transcript_from_file(args.transcript)
    except Exception as e:
        print(f"Error loading transcript: {e}")
        return 1

    # Initialize processor
    processor = TranscriptProcessor(config_path=args.config)

    # Set processing options
    processor.config.processing.dry_run = args.dry_run
    processor.config.processing.verbose = args.verbose

    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made to Notion")

    # Process
    result = processor.process_transcript(transcript)

    # Save results if requested
    if args.output:
        save_processing_result(result.dict(), args.output)
        print(f"💾 Results saved to: {args.output}")

    return 0 if result.success else 1


def process_batch(args):
    """Process multiple transcripts from a directory."""
    print(f"Processing transcripts from: {args.directory}")

    # Load transcripts
    try:
        transcripts = load_transcripts_from_directory(args.directory)
        print(f"Found {len(transcripts)} transcripts")
    except Exception as e:
        print(f"Error loading transcripts: {e}")
        return 1

    if not transcripts:
        print("No transcripts found in directory")
        return 1

    # Initialize processor
    processor = TranscriptProcessor(config_path=args.config)

    # Set processing options
    processor.config.processing.dry_run = args.dry_run
    processor.config.processing.verbose = args.verbose
    processor.config.processing.batch_size = args.batch_size

    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made to Notion")

    # Process batch
    batch_result = processor.process_batch(transcripts)

    # Print summary
    print(f"\n✅ Batch processing complete:")
    print(f"   Success rate: {batch_result.success_rate:.1%}")
    print(f"   Time: {batch_result.processing_time:.2f}s" if batch_result.processing_time else "")

    # Save results if requested
    if args.output:
        save_processing_result(batch_result.dict(), args.output)
        print(f"💾 Results saved to: {args.output}")

    return 0 if batch_result.failed == 0 else 1


def generate_config(args):
    """Generate a configuration template."""
    config_manager = ConfigManager()

    if args.output:
        config_manager.save_template(args.output)
        print(f"✅ Configuration template saved to: {args.output}")
    else:
        # Print to stdout
        config = create_sample_config()
        print(json.dumps(config, indent=2))

    return 0


def generate_sample(args):
    """Generate a sample transcript."""
    sample = create_sample_transcript()

    if args.output:
        with open(args.output, "w") as f:
            json.dump(sample, f, indent=2)
        print(f"✅ Sample transcript saved to: {args.output}")
    else:
        # Print to stdout
        print(json.dumps(sample, indent=2))

    return 0


def cache_info(args):
    """Display cache information."""
    from .cache import SimpleCache

    cache = SimpleCache(cache_dir=args.cache_dir)
    stats = cache.get_stats()

    print("📊 Cache Statistics:")
    print(f"   Directory: {stats['cache_directory']}")
    print(f"   Total entries: {stats['total_entries']}")
    print(f"   Active entries: {stats['active_entries']}")
    print(f"   Expired entries: {stats['expired_entries']}")
    print(f"   Total size: {stats['total_size_bytes']:,} bytes")

    if args.cleanup:
        removed = cache.cleanup_expired()
        print(f"\n🧹 Cleaned up {removed} expired entries")

    if args.clear:
        cache.clear()
        print("\n🗑️  Cache cleared")

    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Minimal Transcript Processor - Extract entities from transcripts and update Notion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single transcript
  python -m blackcore.minimal process transcript.json
  
  # Process with dry run
  python -m blackcore.minimal process transcript.txt --dry-run
  
  # Batch process transcripts
  python -m blackcore.minimal process-batch ./transcripts/
  
  # Generate configuration template
  python -m blackcore.minimal generate-config > config.json
  
  # View cache statistics
  python -m blackcore.minimal cache-info --cleanup
""",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Process single transcript
    process_parser = subparsers.add_parser("process", help="Process a single transcript")
    process_parser.add_argument("transcript", help="Path to transcript file (JSON or text)")
    process_parser.add_argument("-c", "--config", help="Path to configuration file")
    process_parser.add_argument("-o", "--output", help="Save results to file")
    process_parser.add_argument(
        "--dry-run", action="store_true", help="Preview without making changes"
    )
    process_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    # Process batch
    batch_parser = subparsers.add_parser("process-batch", help="Process multiple transcripts")
    batch_parser.add_argument("directory", help="Directory containing transcript files")
    batch_parser.add_argument("-c", "--config", help="Path to configuration file")
    batch_parser.add_argument("-o", "--output", help="Save results to file")
    batch_parser.add_argument(
        "--batch-size", type=int, default=10, help="Number of transcripts per batch"
    )
    batch_parser.add_argument(
        "--dry-run", action="store_true", help="Preview without making changes"
    )
    batch_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    # Generate config
    config_parser = subparsers.add_parser("generate-config", help="Generate configuration template")
    config_parser.add_argument("-o", "--output", help="Save to file (default: print to stdout)")

    # Generate sample
    sample_parser = subparsers.add_parser("generate-sample", help="Generate sample transcript")
    sample_parser.add_argument("-o", "--output", help="Save to file (default: print to stdout)")

    # Cache management
    cache_parser = subparsers.add_parser("cache-info", help="Display cache information")
    cache_parser.add_argument("--cache-dir", default=".cache", help="Cache directory")
    cache_parser.add_argument("--cleanup", action="store_true", help="Remove expired entries")
    cache_parser.add_argument("--clear", action="store_true", help="Clear all cache")

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    try:
        if args.command == "process":
            return process_single_transcript(args)
        elif args.command == "process-batch":
            return process_batch(args)
        elif args.command == "generate-config":
            return generate_config(args)
        elif args.command == "generate-sample":
            return generate_sample(args)
        elif args.command == "cache-info":
            return cache_info(args)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.verbose if "verbose" in args else False:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
