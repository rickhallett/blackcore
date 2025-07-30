# Notion Sync Quick Fixes Guide

## Immediate Issues to Fix

### 1. Property Names Don't Match
**JSON has** → **Notion expects**
- `Organization Type` → `Category`
- `AI Analysis` → (doesn't exist - remove)
- `Description` → (doesn't exist - remove)
- `Notes` → (doesn't exist - remove)
- `Objective Summary` → (doesn't exist - remove)
- `Assignee` → (doesn't exist - remove)
- `Priority` → (doesn't exist - remove)
- `Inferred` → (doesn't exist - remove)

### 2. Data Types Are Wrong

#### Dates (must be ISO format: "2024-06-26")
- ✅ Current: "2024-06-26"
- ❌ Current: "June 26th, 2024"

#### Select Fields (must match Notion options exactly)
- Need to query Notion for valid options
- Examples: "Critical" for Severity, "Evidence" for Document Type

#### Relations (need page IDs, not text)
- ❌ Current: `["Tony Powell", "Sarah Streams"]`
- ✅ Need: `["page-id-123", "page-id-456"]`

#### URLs (must be valid)
- ❌ Current: `""`
- ✅ Need: `"https://example.com"` or omit field

#### Status (special Notion type)
- Different from regular select fields
- Has specific status values

### 3. Content Too Long
- Rich text fields max 2000 characters
- One transcript is 65,269 characters!
- Need to truncate or split

### 4. Mixed JSON Formats
Some files have Notion export format:
```json
{
  "Document Type": {
    "select": {
      "name": "Evidence"
    }
  }
}
```

Need simple format:
```json
{
  "Document Type": "Evidence"
}
```

### 5. Wrong File Names
- Config looks for `people_contacts.json` → actual file is `people_places.json`
- Config looks for `key_places_events.json` → actual file is `places_events.json`

## Quick Fix Order

1. **First**: Create pages without relations
   - People, Organizations, Agendas

2. **Second**: Create dependent pages
   - Documents, Transcripts, Tasks, Transgressions

3. **Third**: Update all pages with relations
   - Link using page IDs from steps 1 & 2

## Sample Fixes

### Fix Date
```python
# Before
"Date Recorded": "June 2024"
# After  
"Date Recorded": "2024-06-01"
```

### Fix Select
```python
# Before
"Severity": "Critical"
# After (verify option exists first)
"Severity": "Critical"
```

### Fix Relation
```python
# Before
"Perpetrator (Person)": ["Tony Powell"]
# After (use actual page ID)
"Perpetrator (Person)": ["21f4753d-608e-8173-b6dc-fc6302804e69"]
```

### Remove Invalid Properties
```python
# Before
{
  "Task Name": "Submit complaint",
  "Status": "Active",
  "Priority": "High",  # ← Remove this
  "Notes": "Important"  # ← Remove this
}
# After
{
  "Task Name": "Submit complaint",
  "Status": "Active"
}
```