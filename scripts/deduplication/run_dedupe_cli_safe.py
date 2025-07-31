Purpose: A safe launcher for the deduplication CLI. It checks for the presence of necessary environment variables (like AI API keys) before running the main CLI script.
Utility: Prevents the CLI from failing unexpectedly due to a misconfigured environment. It provides helpful feedback to the user, improving usability and reducing frustration.
"""
#!/usr/bin/env python3
"""
Safe launcher for the deduplication CLI that checks environment first.
"""

import os
import sys
import subprocess
from pathlib import Path


def check_environment():
    """Check if the environment is properly configured."""
    print("🔍 Checking environment...")

    # Check API keys
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    openai_key = os.getenv("OPENAI_API_KEY", "")

    has_valid_anthropic = bool(
        anthropic_key and anthropic_key != "your_key_here" and len(anthropic_key) > 20
    )
    has_valid_openai = bool(
        openai_key and openai_key != "your_key_here" and len(openai_key) > 20
    )

    if has_valid_anthropic:
        print("✅ Anthropic API key found")
    else:
        print("⚠️  No valid Anthropic API key found")

    if has_valid_openai:
        print("✅ OpenAI API key found")
    else:
        print("⚠️  No valid OpenAI API key found")

    if not has_valid_anthropic and not has_valid_openai:
        print("\n📌 AI analysis will be disabled (no valid API keys)")
        print("   The deduplication will still work using fuzzy matching.")

    return True


def main():
    """Launch the CLI with environment check."""
    print("=" * 60)
    print("Blackcore Deduplication CLI Launcher")
    print("=" * 60)
    print()

    # Check environment
    if not check_environment():
        return 1

    print("\n🚀 Launching deduplication CLI...")
    print("-" * 60)
    print()

    # Change to the blackcore directory
    os.chdir(Path(__file__).parent.parent)

    # Run the CLI
    try:
        subprocess.run([sys.executable, "scripts/dedupe_cli.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ CLI exited with error code: {e.returncode}")
        return e.returncode
    except KeyboardInterrupt:
        print("\n\n👋 Exiting...")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
