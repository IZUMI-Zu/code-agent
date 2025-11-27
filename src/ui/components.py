"""
═══════════════════════════════════════════════════════════════
TUI Component Library - Rich-based Interface Elements
═══════════════════════════════════════════════════════════════
Design Principles:
  - Single Responsibility (Message/Tool/State independent)
  - Stateless Rendering (Input Data -> Output Format, No Side Effects)
  - Visual Clarity (Borders/Colors/Icons distinguish content)
  - Streaming Support (Token-level real-time rendering)
"""

import json
import sys
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.markup import escape
from rich.status import Status
from rich.syntax import Syntax
from rich.text import Text

# ═══════════════════════════════════════════════════════════════
# Global Console Instance
# ═══════════════════════════════════════════════════════════════

console = Console()


# ═══════════════════════════════════════════════════════════════
# Streaming Text Renderer
# ═══════════════════════════════════════════════════════════════


class StreamingText:
    """
    Real-time streaming text renderer for AI responses

    Design Philosophy:
      - Token-by-token rendering for immediate feedback
      - Use Rich Live for flicker-free updates
      - Final Markdown render replaces streaming text (no duplication)

    Usage:
        streaming = StreamingText()
        streaming.start()
        for token in tokens:
            streaming.append(token)
        streaming.finish()
    """

    def __init__(self):
        self._buffer = ""
        self._live = None
        self._finished = False

    def start(self):
        """Start the streaming display"""
        self._live = Live(
            Text(""),
            console=console,
            refresh_per_second=15,
            vertical_overflow="visible",
        )
        self._live.start()

    def append(self, token: str):
        """Append a token to the stream"""
        if self._finished:
            return

        self._buffer += token

        if self._live:
            # During streaming, show plain text for speed
            # Markdown parsing on every token is too slow
            self._live.update(Text(self._buffer))

    def finish(self):
        """Finish streaming and render final markdown (replaces streaming text)"""
        if self._finished:
            return

        self._finished = True

        if self._live:
            # Update Live with final Markdown before stopping
            # This replaces the plain text with formatted Markdown
            if self._buffer.strip():
                self._live.update(Markdown(self._buffer))
            self._live.stop()
            self._live = None

    @property
    def text(self) -> str:
        """Get the accumulated text"""
        return self._buffer


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
            console.print("\n[bold green]Assistant:[/bold green]")
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


def show_thinking(task: str = "Thinking") -> Status:
    """
    Display thinking status with a modern spinner.

    Args:
        task: Description of current task (default: "Thinking")

    Returns Status object, caller is responsible for stop()

    Good Taste:
      - Modern spinner (dots)
      - Clear task description guides user attention
    """
    status = console.status(f"[bold cyan]{task}...[/bold cyan]", spinner="dots")
    status.start()
    return status


def start_tool_spinner(tool_name: str, args: Any = None) -> Status:
    """
    Start a spinner for tool execution.
    """
    args_preview = _format_args_preview(args)
    label = f"[bold cyan]Running {tool_name}[/bold cyan]"
    if args_preview:
        label += f" [dim]{args_preview}[/dim]"

    status = console.status(label, spinner="dots")
    status.start()
    return status


def render_tool_execution(
    tool_name: str,
    args: Any = None,
    status: str = "running",
    duration: float = None,
    error: str = None,
    worker: str = None,
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
        "rejected": ("✗", "yellow"),
    }

    icon, color = status_styles.get(status, ("•", "white"))

    # Build output line
    parts = [f"[{color}]{icon}[/{color}]"]
    if worker:
        parts.append(f"[magenta]{escape(worker)}[/magenta]")
    parts.append(f"[bold]{escape(tool_name)}[/bold]")

    # Add argument preview for ALL statuses (since running line might be replaced by spinner)
    if args:
        args_preview = _format_args_preview(args)
        if args_preview:
            parts.append(f"[dim]{args_preview}[/dim]")

    # Add duration for completed/failed
    if duration is not None and status in ["completed", "failed"]:
        parts.append(f"[dim]({duration:.2f}s)[/dim]")

    console.print(" ".join(parts))

    # Show error details if failed
    if status == "failed" and error:
        console.print(f"  [red]Error: {escape(error)}[/red]")


def _format_args_preview(args: Any, max_length: int = 60) -> str:
    """Format arguments for display preview"""
    if not args:
        return ""

    if isinstance(args, str):
        preview = args
        if len(preview) > max_length:
            preview = preview[: max_length - 3] + "..."
        return escape(preview)

    # Priority keys to show
    main_keys = ["command", "commands", "path", "file_path", "query", "content"]

    for key in main_keys:
        if key in args:
            value = str(args[key])
            if len(value) > max_length:
                value = value[: max_length - 3] + "..."
            return escape(f"{key}={value}")

    # Fallback: show first key
    if args:
        first_key = next(iter(args))
        value = str(args[first_key])
        if len(value) > max_length:
            value = value[: max_length - 3] + "..."
        return escape(f"{first_key}={value}")

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
# Shell Output Streaming (Claude Code Style)
# ═══════════════════════════════════════════════════════════════


def render_shell_start(command: str, cwd: str = None) -> None:
    """Render shell command start indicator"""
    console.print()
    console.print(f"[bold cyan]$ {escape(command)}[/bold cyan]")
    if cwd and cwd != ".":
        console.print(f"[dim]  (in {escape(cwd)})[/dim]")


def render_shell_output(line: str, stream: str = "stdout") -> None:
    """
    Render a single line of shell output in real-time
    
    Args:
        line: Output line content
        stream: "stdout" or "stderr"
    """
    if stream == "stderr":
        console.print(f"[red]{escape(line)}[/red]")
    else:
        console.print(f"[dim]{escape(line)}[/dim]")


def render_shell_finished(return_code: int = 0, status: str = "completed") -> None:
    """Render shell command completion status"""
    if status == "completed" and return_code == 0:
        console.print(f"[green]✓ Command completed (exit code: {return_code})[/green]")
    elif status == "timeout":
        console.print("[yellow]⚠ Command timed out[/yellow]")
    else:
        console.print(f"[red]✗ Command failed (exit code: {return_code})[/red]")


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

    # Special rendering for write_file to show content beautifully
    if tool_name == "write_file" and isinstance(args, dict) and "content" in args:
        file_path = args.get("file_path", "unknown")
        content = args.get("content", "")

        console.print(f"\n[bold]File:[/bold] [green]{file_path}[/green]")

        # Determine lexer from file extension
        lexer = "text"
        if "." in file_path:
            ext = file_path.split(".")[-1].lower()
            lexer = ext

        console.print("\n[bold]Content Preview:[/bold]")
        console.print(
            Syntax(content, lexer, theme="monokai", line_numbers=True, word_wrap=True)
        )

        # Show other args if any (excluding file_path and content)
        other_args = {
            k: v for k, v in args.items() if k not in ["file_path", "content"]
        }
        if other_args:
            console.print("\n[bold]Other Arguments:[/bold]")
            try:
                args_str = json.dumps(other_args, indent=2)
                console.print(Syntax(args_str, "json", theme="monokai", word_wrap=True))
            except TypeError:
                console.print(f"{other_args}")

    else:
        # Format arguments (Default behavior)
        if isinstance(args, dict):
            try:
                args_str = json.dumps(args, indent=2, default=str)
                console.print("\n[bold]Arguments:[/bold]")
                console.print(Syntax(args_str, "json", theme="monokai", word_wrap=True))
            except (TypeError, ValueError):
                console.print(f"\n[bold]Arguments:[/bold] {args}")
        elif hasattr(args, "model_dump"):
            # Handle Pydantic models
            try:
                args_str = json.dumps(args.model_dump(), indent=2, default=str)
                console.print("\n[bold]Arguments:[/bold]")
                console.print(Syntax(args_str, "json", theme="monokai", word_wrap=True))
            except (TypeError, ValueError):
                console.print(f"\n[bold]Arguments:[/bold] {args}")
        else:
            console.print(f"\n[bold]Arguments:[/bold] {args}")

    console.print()
