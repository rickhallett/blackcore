# MCP (Model Context Protocol) Setup Guide for LinkybBotty

This guide provides detailed setup instructions for all MCP services required by the LinkedIn Easy Apply automation bot.

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Bright Data MCP](#bright-data-mcp)
4. [Graphiti MCP](#graphiti-mcp)
5. [MindsDB MCP](#mindsdb-mcp)
6. [Perplexity MCP](#perplexity-mcp)
7. [Context7 MCP](#context7-mcp)
8. [Configuration Files](#configuration-files)
9. [Testing & Validation](#testing--validation)

## Overview

LinkybBotty utilizes five MCP services for different functionalities:

| Service | Purpose | Required for |
|---------|---------|--------------|
| **Bright Data** | LinkedIn job scraping with proxy rotation | Job discovery |
| **Graphiti** | Graph-based data storage and analytics | Application tracking |
| **MindsDB** | Gmail integration for response monitoring | Email tracking |
| **Perplexity** | AI-powered search and research | Job matching & analysis |
| **Context7** | Code understanding and documentation | Development assistance |

## Prerequisites

1. **Claude Code Setup**
   ```bash
   # Ensure Claude Code is installed
   claude --version
   
   # List current MCP servers
   claude mcp list
   ```

2. **API Keys Required**
   - Bright Data API token
   - MindsDB connection credentials
   - Perplexity Pro API key
   - Context7 API key (if applicable)

3. **System Requirements**
   - Node.js 18+ (for MCP servers)
   - Python 3.11+ (for project)
   - Docker (optional, for containerized services)

## Bright Data MCP

### 1. Installation
```bash
# Install Bright Data MCP server
npx -y @brightdata/mcp-server

# Or add to Claude Code configuration
claude mcp add-json bright-data '{
  "command": "npx",
  "args": ["-y", "@brightdata/mcp-server"],
  "env": {
    "BRIGHT_DATA_API_TOKEN": "your-api-token-here",
    "WEB_UNLOCKER_ZONE": "mcp_unlocker"
  }
}'
```

### 2. Configuration
Create `~/.brightdata/config.json`:
```json
{
  "api_token": "your-api-token",
  "zones": {
    "web_unlocker": {
      "zone_id": "mcp_unlocker",
      "proxy_type": "datacenter",
      "country": "US"
    }
  },
  "rate_limits": {
    "linkedin": "100/1h",
    "default": "1000/1h"
  }
}
```

### 3. Environment Variables
```bash
# Add to .env
BRIGHT_DATA_API_TOKEN=your-api-token
BRIGHT_DATA_RATE_LIMIT=100/1h
WEB_UNLOCKER_ZONE=mcp_unlocker
```

### 4. Usage Example
```python
# bright_data_test.py
from mcp import BrightDataMCP

async def test_bright_data():
    client = BrightDataMCP()
    
    # Test LinkedIn job search
    jobs = await client.search_jobs(
        query="python developer",
        location="Remote",
        easy_apply_only=True,
        limit=10
    )
    print(f"Found {len(jobs)} jobs")
```

## Graphiti MCP

### 1. Installation
```bash
# Install Graphiti MCP server
npx -y @graphiti/mcp-server

# Or add to Claude Code
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

### 2. Neo4j Setup (if using local)
```bash
# Using Docker
docker run -d \
  --name neo4j-linkybotty \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/linkybotty123 \
  -e NEO4J_PLUGINS='["graph-data-science"]' \
  -v $HOME/neo4j/data:/data \
  neo4j:5-community
```

### 3. Configuration
```python
# graphiti_config.py
GRAPHITI_CONFIG = {
    "host": "localhost",
    "port": 8000,
    "neo4j": {
        "uri": "neo4j://localhost:7687",
        "user": "neo4j",
        "password": "linkybotty123"
    },
    "schema": {
        "entities": ["Job", "Company", "Application", "Skill"],
        "relationships": ["APPLIED_TO", "POSTED_BY", "REQUIRES", "HAS_SKILL"]
    }
}
```

### 4. Initialize Schema
```python
# init_graphiti.py
async def initialize_graphiti():
    graphiti = GraphitiMCP()
    
    # Create constraints and indexes
    await graphiti.execute_query("""
        CREATE CONSTRAINT job_id IF NOT EXISTS
        FOR (j:Job) REQUIRE j.id IS UNIQUE
    """)
    
    await graphiti.execute_query("""
        CREATE INDEX job_title IF NOT EXISTS
        FOR (j:Job) ON (j.title)
    """)
```

## MindsDB MCP

### 1. Installation
```bash
# Install MindsDB MCP server
npx -y @mindsdb/mcp-server

# Or add to Claude Code
claude mcp add-json mindsdb '{
  "command": "npx",
  "args": ["-y", "@mindsdb/mcp-server"],
  "env": {
    "MINDSDB_HOST": "localhost",
    "MINDSDB_PORT": "47334",
    "MINDSDB_USERNAME": "mindsdb",
    "MINDSDB_PASSWORD": "your-password"
  }
}'
```

### 2. Gmail Integration Setup
```sql
-- Create Gmail database in MindsDB
CREATE DATABASE gmail_db
WITH ENGINE = 'gmail',
PARAMETERS = {
  "credentials_file": "/path/to/gmail-credentials.json"
};

-- Create job responses view
CREATE VIEW job_responses AS
SELECT 
  id,
  subject,
  sender,
  body,
  received_date,
  labels
FROM gmail_db.messages
WHERE 
  labels LIKE '%job%' OR
  subject REGEXP 'application|interview|offer|rejection';
```

### 3. Configuration
```python
# mindsdb_config.py
MINDSDB_CONFIG = {
    "host": "localhost",
    "port": 47334,
    "database": "gmail_db",
    "auth": {
        "username": "mindsdb",
        "password": os.getenv("MINDSDB_PASSWORD")
    }
}
```

## Perplexity MCP

### 1. Installation
```bash
# Install Perplexity MCP server
npx -y @perplexity/mcp-server

# Or add to Claude Code
claude mcp add-json perplexity '{
  "command": "npx",
  "args": ["-y", "@perplexity/mcp-server"],
  "env": {
    "PERPLEXITY_API_KEY": "pplx-your-api-key",
    "PERPLEXITY_MODEL": "sonar-pro",
    "PERPLEXITY_SEARCH_DOMAINS": "linkedin.com,indeed.com,glassdoor.com"
  }
}'
```

### 2. Configuration
```python
# perplexity_config.py
PERPLEXITY_CONFIG = {
    "api_key": os.getenv("PERPLEXITY_API_KEY"),
    "model": "sonar-pro",  # Pro subscription model
    "search_settings": {
        "domains": ["linkedin.com", "indeed.com", "glassdoor.com"],
        "recency": "week",  # Focus on recent job postings
        "search_type": "professional"
    }
}
```

### 3. Usage for Job Analysis
```python
# perplexity_job_analyzer.py
class JobAnalyzer:
    def __init__(self):
        self.perplexity = PerplexityMCP()
    
    async def analyze_company(self, company_name: str):
        """Research company using Perplexity Pro"""
        query = f"""
        Research {company_name}:
        - Recent hiring trends
        - Company culture and values
        - Technology stack
        - Recent news or layoffs
        - Interview process
        """
        
        return await self.perplexity.search(
            query=query,
            search_domains=["linkedin.com", "glassdoor.com"],
            pro_mode=True
        )
    
    async def match_skills(self, job_description: str, user_skills: List[str]):
        """Use Perplexity to analyze skill matching"""
        query = f"""
        Analyze job requirements and match with candidate skills:
        
        Job Description: {job_description[:500]}
        
        Candidate Skills: {', '.join(user_skills)}
        
        Provide:
        1. Skill match percentage
        2. Missing critical skills
        3. Transferable skills that apply
        """
        
        return await self.perplexity.complete(query)
```

## Context7 MCP

### 1. Installation
```bash
# Install Context7 MCP server
npx -y @context7/mcp-server

# Or add to Claude Code
claude mcp add-json context7 '{
  "command": "npx",
  "args": ["-y", "@context7/mcp-server"],
  "env": {
    "CONTEXT7_API_KEY": "your-api-key",
    "CONTEXT7_WORKSPACE": "linkybotty",
    "CONTEXT7_INDEX_PATH": "./src"
  }
}'
```

### 2. Configuration
```python
# context7_config.py
CONTEXT7_CONFIG = {
    "api_key": os.getenv("CONTEXT7_API_KEY"),
    "workspace": "linkybotty",
    "index_settings": {
        "paths": ["./src", "./tests"],
        "file_types": [".py", ".md", ".json"],
        "ignore_patterns": ["*.pyc", "__pycache__", ".venv"]
    }
}
```

### 3. Usage for Code Understanding
```python
# context7_helper.py
class CodeAssistant:
    def __init__(self):
        self.context7 = Context7MCP()
    
    async def find_implementation(self, feature: str):
        """Find where a feature is implemented"""
        return await self.context7.search_code(
            query=f"implementation of {feature}",
            file_types=[".py"],
            semantic=True
        )
    
    async def generate_tests(self, function_name: str):
        """Generate test cases for a function"""
        context = await self.context7.get_function_context(function_name)
        return await self.context7.generate(
            prompt=f"Generate pytest test cases for: {context}",
            context_aware=True
        )
```

## Configuration Files

### 1. Complete `.env` File
```bash
# Bright Data
BRIGHT_DATA_API_TOKEN=your-bright-data-token
BRIGHT_DATA_RATE_LIMIT=100/1h
WEB_UNLOCKER_ZONE=mcp_unlocker

# Graphiti
GRAPHITI_HOST=localhost
GRAPHITI_PORT=8000
NEO4J_URI=neo4j://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=linkybotty123

# MindsDB
MINDSDB_HOST=localhost
MINDSDB_PORT=47334
MINDSDB_USERNAME=mindsdb
MINDSDB_PASSWORD=your-mindsdb-password

# Perplexity
PERPLEXITY_API_KEY=pplx-your-api-key
PERPLEXITY_MODEL=sonar-pro

# Context7
CONTEXT7_API_KEY=your-context7-key
CONTEXT7_WORKSPACE=linkybotty

# Application settings
STATIC_EMAIL=your-email@gmail.com
DAILY_APPLICATION_LIMIT=50
```

### 2. MCP Configuration (`~/.claude/mcp.json`)
```json
{
  "servers": {
    "bright-data": {
      "command": "npx",
      "args": ["-y", "@brightdata/mcp-server"],
      "env": {
        "BRIGHT_DATA_API_TOKEN": "${BRIGHT_DATA_API_TOKEN}"
      }
    },
    "graphiti": {
      "command": "npx",
      "args": ["-y", "@graphiti/mcp-server"],
      "env": {
        "GRAPHITI_HOST": "localhost",
        "GRAPHITI_PORT": "8000"
      }
    },
    "mindsdb": {
      "command": "npx",
      "args": ["-y", "@mindsdb/mcp-server"],
      "env": {
        "MINDSDB_HOST": "localhost",
        "MINDSDB_PORT": "47334"
      }
    },
    "perplexity": {
      "command": "npx",
      "args": ["-y", "@perplexity/mcp-server"],
      "env": {
        "PERPLEXITY_API_KEY": "${PERPLEXITY_API_KEY}"
      }
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@context7/mcp-server"],
      "env": {
        "CONTEXT7_API_KEY": "${CONTEXT7_API_KEY}"
      }
    }
  }
}
```

## Testing & Validation

### 1. Test All MCP Connections
```python
# test_mcp_connections.py
import asyncio
from typing import Dict, Any

async def test_all_connections() -> Dict[str, Any]:
    """Test all MCP service connections"""
    results = {}
    
    # Test Bright Data
    try:
        bright_data = BrightDataMCP()
        test_search = await bright_data.search_jobs("test", limit=1)
        results["bright_data"] = {"status": "✓", "message": "Connected"}
    except Exception as e:
        results["bright_data"] = {"status": "✗", "error": str(e)}
    
    # Test Graphiti
    try:
        graphiti = GraphitiMCP()
        test_query = await graphiti.execute_query("RETURN 1 as test")
        results["graphiti"] = {"status": "✓", "message": "Connected"}
    except Exception as e:
        results["graphiti"] = {"status": "✗", "error": str(e)}
    
    # Test MindsDB
    try:
        mindsdb = MindsDBMCP()
        test_query = await mindsdb.query("SHOW DATABASES")
        results["mindsdb"] = {"status": "✓", "message": "Connected"}
    except Exception as e:
        results["mindsdb"] = {"status": "✗", "error": str(e)}
    
    # Test Perplexity
    try:
        perplexity = PerplexityMCP()
        test_search = await perplexity.search("test query", limit=1)
        results["perplexity"] = {"status": "✓", "message": "Connected"}
    except Exception as e:
        results["perplexity"] = {"status": "✗", "error": str(e)}
    
    # Test Context7
    try:
        context7 = Context7MCP()
        test_search = await context7.search_code("test", limit=1)
        results["context7"] = {"status": "✓", "message": "Connected"}
    except Exception as e:
        results["context7"] = {"status": "✗", "error": str(e)}
    
    return results

# Run tests
if __name__ == "__main__":
    results = asyncio.run(test_all_connections())
    for service, result in results.items():
        print(f"{service}: {result}")
```

### 2. Integration Test
```python
# test_integration.py
async def test_full_pipeline():
    """Test the complete MCP integration pipeline"""
    
    # 1. Search for a job using Bright Data
    jobs = await bright_data.search_jobs("Python Developer", limit=1)
    assert jobs, "No jobs found"
    
    # 2. Research company using Perplexity
    company_info = await perplexity.analyze_company(jobs[0].company)
    assert company_info, "No company info found"
    
    # 3. Store in Graphiti
    await graphiti.create_job_node(jobs[0])
    
    # 4. Check email responses via MindsDB
    responses = await mindsdb.check_job_responses()
    
    # 5. Use Context7 to understand codebase
    implementation = await context7.find_implementation("job application")
    
    print("✓ All MCP services integrated successfully")
```

## Troubleshooting

### Common Issues

1. **Bright Data Connection Issues**
   - Verify API token is valid
   - Check rate limits haven't been exceeded
   - Ensure proxy zones are configured correctly

2. **Graphiti/Neo4j Issues**
   - Verify Neo4j is running: `docker ps | grep neo4j`
   - Check Neo4j logs: `docker logs neo4j-linkybotty`
   - Ensure schema is initialized

3. **MindsDB Gmail Issues**
   - Verify Gmail API credentials are valid
   - Check OAuth scopes include email read access
   - Ensure MindsDB server is running

4. **Perplexity Rate Limits**
   - Pro subscription allows higher limits
   - Implement exponential backoff for rate limit errors
   - Cache results to minimize API calls

5. **Context7 Indexing Issues**
   - Ensure workspace path is correct
   - Check file permissions
   - Verify API key has proper access

### Debug Commands
```bash
# Check MCP server logs
claude mcp logs bright-data
claude mcp logs graphiti

# Restart specific MCP server
claude mcp restart perplexity

# Check all MCP statuses
claude mcp status
```

## Security Best Practices

1. **Never commit API keys** - Use environment variables
2. **Rotate credentials regularly** - Especially for production
3. **Use separate environments** - Dev/staging/production
4. **Implement rate limiting** - Prevent API abuse
5. **Monitor usage** - Set up alerts for unusual activity
6. **Encrypt sensitive data** - Use cryptography library for storage

## Next Steps

1. Run the connection tests to verify all services
2. Initialize the Graphiti schema
3. Set up Gmail integration in MindsDB
4. Configure Perplexity search domains for job sites
5. Index the codebase with Context7
6. Begin implementing the application pipeline

For additional support, refer to:
- [Bright Data Documentation](https://docs.brightdata.com)
- [Graphiti MCP Docs](https://graphiti.dev/mcp)
- [MindsDB Documentation](https://docs.mindsdb.com)
- [Perplexity API Docs](https://docs.perplexity.ai)
- [Context7 Documentation](https://context7.ai/docs)