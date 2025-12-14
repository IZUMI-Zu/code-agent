# Code Agent

A multi-agent code assistant powered by LangGraph that orchestrates Planner, Coder, and Reviewer agents to autonomously handle software development tasks.

## What & Why

**What is Code Agent?**
Code Agent is an AI-powered coding assistant that breaks down complex programming tasks into structured workflows. Instead of a single LLM handling everything, it uses specialized agents (Planner, Coder, Reviewer) coordinated by a Supervisor for better task execution.

**Why use it?**
- **Task Decomposition**: Planner analyzes requirements and creates execution plans
- **Safe Execution**: Human-in-the-loop confirms file operations and shell commands
- **Quality Control**: Reviewer validates code before completion
- **Model Flexibility**: Supports OpenAI, DeepSeek, Qwen, and any OpenAI-compatible APIs

## Core Features

- **Multi-Agent Collaboration**: Supervisor → Planner → Coder → Reviewer workflow
- **Intelligent Routing**: Context-aware agent orchestration
- **Human-in-the-Loop**: Tool execution requires user confirmation
- **Workspace Isolation**: Pattern-based file access control
- **Streaming Output**: Real-time agent reasoning and tool execution display
- **Cross-Platform**: Unified filesystem abstraction (Windows/macOS/Linux)

## Quick Start

### Requirements

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/) (Python package installer)
- LLM API Key (OpenAI, DeepSeek, Qwen, or compatible providers)

### Installation

```bash
# 1. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
# or
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# 2. Clone repository
git clone https://github.com/IZUMI-Zu/code-agent
cd code-agent

# 3. Install dependencies
uv sync
```

### Configuration

Create `.env` file:

```bash
# API Configuration
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1  # custom endpoint

# Model Configuration
REASONING_MODEL=qwen/qwen3-coder-plus              # Main reasoning model
LIGHTWEIGHT_MODEL=openai/gpt-4o-mini               # Fast task model

# Web Search
BRAVE_API_KEY=your_brave_api_key
```

**Supported Model Providers**:

- OpenAI: `openai/gpt-4o`, `openai/gpt-4o-mini`
- DeepSeek: `deepseek/deepseek-chat`
- Qwen: `qwen/qwen3-coder-plus`
- Any OpenAI-compatible API via `OPENAI_BASE_URL`

### Run

```bash
uv run code-agent
uv run ca -w ~/my-project
```

## Examples

Complete arXiv CS Daily applications built with different tools for comparison. All implement the same requirements: category navigation, daily paper lists, and citation generation.

### Code Agent (Multi-Model Comparison)

Code Agent examples using different LLM providers:

| Model                  | Path                                | Language   | Rounds | Fixes | Notes                          |
| ---------------------- | ----------------------------------- | ---------- | ------ | ----- | ------------------------------ |
| **Claude Sonnet 4.5**  | `examples/code-agent/claude-sonnet-4.5/` | JavaScript | 3      | 0     | Clean implementation           |
| **DeepSeek Chat v3**   | `examples/code-agent/deepseek-v3/`       | TypeScript | 2      | 0     | Node proxy + Tailwind fix      |
| **Qwen3 Coder Plus**   | `examples/code-agent/qwen3-coder-plus/`  | JavaScript | 3      | 3     | Manual adjustments needed      |

### Baseline Tools (Industry Comparison)

Established coding assistants for benchmarking:

| Tool              | Path                          | Language   | Rounds | Code Size | CORS Handling  |
| ----------------- | ----------------------------- | ---------- | ------ | --------- | -------------- |
| **Claude Code**   | `examples/baseline/claude-code/` | TypeScript | 2      | 656 LOC   | Auto + Backend |
| **Gemini CLI**    | `examples/baseline/gemini/`      | TypeScript | 3      | 420 LOC   | Auto-detected  |

### Quick Run

```bash
# Code Agent example (Claude Sonnet 4.5)
cd examples/code-agent/claude-sonnet-4.5
npm install && npm run dev

# Baseline example (Gemini CLI)
cd examples/baseline/gemini
npm install && npm run dev
```

**Detailed analysis**: See [`examples/README.md`](examples/README.md) for architecture comparison and metrics.

## Architecture

### State Graph Workflow

```bash
┌─────────┐
│  START  │
└────┬────┘
     │
     ▼
┌──────────────┐
│  Supervisor  │◄─────┐
│ (Orchestrator)│      │
└──────┬───────┘      │
       │              │
       ├──► Planner ──┤
       ├──► Coder ────┤
       ├──► Reviewer ─┤
       │              │
       ▼              │
    FINISH ◄──────────┘
```

### Agent Responsibilities

| Agent      | Responsibility                          | Tool Access |
| ---------- | --------------------------------------- | ----------- |
| Supervisor | Analyze task, route to next executor    | ❌           |
| Planner    | Break down task, create execution plan  | ✅           |
| Coder      | Code implementation, file ops, commands | ✅           |
| Reviewer   | Code review, testing, quality control   | ✅           |

## Tool Capabilities

### File I/O

- `read_file`: Read file contents
- `write_file`: Write/overwrite file
- `list_files`: List directory contents

### Filesystem Operations (Cross-platform)

- `create_directory`: Create directory
- `copy_file`: Copy file/directory
- `move_file`: Move/rename
- `delete_path`: Delete file/directory
- `path_exists`: Check path existence

### Editing

- `str_replace`: Exact string replacement
- `insert_lines`: Insert lines at specific position

### Search

- `grep_search`: Regex based file search

### Shell

- `shell`: Execute system commands (advanced users)

### Planning

- `submit_plan`: Submit task plan (Planner only)

### External Services

- `brave_search`: Web search (requires API key)

## Interactive Commands

Available commands in TUI:

- `clear`: Clear screen
- `exit` / `quit` / `q`: Exit application
- `Ctrl+D`: Exit
- `Enter`: Submit input
- `Alt+Enter`: New line

## Development Guide

### Project Structure

```bash
code-agent/
├── code_agent/
│   ├── __main__.py           # CLI entry point
│   ├── agent/
│   │   ├── graph.py          # State graph definition
│   │   ├── state.py          # State models
│   │   ├── context.py        # Context management
│   │   ├── structured_output.py  # Output formatting
│   │   └── human_in_the_loop.py  # Tool confirmation
│   ├── prompts/
│   │   ├── agents.py         # Agent system prompts
│   │   └── supervisor.py     # Supervisor prompts
│   ├── tools/
│   │   ├── base.py           # Tool base class
│   │   ├── registry.py       # Tool registry
│   │   ├── file_ops.py       # File I/O
│   │   ├── filesystem.py     # Filesystem operations
│   │   ├── shell.py          # Shell execution
│   │   ├── search.py         # Web search
│   │   ├── planning.py       # Plan submission
│   │   ├── edit.py           # File editing
│   │   └── grep.py           # Code search
│   ├── ui/
│   │   ├── app.py            # TUI main controller
│   │   └── components.py     # UI components
│   ├── utils/
│   │   ├── logger.py         # Logging
│   │   ├── event_bus.py      # Event system
│   │   └── path.py           # Path utilities
│   └── config.py             # Configuration
├── pyproject.toml
├── .env.example
└── .env
```

### Adding New Tools

1. Create tool module under `code_agent/tools/`
2. Inherit from `BaseTool` base class
3. Implement `execute()` method
4. Register in `registry.py`

Example:

```python
from .base import BaseTool

class MyTool(BaseTool):
    """Tool description"""

    name: str = "my_tool"
    description: str = "Do something"

    def execute(self, param: str) -> str:
        """Execution logic"""
        return f"Result: {param}"
```

### Code Quality Guidelines

Follow these principles to eliminate code smells:

#### Hard Metrics

- Max 800 lines per file
- Max 8 files per directory level
- Max 20 lines per function (Linus's advice)
- Max 3 levels of indentation

#### Code Smell Detection

- Rigidity: One change triggers cascade of modifications
- Redundancy: Same logic repeated in multiple places
- Circular Dependency: Modules entangled with each other
- Fragility: Unrelated parts break unexpectedly
- Obscurity: Intent unclear, hard to understand
- Data Clump: Parameters always appear together
- Needless Complexity: Over-engineering

#### Optimization Direction

- Eliminate special cases, not add if/else branches
- Refactor data structures, not stack conditionals
- Pursue simplicity, not clever tricks

## Tech Stack

- **Core**: LangGraph 1.0+ / LangChain 1.0+
- **LLM**: OpenAI API (supports custom endpoints)
- **TUI**: Rich + prompt-toolkit
- **Config**: Pydantic Settings
- **Logging**: Python Logging

## License

MIT License
