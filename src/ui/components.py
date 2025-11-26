"""
═══════════════════════════════════════════════════════════════
TUI Component Library - Rich-based Interface Elements
═══════════════════════════════════════════════════════════════
Design Principles:
  - Single Responsibility (Message/Tool/State independent)
  - Stateless Rendering (Input Data -> Output Format, No Side Effects)
  - Visual Clarity (Borders/Colors/Icons distinguish content)
"""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
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
    """
    # Eliminate special cases with a mapping table
    message_styles = {
        HumanMessage: ("👤 User", "blue"),
        AIMessage: ("🤖 Assistant", "green"),
        ToolMessage: ("🔧 Tool", "yellow"),
    }

    # Get style (default gray)
    title, color = message_styles.get(type(message), ("📝 Message", "white"))

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
            Panel(Markdown(content), title=title, border_style=color, padding=(1, 2))
        )


def _render_tool_calls(tool_calls: list) -> None:
    """Render tool call list (Internal helper)"""
    table = Table(title="🔧 Tool Calls", border_style="cyan")
    table.add_column("Tool", style="cyan")
    table.add_column("Arguments", style="white")

    for call in tool_calls:
        tool_name = call.get("name", "Unknown")
        args = str(call.get("args", {}))
        table.add_row(tool_name, args)

    console.print(table)


# ═══════════════════════════════════════════════════════════════
# Welcome Screen
# ═══════════════════════════════════════════════════════════════


def render_welcome() -> None:
    """Display welcome screen"""
    welcome_text = """
# 🚀 TUI Code Agent

An Intelligent Code Agent powered by LangGraph

## 🎮 Available Commands
- Enter task description to start
- `exit`, `quit`, `q` to exit
- `clear` to clear screen

## 🛠️  Available Tools
- 📄 `read_file` - Read file content
- 📝 `write_file` - Write file
- 📂 `list_files` - List directory
- 🐚 `shell` - Execute Shell command

---
**💡 Tip:** Press `[Esc]` then `[Enter]` to submit multi-line input.
    """

    console.print(
        Panel(
            Markdown(welcome_text),
            border_style="bold cyan",
            title="[bold white]Welcome[/bold white]",
            subtitle="[dim]v0.1.0[/dim]",
            padding=(1, 2),
            expand=False,
        )
    )
    console.print()


# ═══════════════════════════════════════════════════════════════
# Status Indicator
# ═══════════════════════════════════════════════════════════════


def show_thinking() -> Progress:
    """
    Display thinking progress bar

    Returns Progress object, caller is responsible for stop()
    """
    progress = Progress(
        SpinnerColumn(), TextColumn("[cyan]Thinking..."), console=console
    )
    progress.start()
    return progress


# ═══════════════════════════════════════════════════════════════
# Separator
# ═══════════════════════════════════════════════════════════════


def render_separator() -> None:
    """Render separator line"""
    console.print("─" * console.width, style="dim")
