# Notion Sync Data Transformation Requirements

## Executive Summary

The production sync attempt on 2025-07-12 failed with 41 errors across 6 databases, resulting in 0 pages created out of 97 attempted. This specification document details all required changes to enable successful synchronization between local JSON files and Notion databases.

## Error Analysis

### 1. Property Type Mismatches

#### 1.1 Date Fields
**Issue**: Date fields expect ISO date format
**Affected Properties**:
- `Date of Transgression` (Identified Transgressions)
- `Date Recorded` (Intelligence & Transcripts)

**Current Format**: Various (e.g., "2024-06-26", "June 26th, 2024")
**Required Format**: ISO 8601 date (e.g., "2024-06-26")

#### 1.2 Select Fields
**Issue**: Select fields require valid option values that exist in Notion
**Affected Properties**:
- `Severity` (Identified Transgressions)
- `Document Type` (Documents & Evidence)
- `Source` (Intelligence & Transcripts)
- `Processing Status` (Intelligence & Transcripts)
- `Category` (Organizations & Bodies)
- `Phase` (Agendas & Epics)
- `Organization Type` (Organizations & Bodies)

**Example Error**: "Severity is expected to be select"
**Solution**: Query Notion to get valid options for each select field

#### 1.3 Status Fields
**Issue**: Status fields have special type requirements
**Affected Properties**:
- `Status` (Actionable Tasks)
- `Status` (Agendas & Epics)

**Example Error**: "Status is expected to be status"
**Solution**: Use Notion's status property format

#### 1.4 URL Fields
**Issue**: URL fields must contain valid URLs
**Affected Properties**:
- `Website` (Organizations & Bodies)

**Example Error**: "Website is expected to be url"
**Current Data**: Empty strings or invalid URLs
**Solution**: Validate URLs or omit if empty

#### 1.5 People Fields
**Issue**: People fields expect Notion user references
**Affected Properties**:
- `Owner` (Agendas & Epics)
- `Reported By` (Identified Transgressions)

**Example Error**: "Owner is expected to be people"
**Current Data**: Text names (e.g., "Pete Mitchell")
**Solution**: Convert to email addresses or omit

#### 1.6 Relation Fields
**Issue**: Relation fields expect page IDs, not text values
**Affected Properties**:
- `Perpetrator (Person)` (Identified Transgressions)
- `Perpetrator (Org)` (Identified Transgressions)
- `Evidence` (Identified Transgressions)
- `Source Organization` (Documents & Evidence)
- `Related Agenda` (Actionable Tasks)

**Example Error**: "Source Organization is expected to be relation"
**Current Data**: Text arrays (e.g., ["Tony Powell"])
**Solution**: Create pages first, then link by ID

### 2. Non-Existent Properties

#### 2.1 Properties That Don't Exist in Notion
**Affected Databases and Properties**:
- **Documents & Evidence**: `AI Analysis`, `Description`
- **Intelligence & Transcripts**: `Inferred`
- **Organizations & Bodies**: `Notes`, `Organization Type`
- **Agendas & Epics**: `Objective Summary`
- **Actionable Tasks**: `Assignee`, `Priority`, `Notes`, `Inferred`

**Solution**: Remove these properties from sync or add them to Notion

### 3. Content Length Limits

**Issue**: Rich text fields have a 2000 character limit
**Example**: "Raw Transcript/Note.rich_text[0].text.content.length should be ≤ 2000, instead was 65269"
**Solution**: Truncate or split long content

### 4. Data Structure Issues

#### 4.1 Mixed JSON Formats
Some JSON files have Notion API export format:
```json
{
  "Document Type": {
    "select": {
      "name": "Evidence"
    }
  }
}
```

Others have simple format:
```json
{
  "Document Type": "Evidence"
}
```

**Solution**: Standardize all to simple format before sync

#### 4.2 Missing JSON Files
- Looking for `people_contacts.json` but file is `people_places.json`
- Looking for `key_places_events.json` but file is `places_events.json`

**Solution**: Update configuration or rename files

## Implementation Plan

### Phase 1: Data Validation and Transformation

1. **Create Property Mapping Configuration**
   - Map JSON field names to Notion property names
   - Define type transformations for each field
   - Handle property exclusions

2. **Implement Type Transformers**
   - Date formatter (ensure ISO 8601)
   - URL validator
   - Text truncator (2000 char limit)
   - Select option validator
   - Relation placeholder handler

3. **Query Notion for Valid Options**
   - Get select field options for each database
   - Cache valid options for validation

### Phase 2: Staged Synchronization

Due to relation dependencies, sync must occur in stages:

1. **Stage 1**: Create all entities without relations
   - People & Contacts
   - Organizations & Bodies
   - Agendas & Epics

2. **Stage 2**: Create dependent entities
   - Documents & Evidence
   - Intelligence & Transcripts
   - Identified Transgressions
   - Actionable Tasks

3. **Stage 3**: Update all pages with relations
   - Link pages using IDs from Stage 1 & 2

### Phase 3: Property Schema Alignment

1. **Option A**: Update Notion Schemas
   - Add missing properties to Notion databases
   - Ensure all select fields have required options

2. **Option B**: Transform Data Only
   - Remove unsupported properties from JSON
   - Map to existing Notion properties only

## Specific Transformations Required

### 1. Identified Transgressions
```javascript
transform: {
  "Date of Transgression": (value) => ensureISODate(value),
  "Severity": (value) => validateSelectOption(value, ["Critical", "High", "Medium", "Low"]),
  "Perpetrator (Person)": (value) => [], // Stage 3: populate with page IDs
  "Perpetrator (Org)": (value) => [],    // Stage 3: populate with page IDs
  "Evidence": (value) => []              // Stage 3: populate with page IDs
}
```

### 2. Documents & Evidence
```javascript
transform: {
  "Document Type": (value) => extractSelectValue(value),
  "Source Organization": (value) => [], // Stage 3: populate with page IDs
  // Remove: "AI Analysis", "Description"
}
```

### 3. Intelligence & Transcripts
```javascript
transform: {
  "Date Recorded": (value) => ensureISODate(value),
  "Source": (value) => validateSelectOption(value, validSources),
  "Processing Status": (value) => validateSelectOption(value, validStatuses),
  "Raw Transcript/Note": (value) => truncateText(value, 2000),
  // Remove: "Inferred"
}
```

### 4. Organizations & Bodies
```javascript
transform: {
  "Category": (value) => validateSelectOption(value, validCategories),
  "Website": (value) => validateURL(value) || "",
  // Remove: "Notes", "Organization Type"
}
```

### 5. Agendas & Epics
```javascript
transform: {
  "Phase": (value) => validateSelectOption(value, validPhases),
  "Owner": (value) => null, // Cannot set people field programmatically
  // Remove: "Objective Summary"
}
```

### 6. Actionable Tasks
```javascript
transform: {
  "Status": (value) => validateStatus(value, validStatuses),
  "Related Agenda": (value) => [], // Stage 3: populate with page IDs
  // Remove: "Assignee", "Priority", "Notes", "Inferred"
}
```

## Testing Strategy

1. **Dry Run with Transformations**
   - Apply all transformations
   - Validate against Notion requirements
   - Log all changes

2. **Staged Test Sync**
   - Sync 1 record per database
   - Verify creation success
   - Test relation linking

3. **Full Production Sync**
   - Execute staged sync plan
   - Monitor and log all operations
   - Validate final state

## Success Metrics

- 0 type mismatch errors
- 0 non-existent property errors
- 97 pages successfully created
- All relations properly linked
- Complete audit trail of all operations

## Next Steps

1. Implement data transformation layer
2. Create property mapping configuration
3. Update sync script to use transformations
4. Execute dry run to validate
5. Perform production sync with monitoring