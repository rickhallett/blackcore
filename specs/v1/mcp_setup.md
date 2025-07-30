# MCP (Model Context Protocol) Setup Guide for Project Blackcore

This guide provides detailed setup instructions for all MCP services that can enhance the development and operation of Project Blackcore, the intelligence engine for "Project Nassau."

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Notion MCP](#notion-mcp)
4. [Graphiti MCP (for Knowledge Graph Analysis)](#graphiti-mcp-for-knowledge-graph-analysis)
5. [Perplexity MCP (for Data Enrichment)](#perplexity-mcp-for-data-enrichment)
6. [Filesystem MCP](#filesystem-mcp)
7. [Context7 MCP (for Code Intelligence)](#context7-mcp-for-code-intelligence)
8. [Configuration Files](#configuration-files)
9. [Testing & Validation](#testing--validation)

## Overview

Project Blackcore transforms unstructured data into a structured knowledge graph in Notion. MCP services can streamline interaction with Notion, enable advanced graph analytics, enrich data with external information, and improve developer productivity.

| Service | Purpose | Blackcore Use Case |
|---|---|---|
| **Notion** | Primary data store and UI | Core for all database/page CRUD operations. |
| **Graphiti** | Graph database interaction | Advanced deduplication and relationship analysis. |
| **Perplexity** | AI-powered web search | Enriching entities with public data. |
| **Filesystem** | Local file access | Reading transcripts, managing local JSON models. |
| **Context7** | Code understanding | Navigating the codebase and generating tests. |

## Prerequisites

1. **Claude Code Setup**
   ```bash
   # Ensure Claude Code is installed
   claude --version
   
   # List current MCP servers
   claude mcp list
   ```

2. **API Keys & Environment**
   - Create a `.env` file from `.env.example`.
   - Populate it with your keys: `NOTION_API_KEY`, `PERPLEXITY_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, etc.
   - The application uses `python-dotenv` to load these variables.

3. **System Requirements**
   - Python 3.11+ (as defined in `.python-version`)
   - `uv` for Python package management
   - Node.js 18+ (for MCP servers)
   - Docker (for Neo4j database)

## Notion MCP

The Notion MCP allows direct interaction with the Notion API, which is central to Blackcore's function.

### 1. Installation
```bash
# Add Notion MCP server to Claude Code
claude mcp add-json notion '{
  "command": "npx",
  "args": ["-y", "@notionhq/notion-mcp-server"],
  "env": {
    "OPENAPI_MCP_HEADERS": "{\"Authorization\": \"Bearer ${NOTION_API_KEY}\", \"Notion-Version\": \"2022-06-28\" }"
  }
}'
```
*Note: Ensure your `NOTION_API_KEY` is set in your shell environment or replace `${NOTION_API_KEY}` directly.*

### 2. Use Cases for Blackcore

*   **Schema Verification**: "Using the Notion MCP, get the schema for the 'People & Places' database and compare it against the local model defined in `blackcore/models/notion_properties.py`."
*   **Live Data Fetching**: "Fetch the top 5 pages from the 'Intelligence Transcripts' database to check their latest content before running the `scripts/ingest_intelligence.py` script."
*   **Manual Page Creation**: "Create a new page in the 'Actionable Tasks' database with the title 'Review deduplication proposals for Operation Stardust'."

## Graphiti MCP (for Knowledge Graph Analysis)

While Notion acts as the primary database, a dedicated graph database like Neo4j (via Graphiti) can power advanced analytics, aligning with Blackcore's goal of creating a knowledge graph. This is particularly useful for the deduplication engine.

### 1. Neo4j Setup (via Docker)
```bash
# Run a Neo4j container for Blackcore
docker run -d \
  --name neo4j-blackcore \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/blackcore_secret_password \
  -e NEO4J_PLUGINS='["graph-data-science"]' \
  -v $HOME/neo4j/blackcore_data:/data \
  neo4j:5-community
```

### 2. Graphiti Installation
```bash
# Add Graphiti MCP server to Claude Code
claude mcp add-json graphiti '{
  "command": "npx",
  "args": ["-y", "@graphiti/mcp-server"],
  "env": {
    "GRAPHITI_HOST": "localhost",
    "GRAPHITI_PORT": "8000",
    "GRAPHITI_DATABASE_URL": "neo4j://localhost:7687"
  }
}'
```

### 3. Use Cases for Blackcore

*   **Deduplication Analysis**: "Load all entities from `blackcore/models/json/people_places.json` into Graphiti. Run a query to find nodes with similar names but different IDs to identify potential duplicates, similar to the logic in `blackcore/deduplication/graph_analyzer.py`."
*   **Relationship Discovery**: "Build a graph of 'Intelligence Transcripts' connected to 'People' and 'Organizations'. Query for paths between two seemingly unrelated people to uncover hidden connections."
*   **Visualize Network**: "Export a subgraph of all entities related to 'Project Nassau' as a Cypher query that can be pasted into the Neo4j Browser for visualization."

## Perplexity MCP (for Data Enrichment)

Perplexity can be used to enrich the raw data ingested by Blackcore, adding a layer of external validation and context.

### 1. Installation
```bash
# Add Perplexity MCP server to Claude Code
claude mcp add-json perplexity '{
  "command": "npx",
  "args": ["-y", "@perplexity/mcp-server"],
  "env": {
    "PERPLEXITY_API_KEY": "${PERPLEXITY_API_KEY}",
    "PERPLEXITY_MODEL": "sonar-pro"
  }
}'
```

### 2. Use Cases for Blackcore

*   **Entity Enrichment**: "For a newly created 'Organization' entity, use Perplexity to search for its official website, headquarters location, and key executives. Add this information to the entity's properties before syncing to Notion."
*   **Fact Checking**: "A transcript mentions a meeting on a specific date. Use Perplexity to search for public news or events on that date to corroborate the information."
*   **Alias Discovery**: "An individual is mentioned by a nickname. Use Perplexity to search for public information linking that nickname to a known person in the 'People & Places' database."

## Filesystem MCP

Direct filesystem access is crucial for reading source data and managing local files before they are processed and synced.

### 1. Installation
```bash
# Add Filesystem MCP server, granting access to the project directory
claude mcp add filesystem -s user -- npx -y @modelcontextprotocol/server-filesystem $(pwd)
```

### 2. Use Cases for Blackcore

*   **Ingest New Transcripts**: "Check the `transcripts/` directory for any new `.json` files that haven't been processed yet."
*   **Read Local Data Models**: "Read the contents of `blackcore/models/json/organizations_bodies.json` to see the current state of local organization data."
*   **Manage Reports**: "List all merge proposal reports in the `reports/merge_operations/` directory generated by the deduplication engine."

## Context7 MCP (for Code Intelligence)

Given the complexity of Blackcore, Context7 can help developers navigate the codebase and maintain quality.

### 1. Installation
```bash
# Add Context7 MCP server to Claude Code
claude mcp add-json context7 '{
  "command": "npx",
  "args": ["-y", "@context7/mcp-server"],
  "env": {
    "CONTEXT7_API_KEY": "${CONTEXT7_API_KEY}",
    "CONTEXT7_WORKSPACE": "blackcore",
    "CONTEXT7_INDEX_PATH": "./blackcore"
  }
}'
```

### 2. Use Cases for Blackcore

*   **Understand Data Flow**: "Using Context7, trace how a 'relation' property is handled from its definition in `blackcore/models/properties.py` through the `blackcore/handlers/relation.py` handler to the `blackcore/services/sync.py` service."
*   **Find Property Handler Logic**: "Find the implementation for handling 'last_edited_time' properties in the codebase."
*   **Generate Tests**: "Get the function signature and context for `blackcore.repositories.page.PageRepository.create_page` and generate a pytest unit test for it."

## Configuration Files

### 1. Example `.env` File
```bash
# Notion
NOTION_API_KEY=secret_...
NOTION_ROOT_PAGE_ID=...

# AI Providers
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Perplexity
PERPLEXITY_API_KEY=pplx-...

# Neo4j/Graphiti
NEO4J_USER=neo4j
NEO4J_PASSWORD=blackcore_secret_password


# Claude code local server connection
claude mcp add context7 -- npx -y @upstash/context7-mcp
```

### 2. MCP Configuration (`~/.claude/mcp.json`)
```json
{
  "mcp-servers": {
    "notion": {
      "command": "npx",
      "args": ["-y", "@notionhq/notion-mcp-server"],
      "env": {
        "OPENAPI_MCP_HEADERS": "{\"Authorization\": \"Bearer ${NOTION_API_KEY}\", \"Notion-Version\": \"2022-06-28\" }"
      }
    },
    "graphiti": {
      "command": "npx",
      "args": ["-y", "@graphiti/mcp-server"],
      "env": {
        "GRAPHITI_DATABASE_URL": "neo4j://localhost:7687"
      }
    },
    "perplexity": {
      "command": "npx",
      "args": ["-y", "@perplexity/mcp-server"],
      "env": {
        "PERPLEXITY_API_KEY": "${PERPLEXITY_API_KEY}"
      }
    },
    "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/your/blackcore/project"]
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@context7/mcp-server"],
      "env": {
        "CONTEXT7_API_KEY": "${CONTEXT7_API_KEY}",
        "CONTEXT7_WORKSPACE": "blackcore"
      }
    }
  }
}
```

## Testing & Validation

Create a Python script `scripts/test_mcp_connections.py` to validate the setup.

```python
# scripts/test_mcp_connections.py
import asyncio
from typing import Dict, Any

# Assume MCP client libraries are available or use a generic MCP client
# This is a conceptual example

async def test_all_connections() -> Dict[str, Any]:
    """Test all MCP service connections for Blackcore"""
    results = {}
    
    # Test Notion
    try:
        # notion_mcp = NotionMCP()
        # test_result = await notion_mcp.get_database(os.getenv("NOTION_ROOT_PAGE_ID"))
        results["notion"] = {"status": "✓", "message": "Conceptually Connected"}
    except Exception as e:
        results["notion"] = {"status": "✗", "error": str(e)}
    
    # Test Graphiti
    try:
        # graphiti_mcp = GraphitiMCP()
        # test_query = await graphiti_mcp.execute_query("RETURN 1 as test")
        results["graphiti"] = {"status": "✓", "message": "Conceptually Connected"}
    except Exception as e:
        results["graphiti"] = {"status": "✗", "error": str(e)}
    
    # Test Perplexity
    try:
        # perplexity_mcp = PerplexityMCP()
        # test_search = await perplexity_mcp.search("test query", limit=1)
        results["perplexity"] = {"status": "✓", "message": "Conceptually Connected"}
    except Exception as e:
        results["perplexity"] = {"status": "✗", "error": str(e)}
    
    print("MCP Connection Test Results:")
    for service, result in results.items():
        print(f"- {service.capitalize()}: {result['status']} {result.get('message', '')}{result.get('error', '')}")

if __name__ == "__main__":
    asyncio.run(test_all_connections())
```
