# Project Bootstrap Prime
> A comprehensive project initialization and bootstrapping command.
> Follow each step in order. Use liberal comments to explain what each step achieves.

## 1. Git Repository Initialization
```bash
# Initialize git repository if not already initialized
git init

# Create initial empty commit with message "Initial commit"
git commit --allow-empty -m "Initial commit"
```

## 2. Chose Node version
```bash
# Choose Node version
nvm use 21
```

## 3. Bun Project Setup
```bash
# Create new bun project with TypeScript support
bun init -y

# Add task-master-ai package using bun
bun add task-master-ai

# Add development dependencies
bun add -D @types/node
```

## 4. Task Master Initialization
```bash
# Initialize task-master in the project
# This creates .task-master directory and configuration
bunx task-master init

# Configure API keys in .env file
# get keys from printenv
printenv | grep 'ANTHROPIC_API_KEY=' >> .env
printenv | grep 'OPENAI_API_KEY=' >> .env
printenv | grep 'GOOGLE_API_KEY=' >> .env
printenv | grep 'PERPLEXITY_API_KEY=' >> .env
echo "MODEL=claude-sonnet-4-20250514" >> .env
echo "PERPLEXITY_MODEL=sonar-pro" >> .env
```

## 5. Python Environment Setup with UV
```bash
# Initialize Python project with UV
# get project name folder name
uv init --name "$(basename "$PWD")"

# Pin Python version for consistency
uv python pin 3.11

# Create virtual environment (automatically done by uv)
# Add essential AI packages
uv add anthropic openai google-generativeai rich notion-client pypdf beautifulsoup4 pydantic httpx python-dotenv 

# Add development tools
uv add --dev ruff pytest pytest-asyncio ipython
```

## 6. Read AI Documentation & Best Practices
> Read and understand Claude Code's programmable capabilities

### PARALLEL READ the following:
- Claude Code tutorials for extended thinking workflows
- Claude Code best practices for programmability
- Examples of runtime script execution
- Custom slash command documentation
- MCP (Model Context Protocol) integration guides

Add summary of the information to the CLAUDE.md file

### PARALLEL READ the following:
- .roo/rules/dev_workflow.md
- .roo/rules/taskmaster.md

Add summary of the information to the CLAUDE.md file

### Key Concepts to Extract:
1. **Extended Thinking**: Using "think" commands for complex reasoning
2. **Piping**: `cat error.txt | claude -p 'explain'`
3. **Custom Commands**: Project-specific `.claude/commands/`
4. **MCP Servers**: Connecting to external tools and databases


## 8. Create Developer Workflow Commands

### Create commit-all command
```bash
mkdir -p .claude/commands
cat > .claude/commands/commit-all.md << 'EOF'
# Commit All Changes
> Systematically review and commit all staged changes
> Check with human before committing changes

## Steps:
1. Show current git status
2. Review all changes with git diff
3. Create detailed commit message covering all changes
4. Commit with comprehensive message

```bash
git status
git diff --staged
# Analyze changes and create detailed commit message
git commit -m "Comprehensive commit message here"
```
EOF
```

### Create review-staging command
```bash
cat > .claude/commands/review-staging.md << 'EOF'
# Review Staging Area
> Thoroughly review all changes in git staging area
> Develop plan before reviewing staging area
> Check with human before reviewing staging area

## Review Process:
```bash
# Show overview of staged files
git status -s

# Review each staged file's changes
git diff --staged --name-only | while read file; do
    echo "=== Changes in $file ==="
    git diff --staged "$file"
done

# Summary of changes by type
git diff --staged --stat
```
EOF
```

### Create next-todo command
```bash
cat > .claude/commands/next-todo.md << 'EOF'
# Execute Next Todo
> Execute the next task from task-master todo list
> Develop plan (if not already present) before executing next task
> Check with human before executing next task

## Workflow:
```bash
# Show current task list
task-master list

# Get next task with AI analysis
task-master next

# Mark task as in progress
task-master update <task-id> --status "In Progress"

# Execute the task
# ... implementation ...

# Mark task as complete
task-master update <task-id> --status "Complete"
```
EOF
```

## 9. Advanced Workflow Commands

### Create think-harder command
```bash
cat > .claude/commands/think-harder.md << 'EOF'
# Deep Thinking Mode
> Engage extended thinking for complex problems
> Develop plan after thinking
> Check with human after thinking

Use this when facing:
- Architectural decisions
- Complex algorithm design
- Performance optimization
- Security considerations

Invoke with varying intensity:
- "think" - Basic reasoning
- "think harder" - Deeper analysis
- "think more" - Extended consideration
EOF
```

```bash
#!/bin/bash
echo "🚀 Installing Claude Code MCP Servers..."

# Core Thinking & Memory
claude mcp add sequential-thinking -s user -- npx -y @modelcontextprotocol/server-sequential-thinking
claude mcp add knowledge-graph-memory -s user -- npx -y @modelcontextprotocol/server-memory
claude mcp add memory-bank -s user -e MEMORY_BANK_ROOT=~/memory-bank -- npx -y @allpepper/memory-bank-mcp

# Browser Automation
claude mcp add puppeteer -s user -- npx -y @modelcontextprotocol/server-puppeteer
claude mcp add playwright -s user -- npx @playwright/mcp@latest

# Development Tools
claude mcp add github -s user -- npx -y @modelcontextprotocol/server-github
claude mcp add desktop-commander -s user -- npx -y @wonderwhy-er/desktop-commander

# Search & Discovery
claude mcp add duckduckgo -s user -- npx -y duckduckgo-mcp-server
claude mcp add mcp-compass -s user -- npx -y mcp-compass

# Database & Backend
# claude mcp add supabase -s user -e SUPABASE_ACCESS_TOKEN=$SUPABASE_ACCESS_TOKEN -- npx -y @supabase/mcp-server-supabase@latest

# Filesystem (Essential)
claude mcp add filesystem -s user -- npx -y @modelcontextprotocol/server-filesystem ~/Documents ~/Desktop ~/Downloads ~/Projects

echo "✅ Installation complete! Use 'claude mcp list' to verify."
```

{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "GITHUB_PERSONAL_ACCESS_TOKEN",
        "ghcr.io/github/github-mcp-server"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<YOUR_TOKEN>"
      }
    }
  }
}

### Create mcp-connect command (check to see if MCPs are installed before adding locally; they may be available globally already)
```bash
cat > .claude/commands/mcp-connect.md << 'EOF'
# MCP Server Connection
> Connect to external tools via Model Context Protocol

## Available Servers:
- filesystem: Access to specified directories
- github: Repository management
- notion: Notion integration
- task-master: Task Master integration

## Setup:
```bash
# Add MCP server (example for filesystem)
claude mcp add-json filesystem '{
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]
}'

# Add MCP server for notion
{
  "mcpServers": {
    "notionApi": {
      "command": "npx",
      "args": ["-y", "@notionhq/notion-mcp-server"],
      "env": {
        "OPENAPI_MCP_HEADERS": "{\"Authorization\": \"Bearer ntn_****\", \"Notion-Version\": \"2022-06-28\" }"
      }
    }
  }
}

# Add Task Master MCP server
{
  "mcpServers": {
    "taskmaster-ai": {
      "command": "npx",
      "args": ["-y", "--package=task-master-ai", "task-master-ai"],
      "env": {
        "ANTHROPIC_API_KEY": "YOUR_ANTHROPIC_API_KEY_HERE",
        "PERPLEXITY_API_KEY": "YOUR_PERPLEXITY_API_KEY_HERE",
        "MODEL": "claude-3-7-sonnet-20250219",
        "PERPLEXITY_MODEL": "sonar-pro",
        "MAX_TOKENS": 64000,
        "TEMPERATURE": 0.2,
        "DEFAULT_SUBTASKS": 5,
        "DEFAULT_PRIORITY": "medium"
      }
    }
  }
}

# Add Github MCP server
claude mcp add-json github '{
  "command": "npx",
      "args": ["-y", "--package=task-master-ai", "task-master-ai"],
      "env": {
        "ANTHROPIC_API_KEY": "YOUR_ANTHROPIC_API_KEY_HERE",
        "PERPLEXITY_API_KEY": "YOUR_PERPLEXITY_API_KEY_HERE",
        "OPENAI_API_KEY": "YOUR_OPENAI_KEY_HERE",
        "GOOGLE_API_KEY": "YOUR_GOOGLE_KEY_HERE",
        "MISTRAL_API_KEY": "YOUR_MISTRAL_KEY_HERE",
        "OPENROUTER_API_KEY": "YOUR_OPENROUTER_KEY_HERE",
        "XAI_API_KEY": "YOUR_XAI_KEY_HERE",
        "AZURE_OPENAI_API_KEY": "YOUR_AZURE_KEY_HERE"
      },
}'

# Add Context7 MCP server


# List configured servers
claude mcp list
```


## 10. Project Analysis Command
```bash
# Create comprehensive project structure view
cat > .claude/commands/analyze-project.md << 'EOF'
# Analyze Project Structure
> Comprehensive project analysis and documentation
> Develop plan before analyzing project
> Check with human before analyzing project

## Commands to run:
```bash
# Tree view (if eza available)
eza . --tree --git-ignore --level 3

# Alternative with standard tools
find . -type f -name "*.md" -o -name "*.json" -o -name "*.ts" -o -name "*.py" | head -20

# Check for key files
ls -la README.md package.json pyproject.toml .env .gitignore
```

## 11. Code Review Command
```bash
# Create code review command
cat > .claude/commands/code-review.md << 'EOF'
# Code Review
> Comprehensive code review and analysis
> Develop plan before code review
> Check with human before code review
```

## 12. Find Dead Code Command
```bash
# Create find dead code command
cat > .claude/commands/find-dead-code.md << 'EOF'
# Find Dead Code
> Identify and remove unused code
> Develop plan before find dead code
> Check with human before find dead code
```

## 13. Refactor Command
```bash
# Create refactor command
cat > .claude/commands/refactor.md << 'EOF'
# Refactor Code
> Refactor codebase for improved readability and maintainability
> Develop plan before refactoring
> Check with human before refactoring
```

## 14. Code Cleanup Command
```bash
# Create code cleanup command
cat > .claude/commands/code-cleanup.md << 'EOF'
# Code Cleanup
> Clean up codebase for improved readability and maintainability
> Develop plan before refactoring
> Check with human before refactoring
```

## Files to read in parallel:
- README.md
- package.json / pyproject.toml
- Any .claude/CLAUDE.md file
- Key source files in src/ or lib/

## 15. Final Setup Tasks
```bash
# Create .gitignore if not exists
cat > .gitignore << 'EOF'
# Dependencies
node_modules/
.venv/
__pycache__/
*.pyc

# Environment
.env
.env.local

# Build outputs
dist/
build/
*.egg-info/

# IDE
.vscode/
.idea/

# Task Master
.task-master/cache/
mcp.json
```

# Create initial README
```bash
cat > README.md << 'EOF'

# Project Name

(generate based on repository information)

```

# Stage and commit bootstrap files
git add .
git commit -m "Bootstrap project with Bun, UV, and Task Master

- Initialize Bun TypeScript project
- Set up Python environment with UV
- Configure Task Master for AI-powered development
- Create Claude custom commands for workflow automation
- Add comprehensive .gitignore and README"
```

## Summary
This bootstrap process creates a sophisticated development environment with:
1. **Git repository** with clean initial state
2. **Bun project** for TypeScript/JavaScript development
3. **Task Master** for AI-powered task management
4. **UV-managed Python** environment with AI packages
5. **Custom Claude commands** for streamlined workflows
6. **Documentation** for Roo integration and best practices

The setup enables:
- Test-driven development with atomic commits
- AI-assisted coding with extended thinking
- Systematic change review and committing
- Integration with external tools via MCP
- Collaborative development with Roo

