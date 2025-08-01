# 🚀 Quick Launch Instructions for Query Engine Development

## Setup Complete! 

The query engine development environment is now ready for 3 parallel AI agents.

## 📋 How to Launch the Agents

### Option 1: Three Separate Claude Sessions (Recommended)

Open **3 terminal windows** and in each one:

#### Terminal 1 - Agent A (Data Foundation)
```bash
cd /Users/oceanheart/Documents/Manual Library/code/blackcore
claude
```
Then paste this message:
```
You are Agent A: Data Foundation Engineer. Read your specification at specs/v2/agent-a-data-foundation.md and your quick start guide at blackcore/minimal/query_engine/AGENT-A-START-HERE.md. Begin implementing the data foundation layer focusing on loaders/, filters/, and sorting/ modules. Start with JSONDataLoader. Update .coordination/status.json as you complete modules.
```

#### Terminal 2 - Agent B (Intelligence & Search)  
```bash
cd /Users/oceanheart/Documents/Manual Library/code/blackcore
claude
```
Then paste this message:
```
You are Agent B: Intelligence & Search Engineer. Read your specification at specs/v2/agent-b-intelligence-search.md and your quick start guide at blackcore/minimal/query_engine/AGENT-B-START-HERE.md. Begin implementing search/, relationships/, and nlp/ modules. Start by defining interfaces. Check .coordination/status.json for Agent A's progress.
```

#### Terminal 3 - Agent C (Performance & Export)
```bash
cd /Users/oceanheart/Documents/Manual Library/code/blackcore
claude
```
Then paste this message:
```
You are Agent C: Performance & Export Engineer. Read your specification at specs/v2/agent-c-performance-export.md and your quick start guide at blackcore/minimal/query_engine/AGENT-C-START-HERE.md. Begin implementing cache/, optimization/, and export/ modules. Start with MemoryCache. Monitor .coordination/status.json for dependencies.
```

### Option 2: Single Claude with Task Master

In a single Claude session:
```
Use the task-master MCP to create three parallel development tasks:

1. Agent A (Data Foundation): Implement loaders/, filters/, and sorting/ modules following specs/v2/agent-a-data-foundation.md
2. Agent B (Intelligence & Search): Implement search/, relationships/, and nlp/ modules following specs/v2/agent-b-intelligence-search.md  
3. Agent C (Performance & Export): Implement cache/, optimization/, and export/ modules following specs/v2/agent-c-performance-export.md

Each agent should read their AGENT-[A/B/C]-START-HERE.md file in blackcore/minimal/query_engine/ and update .coordination/status.json as they progress.
```

## 📊 Monitor Progress

In a separate terminal:
```bash
cd /Users/oceanheart/Documents/Manual Library/code/blackcore
python scripts/query-engine/monitor-agents.py
```

Or watch the raw status:
```bash
watch -n 5 'cat blackcore/minimal/query_engine/.coordination/status.json | jq .'
```

## 🎯 Expected Outcomes

- **Hour 1**: All interfaces defined, basic implementations started
- **Hour 2**: Core functionality complete, integration beginning
- **Hour 3**: Optimization and advanced features
- **Hour 4**: Full integration, testing, and documentation

## 📁 File Structure

The agents will create files in:
```
blackcore/minimal/query_engine/
├── loaders/          # Agent A
├── filters/          # Agent A  
├── sorting/          # Agent A
├── search/           # Agent B
├── relationships/    # Agent B
├── nlp/             # Agent B
├── cache/           # Agent C
├── optimization/    # Agent C
├── export/          # Agent C
└── .coordination/   # Shared status
```

## 🔧 Troubleshooting

- If agents get blocked, check `.coordination/status.json`
- Agents can work with mocks if dependencies aren't ready
- The monitor script shows real-time progress
- Each agent has a START-HERE.md file with specific instructions

## 🚦 Ready to Launch!

The environment is set up and waiting. Launch your agents and watch them build the query engine in parallel!