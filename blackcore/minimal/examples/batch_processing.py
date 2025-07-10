"""Batch processing example for multiple transcripts."""

import os
from pathlib import Path
from blackcore.minimal import TranscriptProcessor
from blackcore.minimal.utils import load_transcripts_from_directory, save_processing_result


def create_sample_transcripts(directory: str):
    """Create sample transcript files for demonstration."""
    Path(directory).mkdir(exist_ok=True)

    transcripts = [
        {
            "filename": "council-meeting-2025-01-05.json",
            "data": {
                "title": "Town Council Regular Meeting",
                "content": """Regular council meeting held January 5, 2025.
                
Attendees: Mayor John Smith, Councillor Jane Davis, Councillor Bob Wilson

Agenda Items:
1. Budget Review - Councillor Davis presented Q4 budget report
2. Planning Applications - 3 new applications reviewed
3. Community Feedback - Concerns raised about beach access

Action: Jane Davis to prepare detailed budget analysis by January 15.""",
                "date": "2025-01-05T18:00:00",
                "source": "google_meet",
            },
        },
        {
            "filename": "planning-committee-2025-01-07.txt",
            "content": """Planning Committee Meeting - January 7, 2025

Present: Sarah Johnson (Planning), Mike Brown (Development), Lisa Chen (Environment)

Key Discussion:
- Beachfront development proposal review
- Environmental impact assessment required
- Mike Brown pushing for fast-track approval despite missing assessments
- Lisa Chen raised concerns about protected habitat

This appears to be a violation of planning procedures by Mike Brown.""",
        },
        {
            "filename": "community-forum-2025-01-08.json",
            "data": {
                "title": "Community Forum - Beach Access Rights",
                "content": """Community forum organized by Mark Wilson on January 8.

Over 50 residents attended to discuss beach access issues.

Key Speakers:
- Mark Wilson (Organizer) - Presented historical access rights
- Helen Parker (Local Resident) - 40 years of beach use testimony  
- Tom Anderson (Legal Advisor) - Explained legal precedents

Main Concerns:
1. Recent restrictions on traditional access paths
2. Preferential treatment for tourist facilities
3. Lack of council consultation

Resolution: Form action committee led by Helen Parker to document access rights.""",
                "date": "2025-01-08T19:00:00",
                "source": "personal_note",
            },
        },
    ]

    # Save transcripts
    for transcript in transcripts:
        if transcript["filename"].endswith(".json"):
            import json

            filepath = Path(directory) / transcript["filename"]
            with open(filepath, "w") as f:
                json.dump(transcript["data"], f, indent=2)
        else:
            filepath = Path(directory) / transcript["filename"]
            with open(filepath, "w") as f:
                f.write(transcript["content"])

    print(f"✅ Created {len(transcripts)} sample transcripts in {directory}/")


def main():
    """Demonstrate batch processing of multiple transcripts."""

    print("=== Minimal Transcript Processor - Batch Processing ===\n")

    # Check for API keys
    if not os.getenv("NOTION_API_KEY") or not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  API keys not found in environment!")
        print("Please set NOTION_API_KEY and ANTHROPIC_API_KEY")
        return

    # Create sample transcripts
    transcript_dir = "./sample_transcripts"
    print("1️⃣ Creating sample transcripts...")
    create_sample_transcripts(transcript_dir)

    # Initialize processor
    print("\n2️⃣ Initializing processor...")
    processor = TranscriptProcessor()

    # Configuration options
    processor.config.processing.verbose = True  # Show progress

    # Load transcripts
    print("\n3️⃣ Loading transcripts from directory...")
    transcripts = load_transcripts_from_directory(transcript_dir)
    print(f"✅ Loaded {len(transcripts)} transcripts")

    for t in transcripts:
        print(f"   - {t.title} ({t.date.strftime('%Y-%m-%d') if t.date else 'undated'})")

    # Process in batch
    print("\n4️⃣ Processing transcripts in batch...")
    print("=" * 50)

    batch_result = processor.process_batch(transcripts)

    print("=" * 50)
    print("\n📊 Batch Processing Results:")
    print(f"   Total transcripts: {batch_result.total_transcripts}")
    print(f"   Successful: {batch_result.successful}")
    print(f"   Failed: {batch_result.failed}")
    print(f"   Success rate: {batch_result.success_rate:.1%}")

    if batch_result.processing_time:
        avg_time = batch_result.processing_time / batch_result.total_transcripts
        print(f"   Total time: {batch_result.processing_time:.2f}s")
        print(f"   Average time per transcript: {avg_time:.2f}s")

    # Show summary of entities created
    total_created = sum(len(r.created) for r in batch_result.results)
    total_updated = sum(len(r.updated) for r in batch_result.results)

    print(f"\n📝 Entity Summary:")
    print(f"   Total entities created: {total_created}")
    print(f"   Total entities updated: {total_updated}")

    # Save detailed results
    results_file = "batch_results.json"
    save_processing_result(batch_result.dict(), results_file)
    print(f"\n💾 Detailed results saved to: {results_file}")

    # Show any failures
    if batch_result.failed > 0:
        print("\n⚠️  Failed transcripts:")
        for i, result in enumerate(batch_result.results):
            if not result.success:
                print(f"   - Transcript {i + 1}: {', '.join(e.message for e in result.errors)}")

    print("\n" + "=" * 50)
    print("💡 Tips for batch processing:")
    print("   - Use dry-run mode first to preview: --dry-run")
    print("   - Process in smaller batches for large datasets")
    print("   - Check cache stats: processor.cache.get_stats()")
    print("   - Monitor rate limits in Notion API dashboard")


if __name__ == "__main__":
    main()
