import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.status import Status
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

# Global Console Instance & Color Palette
console = Console()

COLORS = {
    "primary": "bright_blue",  # Indigo/Blue
    "secondary": "bright_cyan",  # Cyan/Sky
    "accent": "bright_magenta",  # Purple
    "success": "green",
    "warning": "yellow",
    "error": "red",
    "text": "white",
    "dim": "bright_black",  # Slate-ish
    "dimmer": "dim",
}

# 扁平化 Icon 系统 (Terminal 原生, 无 emoji)
ICONS = {
    # 状态指示
    "success": "✓",
    "error": "✗",
    "warning": "!",
    "running": "·",
    "flow": "→",
    # Agent 类型
    "planner": "■",
    "coder": "▸",
    "reviewer": "○",
    "thinking": "·",
    # 文件/目录
    "file": "→",
    "directory": "↳",
    "preview": "→",
    # 系统
    "shell": "$",
    "timeline": "│",
}


# Streaming Text Renderer


class StreamingPanel:
    """
    Real-time streaming panel with timeline layout
    """

    def __init__(self):
        self._buffer = ""
        self._live = None
        self._finished = False

    def start(self):
        """Start the streaming display"""
        # Initial empty table
        grid = self._create_grid("")

        self._live = Live(
            grid,
            console=console,
            refresh_per_second=15,
            vertical_overflow="visible",
        )
        self._live.start()

    def _create_grid(self, content: str) -> Table:
        """Create the layout grid with timeline"""
        grid = Table.grid(padding=(0, 1))
        grid.add_column(style="dim", width=3, justify="left")  # │ column
        grid.add_column(style="white")  # Content column

        # If content is empty, just show the line
        if not content:
            grid.add_row(ICONS["timeline"], "")
        else:
            # Render content as Markdown for nice formatting & wrapping
            # Note: Markdown will handle wrapping within the column width automatically
            md = Markdown(content)
            grid.add_row(ICONS["timeline"], md)

        return grid

    def append(self, token: str):
        """Append a token to the stream"""
        if self._finished:
            return

        self._buffer += token

        if self._live:
            # Update Live with new grid containing updated Markdown
            self._live.update(self._create_grid(self._buffer))

    def finish(self):
        """Finish streaming"""
        if self._finished:
            return

        self._finished = True

        if self._live:
            # Final update
            if self._buffer.strip():
                self._live.update(self._create_grid(self._buffer))
            self._live.stop()
            self._live = None

    @property
    def text(self) -> str:
        """Get the accumulated text"""
        return self._buffer


# Message Renderer


def render_message(message) -> None:
    """
    Render a single message
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


# Welcome Screen


def render_welcome() -> None:
    console.print()

    # Modern Header
    grid = Table.grid(padding=(0, 1))
    grid.add_column()

    grid.add_row(f"[bold {COLORS['primary']}]TUI Code Agent[/bold {COLORS['primary']}]")
    grid.add_row("[dim]An intelligent multi-agent system powered by LangGraph[/dim]")

    console.print(grid)
    console.print()

    # Hints
    console.print("[dim]Type your request or use [cyan]/help[/cyan] to see available commands[/dim]")
    console.print()


def render_agent_header(worker_name: str) -> None:
    """
    Render agent header with timeline
    """
    agent_icons = {
        "Planner": "📋",
        "Coder": "💻",
        "Reviewer": "🔍",
    }
    agent_colors = {
        "Planner": "bright_magenta",
        "Coder": "bright_cyan",
        "Reviewer": "bright_yellow",
    }

    icon = agent_icons.get(worker_name, "💭")
    color = agent_colors.get(worker_name, "white")

    # Timeline spacing
    console.print()

    # Header line
    grid = Table.grid(padding=(0, 1))
    grid.add_column(style="dim", width=3)  # │
    grid.add_column()

    grid.add_row(ICONS["timeline"], f"[bold {color}]{icon} {worker_name}[/bold {color}]")
    console.print(grid)


# Status Indicator


def show_thinking(task: str = "Thinking") -> Status:
    status = console.status(
        f"[{COLORS['dimmer']}]{ICONS['thinking']} {task}...[/{COLORS['dimmer']}]",
        spinner="dots",
    )
    status.start()
    return status


def start_tool_spinner(tool_name: str, args: Any = None) -> Status:
    args_preview = _format_args_preview(args, max_length=50)
    label = f"[{COLORS['accent']}]{ICONS['running']} {tool_name}[/{COLORS['accent']}]"
    if args_preview:
        label += f" [{COLORS['dimmer']}]{args_preview}[/{COLORS['dimmer']}]"

    status = console.status(label, spinner="dots")
    status.start()
    return status


def render_tool_execution(
    tool_name: str,
    args: Any = None,
    status: str = "running",
    duration: float | None = None,
    error: str | None = None,
    worker: str | None = None,
) -> None:
    status_config = {
        "running": (ICONS["running"], "bold bright_magenta"),
        "completed": (ICONS["success"], "bold bright_cyan"),
        "failed": (ICONS["error"], "bold red"),
        "rejected": (ICONS["warning"], "bold yellow"),
        "control_flow": (ICONS["flow"], "bold bright_blue"),
    }
    icon, action_color = status_config.get(status, ("·", "white"))
    worker_prefix = ""
    if worker:
        worker_prefix = f"[dim]{escape(worker)}[/dim] "

    action_verb = {
        "running": "Running",
        "completed": "Completed",
        "failed": "Failed",
        "rejected": "Rejected",
        "control_flow": "Flow",
    }.get(status, "")

    args_text = ""
    if args:
        args_preview = _format_args_preview(args, max_length=60)
        if args_preview:
            args_text = f"[dim]{args_preview}[/dim]"

    duration_text = ""
    if duration is not None and status in ["completed", "failed", "control_flow"]:
        duration_text = f"[dim]({duration:.2f}s)[/dim]"

    content = f"[{action_color}]{icon} {action_verb}[/{action_color}] {worker_prefix}[bold]{escape(tool_name)}[/bold]"
    if args_text:
        content += f" {args_text}"
    if duration_text:
        content += f" {duration_text}"

    # Use Table for indentation
    grid = Table.grid(padding=(0, 1))
    grid.add_column(style="dim", width=3)  # │ + 2 spaces
    grid.add_column()  # Content

    grid.add_row(ICONS["timeline"], content)
    console.print(grid)

    if status == "failed" and error:
        error_grid = Table.grid(padding=(0, 1))
        error_grid.add_column(style="dim", width=5)  # │ + 4 spaces
        error_grid.add_column()
        error_grid.add_row(ICONS["timeline"], f"[{COLORS['error']}]└─ Error: {escape(error)}[/{COLORS['error']}]")
        console.print(error_grid)


def render_tool_result_preview(result_preview: str, tool_name: str | None = None) -> None:
    if not result_preview or not result_preview.strip():
        return

    if tool_name:
        tool_lower = tool_name.lower()
        if "read" in tool_lower or "grep" in tool_lower:
            if result_preview.strip().startswith(("{ ", "[ ")):
                # lexer = "json" # This was not actually used for Syntax highlighting
                pass
            elif "import " in result_preview or "def " in result_preview:
                # lexer = "python"
                pass
        elif "shell" in tool_lower or "bash" in tool_lower:
            # lexer = "bash"
            pass

    lines = result_preview.split("\n")
    preview_lines = lines[:5]
    has_more = len(lines) > 5

    # Header
    grid = Table.grid(padding=(0, 1))
    grid.add_column(style="dim", width=5)
    grid.add_column()
    grid.add_row(ICONS["timeline"], f"[dim]└─ {ICONS['preview']} Preview:[/dim]")
    console.print(grid)

    # Content
    for line in preview_lines:
        line_grid = Table.grid(padding=(0, 1))
        line_grid.add_column(style="dim", width=8)  # Indent 8
        line_grid.add_column()
        line_grid.add_row(ICONS["timeline"], f"[dim]{escape(line)}[/dim]")
        console.print(line_grid)

    if has_more:
        more_grid = Table.grid(padding=(0, 1))
        more_grid.add_column(style="dim", width=8)
        more_grid.add_column()
        more_grid.add_row(ICONS["timeline"], f"[dim]... [{len(lines) - 5} more lines][/dim]")
        console.print(more_grid)


def _format_args_preview(args: Any, max_length: int = 60) -> str:
    if not args:
        return ""

    if isinstance(args, str):
        preview = args
        if len(preview) > max_length:
            preview = preview[: max_length - 3] + "..."
        return escape(preview)

    priority_keys = [
        "command",
        "commands",
        "path",
        "file_path",
        "query",
        "content",
        "pattern",
    ]

    for key in priority_keys:
        if key in args:
            value = str(args[key])
            if len(value) > max_length:
                value = value[: max_length - 3] + "..."
            return escape(f"{key}={value}")
    if args:
        first_key = next(iter(args))
        value = str(args[first_key])
        if len(value) > max_length:
            value = value[: max_length - 3] + "..."
        return escape(f"{first_key}={value}")

    return ""


# Status Bar & Separator


def render_status_bar(model: str = "GPT-4", cost: str = "$0.00", workspace: str = "./") -> None:
    table = Table.grid(expand=True)
    table.add_column(justify="left", style=COLORS["dimmer"])
    table.add_column(justify="right", style=COLORS["dimmer"])

    left_info = f"Model: {model} | Cost: {cost}"
    right_info = f"📁 {workspace}"

    table.add_row(left_info, right_info)

    console.print("─" * console.width, style=COLORS["dim"])
    console.print(table)
    console.print()


def render_separator() -> None:
    console.print("─" * console.width, style=COLORS["dim"])


def render_shell_start(command: str, cwd: str | None = None) -> None:
    grid = Table.grid(padding=(0, 1))
    grid.add_column(style="dim", width=3)  # │ + 2 spaces
    grid.add_column()

    grid.add_row(
        ICONS["timeline"],
        f"[bold bright_cyan]{ICONS['shell']} Shell[/bold bright_cyan] [bold]$ {escape(command)}[/bold]",
    )
    console.print(grid)

    if cwd and cwd != ".":
        cwd_grid = Table.grid(padding=(0, 1))
        cwd_grid.add_column(style="dim", width=5)  # │ + 4 spaces
        cwd_grid.add_column()
        cwd_grid.add_row(ICONS["timeline"], f"[dim]└─ {ICONS['directory']} {escape(cwd)}[/dim]")
        console.print(cwd_grid)


def render_shell_output(line: str, stream: str = "stdout") -> None:
    grid = Table.grid(padding=(0, 1))
    grid.add_column(style="dim", width=8)  # Indent 8
    grid.add_column()

    if stream == "stderr":
        grid.add_row(ICONS["timeline"], f"[{COLORS['error']}]{escape(line)}[/{COLORS['error']}]")
    else:
        grid.add_row(ICONS["timeline"], f"[dim]{escape(line)}[/dim]")

    console.print(grid)


def render_shell_finished(return_code: int = 0, status: str = "completed") -> None:
    grid = Table.grid(padding=(0, 1))
    grid.add_column(style="dim", width=5)  # Indent 5
    grid.add_column()

    if status == "completed" and return_code == 0:
        grid.add_row(
            ICONS["timeline"],
            f"[{COLORS['success']}]{ICONS['success']} Completed (exit code: {return_code})[/{COLORS['success']}]",
        )
    elif status == "timeout":
        grid.add_row(ICONS["timeline"], f"[{COLORS['warning']}]{ICONS['warning']} Timed out[/{COLORS['warning']}]")
    else:
        grid.add_row(
            ICONS["timeline"],
            f"[{COLORS['error']}]{ICONS['error']} Failed (exit code: {return_code})[/{COLORS['error']}]",
        )
    console.print(grid)


# Confirmation Dialog


def render_tool_confirmation(
    tool_name: str,
    args: Any,
    description: str | None = None,
) -> None:
    console.print()

    title = Text()
    title.append("⚠ ", style=COLORS["warning"])
    title.append("Confirmation Required", style=f"bold {COLORS['warning']}")

    content_parts = []

    content_parts.append(Text(f"Tool: {tool_name}", style=f"bold {COLORS['accent']}"))

    if description:
        content_parts.append(Text(description, style=COLORS["dimmer"]))
        content_parts.append(Text())

    if tool_name == "write_file" and isinstance(args, dict) and "content" in args:
        file_path = args.get("file_path", "unknown")
        content = args.get("content", "")

        content_parts.append(Text(f"File: {file_path}", style=f"bold {COLORS['success']}"))
        content_parts.append(Text())

        lexer = "text"
        if "." in file_path:
            ext = file_path.split(".")[-1].lower()
            lexer = ext

        content_parts.append(Text("Content Preview:", style="bold"))
        content_parts.append(Syntax(content, lexer, theme="monokai", line_numbers=True, word_wrap=True))

        other_args = {k: v for k, v in args.items() if k not in ["file_path", "content"]}
        if other_args:
            content_parts.append(Text())
            content_parts.append(Text("Other Arguments:", style="bold"))
            try:
                args_str = json.dumps(other_args, indent=2)
                content_parts.append(Syntax(args_str, "json", theme="monokai", word_wrap=True))
            except TypeError:
                content_parts.append(Text(str(other_args)))

    else:
        if isinstance(args, dict):
            try:
                args_str = json.dumps(args, indent=2, default=str)
                content_parts.append(Text("Arguments:", style="bold"))
                content_parts.append(Syntax(args_str, "json", theme="monokai", word_wrap=True))
            except (TypeError, ValueError):
                content_parts.append(Text(f"Arguments: {args}"))
        elif hasattr(args, "model_dump"):
            try:
                args_str = json.dumps(args.model_dump(), indent=2, default=str)
                content_parts.append(Text("Arguments:", style="bold"))
                content_parts.append(Syntax(args_str, "json", theme="monokai", word_wrap=True))
            except (TypeError, ValueError):
                content_parts.append(Text(f"Arguments: {args}"))
        else:
            content_parts.append(Text(f"Arguments: {args}"))

    panel = Panel(
        Group(*content_parts),
        title=title,
        title_align="left",
        border_style=COLORS["warning"],
        padding=(1, 2),
    )

    console.print(panel)
    console.print()
