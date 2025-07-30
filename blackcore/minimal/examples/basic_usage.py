"""Basic usage example for minimal transcript processor."""

import os
from datetime import datetime
from blackcore.minimal import TranscriptProcessor, TranscriptInput
from blackcore.minimal.utils import create_sample_config


def main():
    """Demonstrate basic usage of the transcript processor."""

    print("=== Minimal Transcript Processor - Basic Usage ===\n")

    # Check for API keys
    if not os.getenv("NOTION_API_KEY") or not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  API keys not found in environment!")
        print("Please set:")
        print("  - NOTION_API_KEY")
        print("  - ANTHROPIC_API_KEY (or OPENAI_API_KEY)")
        print("\nFor this demo, we'll use a sample configuration.")

        # Save sample config
        config_path = "sample_config.json"
        import json

        with open(config_path, "w") as f:
            json.dump(create_sample_config(), f, indent=2)
        print(f"\n✅ Created sample configuration at: {config_path}")
        return

    # Initialize processor
    print("1️⃣ Initializing processor...")
    processor = TranscriptProcessor()
    print("✅ Processor initialized with environment variables\n")

    # Create a sample transcript
    print("2️⃣ Creating sample transcript...")
    transcript = TranscriptInput(
        title="Meeting with Mayor - Beach Hut Survey Discussion",
        content="""Meeting held on January 9, 2025 with Mayor John Smith of Swanage Town Council.

Present:
- Mayor John Smith (Swanage Town Council)
- Sarah Johnson (Council Planning Department)
- Mark Wilson (Community Representative)

Discussion Points:

1. Beach Hut Survey Concerns
The Mayor expressed concerns about the methodology used in the recent beach hut survey. 
He stated that the survey failed to capture input from long-term residents and focused 
primarily on tourist opinions.

Sarah Johnson from Planning noted that the survey was conducted according to standard 
procedures but acknowledged that the timing (during peak tourist season) may have 
skewed results.

2. Action Items
- Mark Wilson to organize a community meeting for resident feedback (Due: January 20)
- Planning Department to review survey methodology (Due: February 1)
- Mayor to draft letter to county council highlighting concerns

3. Identified Issues
The Mayor's dismissal of resident concerns in favor of tourist revenue appears to be 
a pattern. This represents a potential breach of his duty to represent constituents.

Next meeting scheduled for January 25, 2025.""",
        date=datetime(2025, 1, 9, 14, 0, 0),
        source="voice_memo",
    )
    print("✅ Sample transcript created\n")

    # Process the transcript
    print("3️⃣ Processing transcript (this may take a moment)...")
    result = processor.process_transcript(transcript)

    if result.success:
        print("✅ Processing completed successfully!\n")

        # Display results
        print("📊 Results:")
        print(f"   - Entities created: {len(result.created)}")
        print(f"   - Entities updated: {len(result.updated)}")
        print(f"   - Relationships created: {result.relationships_created}")
        print(f"   - Processing time: {result.processing_time:.2f} seconds")

        # Show created entities
        if result.created:
            print("\n📝 Created entities:")
            for page in result.created[:5]:  # Show first 5
                print(
                    f"   - {page.id}: {page.properties.get('Full Name') or page.properties.get('Organization Name') or 'Entity'}"
                )

        # Show any errors
        if result.errors:
            print("\n⚠️  Errors encountered:")
            for error in result.errors:
                print(f"   - {error.stage}: {error.message}")
    else:
        print("❌ Processing failed!")
        for error in result.errors:
            print(f"   - {error.error_type}: {error.message}")

    print("\n" + "=" * 50)
    print("💡 Next steps:")
    print("   1. Check your Notion workspace for the created entities")
    print("   2. Try processing your own transcripts")
    print("   3. Customize the configuration for your databases")
    print("   4. Run with --dry-run flag to preview without creating")


if __name__ == "__main__":
    main()
