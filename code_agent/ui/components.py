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

# Claude Code 风格配色方案 (柔和、低饱和度)
COLORS = {
    # 主色调 - 紫蓝色系 (用于强调关键信息)
    "primary": "bright_blue",
    "secondary": "bright_magenta",
    "accent": "bright_cyan",
    # 语义色 - 降低视觉冲击
    "success": "green",
    "warning": "yellow",
    "error": "red",
    # Agent 标识色 (柔和区分不同 Agent)
    "planner": "bright_magenta",
    "coder": "bright_cyan",
    "reviewer": "bright_yellow",
    # 灰度层次 (信息优先级分级)
    "text": "white",
    "dim": "bright_black",
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


# Message Renderer


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


# Welcome Screen


def render_welcome() -> None:
    """
    极简欢迎界面(扁平化, 斜杠命令提示)

    Good Taste: 只显示必要信息, 节省空间
    """
    console.print()
    console.print(f"[bold {COLORS['primary']}]TUI Code Agent[/bold {COLORS['primary']}]")
    console.print(f"[{COLORS['dimmer']}]An intelligent multi-agent system powered by LangGraph[/{COLORS['dimmer']}]")
    console.print()
    console.print("[dim]Type your request or use [cyan]/help[/cyan] for commands[/dim]")
    console.print()


# Status Indicator


def show_thinking(task: str = "Thinking") -> Status:
    """
    思考状态指示器(扁平化)

    Good Taste: 降低视觉干扰, 用 dim 色调表示非关键信息
    """
    status = console.status(
        f"[{COLORS['dimmer']}]{ICONS['thinking']} {task}...[/{COLORS['dimmer']}]",
        spinner="dots",
    )
    status.start()
    return status


def start_tool_spinner(tool_name: str, args: Any = None) -> Status:
    """
    工具执行 Spinner(扁平化)

    Good Taste: 统一的色彩方案, 参数预览简化
    """
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
    """
    Timeline 风格工具执行渲染 (扁平化 icon)

    Good Taste:
      - 移除 Panel 盒子, 使用垂直线 │ 连接
      - 扁平化 icon, Terminal 原生美学
      - 动作动词用 bold magenta/cyan
    """
    # 状态图标与颜色(扁平化)
    status_config = {
        "running": (ICONS["running"], "bold bright_magenta"),
        "completed": (ICONS["success"], "bold bright_cyan"),
        "failed": (ICONS["error"], "bold red"),
        "rejected": (ICONS["warning"], "bold yellow"),
        "control_flow": (ICONS["flow"], "bold bright_blue"),
    }
    icon, action_color = status_config.get(status, ("·", "white"))

    # 构建 Timeline 行
    # 格式: │  ├─ 🔨 tool_name  [args]  [duration]

    # Worker 前缀(如果有)
    worker_prefix = ""
    if worker:
        worker_prefix = f"[dim]{escape(worker)}[/dim] "

    # 动作动词(根据状态)
    action_verb = {
        "running": "Running",
        "completed": "Completed",
        "failed": "Failed",
        "rejected": "Rejected",
        "control_flow": "Flow",
    }.get(status, "")

    # 参数预览
    args_text = ""
    if args:
        args_preview = _format_args_preview(args, max_length=60)
        if args_preview:
            args_text = f"[dim]{args_preview}[/dim]"

    # 时长
    duration_text = ""
    if duration is not None and status in ["completed", "failed", "control_flow"]:
        duration_text = f"[dim]({duration:.2f}s)[/dim]"

    # 组装主行
    line = f"[dim]│[/dim]  [{action_color}]{icon} {action_verb}[/{action_color}] {worker_prefix}[bold]{escape(tool_name)}[/bold]"

    if args_text:
        line += f" {args_text}"

    if duration_text:
        line += f" {duration_text}"

    console.print(line)

    # 错误信息(如果有)
    if status == "failed" and error:
        console.print(f"[dim]│[/dim]     [{COLORS['error']}]└─ Error: {escape(error)}[/{COLORS['error']}]")


def render_tool_result_preview(result_preview: str, tool_name: str | None = None) -> None:
    """
    Timeline 风格结果预览(移除 Panel, 使用缩进)

    Good Taste: 简洁的缩进, 不用盒子包裹
    """
    if not result_preview or not result_preview.strip():
        return

    # 检测语法类型
    # Removed unused lexer variable
    # lexer = "text"
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

    # 限制预览行数(最多 5 行, 更紧凑)
    lines = result_preview.split("\n")
    preview_lines = lines[:5]
    has_more = len(lines) > 5

    # Timeline 风格输出(扁平化)
    console.print(f"[dim]{ICONS['timeline']}[/dim]     [dim]└─ {ICONS['preview']} Preview:[/dim]")

    # 缩进显示每行
    for line in preview_lines:
        if line.strip():
            console.print(f"[dim]{ICONS['timeline']}[/dim]        [dim]{escape(line)}[/dim]")

    if has_more:
        console.print(f"[dim]{ICONS['timeline']}[/dim]        [dim]... [{len(lines) - 5} more lines][/dim]")


def _format_args_preview(args: Any, max_length: int = 60) -> str:
    """
    格式化参数预览(简化显示)

    Good Taste: 优先显示最有信息量的字段
    """
    if not args:
        return ""

    if isinstance(args, str):
        preview = args
        if len(preview) > max_length:
            preview = preview[: max_length - 3] + "..."
        return escape(preview)

    # 优先显示的关键字段
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

    # 回退: 显示第一个字段
    if args:
        first_key = next(iter(args))
        value = str(args[first_key])
        if len(value) > max_length:
            value = value[: max_length - 3] + "..."
        return escape(f"{first_key}={value}")

    return ""


# Status Bar & Separator


def render_status_bar(model: str = "GPT-4", cost: str = "$0.00", workspace: str = "./") -> None:
    """
    渲染底部状态栏(Claude Code 风格)

    Good Taste: 用表格布局自动对齐, 消除手动空格计算
    """
    # 创建状态栏表格
    table = Table.grid(expand=True)
    table.add_column(justify="left", style=COLORS["dimmer"])
    table.add_column(justify="right", style=COLORS["dimmer"])

    left_info = f"Model: {model} | Cost: {cost}"
    right_info = f"📁 {workspace}"

    table.add_row(left_info, right_info)

    # 渲染分隔线 + 状态栏
    console.print("─" * console.width, style=COLORS["dim"])
    console.print(table)
    console.print()


def render_separator() -> None:
    """
    渲染分隔线

    Good Taste: 简洁的视觉呼吸空间
    """
    console.print("─" * console.width, style=COLORS["dim"])


# Shell Output Streaming (Claude Code Style)


def render_shell_start(command: str, cwd: str | None = None) -> None:
    """
    Timeline 风格 Shell 命令启动(扁平化)

    Good Taste: 移除 Panel, 使用垂直线连接
    """
    # Timeline 格式: │  $ command(扁平化)
    console.print(
        f"[dim]{ICONS['timeline']}[/dim]  [bold bright_cyan]{ICONS['shell']} Shell[/bold bright_cyan] [bold]$ {escape(command)}[/bold]"
    )

    if cwd and cwd != ".":
        console.print(f"[dim]{ICONS['timeline']}[/dim]     [dim]└─ {ICONS['directory']} {escape(cwd)}[/dim]")


def render_shell_output(line: str, stream: str = "stdout") -> None:
    """
    Timeline 风格 Shell 输出(扁平化)

    Good Taste: 缩进输出, 保持时间线连续
    """
    if stream == "stderr":
        console.print(f"[dim]{ICONS['timeline']}[/dim]        [{COLORS['error']}]{escape(line)}[/{COLORS['error']}]")
    else:
        console.print(f"[dim]{ICONS['timeline']}[/dim]        [dim]{escape(line)}[/dim]")


def render_shell_finished(return_code: int = 0, status: str = "completed") -> None:
    """
    Timeline 风格 Shell 完成状态(扁平化)

    Good Taste: 简洁的状态行, 不打断时间线
    """
    if status == "completed" and return_code == 0:
        console.print(
            f"[dim]{ICONS['timeline']}[/dim]     [{COLORS['success']}]{ICONS['success']} Completed (exit code: {return_code})[/{COLORS['success']}]"
        )
    elif status == "timeout":
        console.print(
            f"[dim]{ICONS['timeline']}[/dim]     [{COLORS['warning']}]{ICONS['warning']} Timed out[/{COLORS['warning']}]"
        )
    else:
        console.print(
            f"[dim]{ICONS['timeline']}[/dim]     [{COLORS['error']}]{ICONS['error']} Failed (exit code: {return_code})[/{COLORS['error']}]"
        )


# Confirmation Dialog


def render_tool_confirmation(
    tool_name: str,
    args: Any,
    description: str | None = None,
) -> None:
    """
    渲染工具确认对话框(Panel + 语法高亮)

    Good Taste: 统一的确认界面, 自动检测文件类型
    """
    console.print()

    # 标题
    title = Text()
    title.append("⚠ ", style=COLORS["warning"])
    title.append("Confirmation Required", style=f"bold {COLORS['warning']}")

    # 构建内容
    content_parts = []

    # 工具名称
    content_parts.append(Text(f"Tool: {tool_name}", style=f"bold {COLORS['accent']}"))

    # 描述
    if description:
        content_parts.append(Text(description, style=COLORS["dimmer"]))
        content_parts.append(Text())  # 空行

    # 特殊处理 write_file(显示文件内容预览)
    if tool_name == "write_file" and isinstance(args, dict) and "content" in args:
        file_path = args.get("file_path", "unknown")
        content = args.get("content", "")

        content_parts.append(Text(f"File: {file_path}", style=f"bold {COLORS['success']}"))
        content_parts.append(Text())

        # 检测文件类型
        lexer = "text"
        if "." in file_path:
            ext = file_path.split(".")[-1].lower()
            lexer = ext

        content_parts.append(Text("Content Preview:", style="bold"))
        content_parts.append(Syntax(content, lexer, theme="monokai", line_numbers=True, word_wrap=True))

        # 其他参数
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
        # 默认参数渲染
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

    # 渲染 Panel
    panel = Panel(
        Group(*content_parts),
        title=title,
        title_align="left",
        border_style=COLORS["warning"],
        padding=(1, 2),
    )

    console.print(panel)
    console.print()
