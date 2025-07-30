# Blackcore Simple Syncer - Quick Start Guide

A fast, simple command-line tool that processes meeting transcripts and notes, automatically extracts key information (people, organizations, tasks), identifies duplicates, and syncs everything to your Notion workspace.

## 15-Minute Setup

### 1. Prerequisites

- Python 3.11 or higher
- A Notion workspace with integration access
- An AI API key (Claude or OpenAI)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/your-org/blackcore.git
cd blackcore

# Install dependencies
pip install -e .
# or
pip install notion-client anthropic  # For Claude
# or  
pip install notion-client openai     # For OpenAI
```

### 3. Configuration

Set up your environment variables:

```bash
# Required - Get from notion.so/my-integrations
export NOTION_API_KEY="secret_..."

# Required - Choose one AI provider
export ANTHROPIC_API_KEY="sk-ant-..."  # For Claude (recommended)
# OR
export OPENAI_API_KEY="sk-..."         # For OpenAI

# Required - Your Notion database IDs (from database URLs)
export NOTION_DB_PEOPLE_ID="..."
export NOTION_DB_ORGANIZATIONS_ID="..."
export NOTION_DB_TASKS_ID="..."
export NOTION_DB_TRANSCRIPTS_ID="..."
```

### 4. Process Your First Transcript

```bash
# Process a single transcript
python -m blackcore.minimal sync-transcript meeting-notes.txt

# Preview without making changes
python -m blackcore.minimal sync-transcript meeting-notes.txt --dry-run

# Process with detailed output
python -m blackcore.minimal sync-transcript meeting-notes.txt --verbose
```

## What It Does

1. **Reads** your transcript file (text or JSON)
2. **Extracts** entities using AI:
   - People (with roles, emails, organizations)
   - Organizations (with categories, websites)
   - Tasks (with assignees, due dates)
   - Issues/Transgressions
3. **Deduplicates** automatically:
   - "Tony Smith" → finds existing "Anthony Smith" 
   - "Nassau Council Inc" → matches "Nassau Council"
   - Uses email/phone for high-confidence matching
4. **Syncs** to Notion:
   - Updates existing records with new information
   - Creates new pages only when needed
   - Links everything together

## Example Output

```
Processing transcript: meeting-notes.txt
🔍 DRY RUN MODE - No changes will be made to Notion

Extracting entities from 'Meeting with Mayor'...
  Found duplicate: 'Tony Smith' matches existing entity (score: 95.0, reason: email match)
  Found duplicate: 'Nassau Council' matches existing entity (score: 95.0, reason: normalized name match)

Processing complete in 12.3s:
  Created: 3 entities
  Updated: 2 entities
  Relationships: 0
```

## File Formats

### Text Files
Just paste your meeting notes or transcript:
```
Meeting with Tony Smith from Nassau Council about beach permits.
Action: Tony to review permit applications by Friday.
Issue: Unauthorized beach hut construction at North Beach.
```

### JSON Files
For structured input:
```json
{
  "title": "Council Meeting 2024-01-15",
  "content": "Meeting transcript...",
  "date": "2024-01-15",
  "source": "google_meet"
}
```

## Deduplication Examples

The tool automatically identifies these as the same person:
- "Tony Smith" = "Anthony Smith" (nickname detection)
- "Dr. Jane Doe" = "Jane Doe" (title removal)
- "john.smith@email.com" = "j.smith@email.com" (email match)

And these as the same organization:
- "Nassau Council Inc." = "Nassau Council" (suffix removal)
- "NASA" = "National Aeronautics and Space Administration" (acronym matching)

## Performance

- **1,000-word transcript**: ~15-20 seconds
- **10,000-word document**: ~30-40 seconds
- Caches results to avoid duplicate AI calls

## Troubleshooting

**"API key not configured"**
- Ensure environment variables are set
- Check spelling of variable names

**"Database ID not found"**
- Copy the ID from your Notion database URL
- Format: 32 characters, no hyphens needed

**"No duplicates found"**
- The deduplication threshold is 90% by default
- Check existing records have matching fields (email, phone)

## Advanced Usage

### Batch Processing
```bash
python -m blackcore.minimal process-batch ./transcripts/
```

### Custom Configuration
Create a `config.json`:
```json
{
  "processing": {
    "enable_deduplication": true,
    "deduplication_threshold": 85.0
  }
}
```

Then use:
```bash
python -m blackcore.minimal sync-transcript transcript.txt -c config.json
```

## Need Help?

- Check existing entries in your Notion databases
- Run with `--verbose` for detailed output
- Use `--dry-run` to preview changes
- Ensure your databases have the expected properties (Full Name, Email, etc.)

## Next Steps

1. Process your backlog of transcripts
2. Set up a daily routine for new notes
3. Review Notion for newly discovered connections
4. Customize database properties as needed

---

**Version**: MVP 1.0  
**License**: MIT