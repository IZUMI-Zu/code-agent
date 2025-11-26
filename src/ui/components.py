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
    Render a single message

    Supported Types:
      - HumanMessage: User Input
      - AIMessage: AI Response
      - ToolMessage: Tool Result

    Good Taste:
      - Clean, minimal design without borders
      - Clear visual hierarchy through typography
    """
    # Render content
    content = message.content if hasattr(message, "content") else str(message)

    # If AI message contains tool calls, skip rendering here
    # (tool calls are rendered separately in real-time)
    if isinstance(message, AIMessage) and hasattr(message, "tool_calls"):
        tool_calls = message.tool_calls or []
        if tool_calls and not content.strip():
            return  # Tool calls already shown in real-time

    # Render based on message type
    if isinstance(message, HumanMessage):
        # User message - simple and clean
        if content.strip():
            console.print(f"\n[bold cyan]You:[/bold cyan] {content}")

    elif isinstance(message, AIMessage):
        # AI response - markdown formatted
        if content.strip():
            console.print(f"\n[bold green]Assistant:[/bold green]")
            console.print(Markdown(content))

    elif isinstance(message, ToolMessage):
        # Tool results are handled in real-time, skip duplicate rendering
        pass


def _render_tool_calls(tool_calls: list) -> None:
    """Render tool call list (Internal helper - now unused, kept for compatibility)"""
    # Tool calls are now rendered in real-time during execution
    pass


# ═══════════════════════════════════════════════════════════════
# Welcome Screen
# ═══════════════════════════════════════════════════════════════


def render_welcome() -> None:
    """
    Display welcome screen (Claude Code style)

    Design Philosophy:
      - Clean and minimal
      - Informative without overwhelming
    """
    console.print("\n[bold bright_cyan]TUI Code Agent[/bold bright_cyan]", style="bold")
    console.print("[dim]An intelligent multi-agent system powered by LangGraph[/dim]\n")

    console.print("[bold]Quick Start:[/bold]")
    console.print('  • "Create a Python script to analyze CSV files"')
    console.print('  • "Find all TODOs in my codebase"')
    console.print('  • "Explain the main.py file to me"\n')

    console.print("[bold]Commands:[/bold]")
    console.print("  • [cyan]exit[/cyan] / [cyan]quit[/cyan] / [cyan]q[/cyan] - Exit")
    console.print("  • [cyan]clear[/cyan] - Clear screen")
    console.print("  • [dim][Enter] to submit | [Alt+Enter] for newline[/dim]\n")

    console.print(
        "[dim]💡 The agent will ask for approval before destructive operations.[/dim]\n"
    )


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


def render_tool_execution(
    tool_name: str,
    args: dict = None,
    status: str = "running",
    duration: float = None,
    error: str = None,
) -> None:
    """
    Render tool execution status with enhanced visibility

    Args:
        tool_name: Name of the tool being executed
        args: Tool arguments (optional)
        status: "running" | "completed" | "failed"
        duration: Execution time in seconds (optional)
        error: Error message if failed (optional)

    Design Philosophy:
      - Real-time visibility into every tool execution
      - Clear status indication with appropriate colors
      - Execution time for performance awareness
    """
    status_styles = {
        "running": ("⏳", "cyan"),
        "completed": ("✓", "green"),
        "failed": ("✗", "red"),
    }

    icon, color = status_styles.get(status, ("•", "white"))

    # Build output line
    parts = [f"[{color}]{icon}[/{color}]", f"[bold]{tool_name}[/bold]"]

    # Add argument preview for running status
    if status == "running" and args:
        args_preview = _format_args_preview(args)
        if args_preview:
            parts.append(f"[dim]{args_preview}[/dim]")

    # Add duration for completed/failed
    if duration is not None and status in ["completed", "failed"]:
        parts.append(f"[dim]({duration:.2f}s)[/dim]")

    console.print(" ".join(parts))

    # Show error details if failed
    if status == "failed" and error:
        # Highlight error in red
        console.print(f"  [red]Error: {error}[/red]")


def _format_args_preview(args: dict, max_length: int = 60) -> str:
    """Format arguments for display preview"""
    if not args:
        return ""

    # Priority keys to show
    main_keys = ["command", "commands", "path", "file_path", "query", "content"]

    for key in main_keys:
        if key in args:
            value = str(args[key])
            if len(value) > max_length:
                value = value[: max_length - 3] + "..."
            return f"{key}={value}"

    # Fallback: show first key
    if args:
        first_key = next(iter(args))
        value = str(args[first_key])
        if len(value) > max_length:
            value = value[: max_length - 3] + "..."
        return f"{first_key}={value}"

    return ""


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
    """Render tool confirmation dialog (Claude Code style)"""

    console.print()
    console.print("[bold yellow]⚠ Confirmation Required[/bold yellow]")
    console.print(f"[bold]Tool:[/bold] [cyan]{tool_name}[/cyan]")

    if description:
        console.print(f"[dim]{description}[/dim]")

    # Format arguments
    if isinstance(args, dict):
        try:
            args_str = json.dumps(args, indent=2)
            console.print("\n[bold]Arguments:[/bold]")
            console.print(Syntax(args_str, "json", theme="monokai", word_wrap=True))
        except TypeError:
            console.print(f"\n[bold]Arguments:[/bold] {args}")
    else:
        console.print(f"\n[bold]Arguments:[/bold] {args}")

    console.print()
