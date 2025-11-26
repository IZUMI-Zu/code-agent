"""
═══════════════════════════════════════════════════════════════
TUI Component Library - Rich-based Interface Elements
═══════════════════════════════════════════════════════════════
Design Principles:
  - Single Responsibility (Message/Tool/State independent)
  - Stateless Rendering (Input Data -> Output Format, No Side Effects)
  - Visual Clarity (Borders/Colors/Icons distinguish content)
"""

import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table

# ═══════════════════════════════════════════════════════════════
# Global Console Instance
# ═══════════════════════════════════════════════════════════════

console = Console()


# ═══════════════════════════════════════════════════════════════
# Message Renderer
# ═══════════════════════════════════════════════════════════════


def render_message(message) -> None:
    """
    Render a single message (Automatically select style based on type)

    Supported Types:
      - HumanMessage: User Input (Blue Border)
      - AIMessage: AI Response (Green Border)
      - ToolMessage: Tool Result (Yellow Border)

    Good Taste:
      - Mapping table eliminates type checking spaghetti
      - Each message type has consistent visual identity
    """
    # Eliminate special cases with a mapping table
    message_styles = {
        HumanMessage: ("👤 You", "bright_blue", "bold blue"),
        AIMessage: ("🤖 Assistant", "bright_green", "bold green"),
        ToolMessage: ("🔧 Tool Result", "bright_yellow", "bold yellow"),
    }

    # Get style (default gray)
    title, border_color, title_style = message_styles.get(
        type(message), ("📝 Message", "white", "bold white")
    )

    # Render content
    content = message.content if hasattr(message, "content") else str(message)

    # If AI message contains tool calls, display separately
    if isinstance(message, AIMessage) and hasattr(message, "tool_calls"):
        tool_calls = message.tool_calls or []
        if tool_calls:
            _render_tool_calls(tool_calls)
            return  # Tool calls don't show text content

    # Normal message display
    if content.strip():
        console.print(
            Panel(
                Markdown(content),
                title=f"[{title_style}]{title}[/{title_style}]",
                border_style=border_color,
                padding=(1, 2),
            )
        )


def _render_tool_calls(tool_calls: list) -> None:
    """Render tool call list (Internal helper)"""
    table = Table(title="🔧 Tool Calls", border_style="cyan")
    table.add_column("Tool", style="cyan")
    table.add_column("Arguments", style="white")

    for call in tool_calls:
        tool_name = call.get("name", "Unknown")
        args = call.get("args", {})
        # Format args nicely if possible
        if isinstance(args, dict):
            try:
                args_str = json.dumps(args, indent=2)
            except TypeError:
                args_str = str(args)
        else:
            args_str = str(args)

        table.add_row(tool_name, args_str)

    console.print(table)


# ═══════════════════════════════════════════════════════════════
# Welcome Screen
# ═══════════════════════════════════════════════════════════════


def render_welcome() -> None:
    """
    Display welcome screen

    Design Philosophy:
      - First impression matters: clean, professional, informative
      - Guide user without overwhelming them
    """
    welcome_text = """
# 🤖 TUI Code Agent

> *An intelligent multi-agent system powered by LangGraph*

## 💬 Quick Start
Just type what you want to do:
- `"Create a Python script to analyze CSV files"`
- `"Find all TODOs in my codebase"`
- `"Explain the main.py file to me"`

## 🎛️  Commands
- `exit` / `quit` / `q` - Exit application
- `clear` - Clear screen
- `[Enter]` - Submit message
- `[Alt+Enter]` - New line in message

## 🛠️  Available Tools
- **read_file** - Read file content
- **write_file** - Create or modify files
- **list_files** - Browse directory structure
- **shell** - Execute shell commands
- **web_search** - Search the web for information

---
*💡 The agent will ask for your approval before executing potentially destructive operations.*
    """

    console.print(
        Panel(
            Markdown(welcome_text),
            border_style="bold bright_cyan",
            title="[bold bright_white]╔══ Welcome ══╗[/bold bright_white]",
            subtitle="[dim italic]v0.2.0 · Enhanced Visibility Edition[/dim italic]",
            padding=(1, 3),
            expand=False,
        )
    )
    console.print()


# ═══════════════════════════════════════════════════════════════
# Status Indicator
# ═══════════════════════════════════════════════════════════════


def show_thinking(task: str = "Thinking") -> Progress:
    """
    Display thinking progress bar with task description

    Args:
        task: Description of current task (default: "Thinking")

    Returns Progress object, caller is responsible for stop()

    Good Taste:
      - Single spinner, no nested progress bars
      - Clear task description guides user attention
    """
    progress = Progress(
        SpinnerColumn(spinner_name="dots12"),
        TextColumn(f"[bold cyan]{task}..."),
        console=console,
        transient=True,  # Auto-clear when stopped
    )
    progress.start()
    return progress


def render_tool_execution(tool_name: str, args: dict, status: str = "running") -> None:
    """
    Render tool execution status

    Args:
        tool_name: Name of the tool being executed
        args: Tool arguments
        status: "running" | "completed" | "failed" | "approved"

    Design Philosophy:
      - Tool execution is a first-class citizen, not hidden
      - Status colors guide user's emotional response
    """
    status_styles = {
        "running": ("🔄", "cyan", "Running"),
        "completed": ("✅", "green", "Completed"),
        "failed": ("❌", "red", "Failed"),
        "approved": ("👍", "yellow", "Approved"),
    }

    icon, color, status_text = status_styles.get(
        status, ("🔧", "white", "Unknown")
    )

    # Build argument preview (first 100 chars)
    args_preview = ""
    if args:
        if isinstance(args, dict):
            # Show most important arg
            main_keys = ["command", "commands", "path", "file_path", "query"]
            for key in main_keys:
                if key in args:
                    args_preview = f"{key}={args[key]}"
                    break
            if not args_preview:
                # Fallback: show first key
                first_key = next(iter(args))
                args_preview = f"{first_key}={args[first_key]}"
        else:
            args_preview = str(args)

    # Truncate if too long
    if len(args_preview) > 80:
        args_preview = args_preview[:77] + "..."

    console.print(
        f"{icon} [bold {color}]{status_text}[/bold {color}] [dim]│[/dim] "
        f"[bold]{tool_name}[/bold] [dim]{args_preview}[/dim]"
    )


# ═══════════════════════════════════════════════════════════════
# Separator
# ═══════════════════════════════════════════════════════════════


def render_separator() -> None:
    """
    Render separator line

    Design Philosophy:
      - Visual breathing room between interactions
      - Subtle, not distracting
    """
    console.print("─" * console.width, style="dim cyan")


# ═══════════════════════════════════════════════════════════════
# Confirmation Dialog
# ═══════════════════════════════════════════════════════════════


def render_tool_confirmation(
    tool_name: str, args: any, description: str = None
) -> None:
    """Render tool confirmation dialog"""

    # Format arguments
    if isinstance(args, dict):
        try:
            # Try to format as JSON
            args_str = json.dumps(args, indent=2)
            args_display = Syntax(args_str, "json", theme="monokai", word_wrap=True)
        except TypeError:
            # Fallback to string representation if not JSON serializable
            args_display = str(args)
    else:
        args_display = str(args)

    # Build content
    console.print()
    console.print(
        Panel(
            f"[bold cyan]Tool:[/bold cyan] {tool_name}\n"
            + (f"[bold]Description:[/bold] {description}\n" if description else "")
            + "\n[bold]Arguments:[/bold]",
            title="[bold yellow]⚠️  Confirmation Required[/bold yellow]",
            border_style="yellow",
            padding=(1, 2),
        )
    )

    # Print args separately to handle Syntax highlighting or raw text correctly
    console.print(Panel(args_display, border_style="dim", padding=(1, 2)))
    console.print()
