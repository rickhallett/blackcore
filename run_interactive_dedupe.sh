#!/bin/bash
# Interactive deduplication CLI launcher

echo "=============================================="
echo "Blackcore Interactive Deduplication CLI"
echo "=============================================="
echo ""
echo "This will launch the interactive CLI where you can:"
echo "  1. Select databases to analyze"
echo "  2. Configure thresholds"
echo "  3. Run analysis with AI (if API keys are set)"
echo "  4. Review and approve/reject matches"
echo ""
echo "The system is in SAFETY MODE by default."
echo "No changes will be made without explicit approval."
echo ""
echo "Press Enter to continue..."
read

# Change to the blackcore directory
cd "$(dirname "$0")"

# Run the CLI
python scripts/dedupe_cli.py