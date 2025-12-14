"""
Command system with slash command completion.

Architecture:
  - Data-driven command registry (no if/else chains)
  - Auto-generated alias map
  - prompt_toolkit integration for completion
"""

from collections.abc import Callable
from dataclasses import dataclass

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from code_agent.tools.registry import get_registry

from .components import console, render_welcome


@dataclass
class Command:
    """Command definition"""

    name: str
    description: str
    handler: Callable
    aliases: list[str] | None = None


# Command Handlers


def _cmd_help() -> str:
    """Show available commands"""
    console.print("\n[bold cyan]Available Commands:[/bold cyan]\n")

    for cmd_name, cmd in COMMANDS.items():
        if cmd_name in _ALIAS_MAP:  # Skip aliases
            continue

        aliases = f" (aliases: {', '.join(cmd.aliases)})" if cmd.aliases else ""
        console.print(f"  [bold]/{cmd_name}[/bold]{aliases}")
        console.print(f"    [dim]{cmd.description}[/dim]\n")

    console.print("[dim]Tip: Type '/' to see completions[/dim]\n")
    return "help"


def _cmd_clear() -> str:
    """Clear screen and show welcome"""
    console.clear()
    render_welcome()
    return "clear"


def _cmd_exit() -> str:
    """Exit the application"""
    console.print("\n[yellow]Goodbye! 👋[/yellow]\n")
    return "exit"


def _cmd_tools() -> str:
    """List all available tools"""
    console.print("\n[bold cyan]Available Tools:[/bold cyan]\n")

    registry = get_registry()
    tools = registry.get_all_tools_with_mcp()

    # Group tools by category (heuristic based on name patterns)
    categories = {
        "File I/O": [],
        "Code Search": [],
        "Edit": [],
        "Filesystem": [],
        "Shell": [],
        "Planning": [],
        "Sub-Agent": [],
        "External": [],
        "MCP": [],
    }

    for tool in tools:
        name = tool.name if hasattr(tool, "name") else str(tool)
        desc = tool.description if hasattr(tool, "description") else "No description"

        # Categorize
        if any(x in name for x in ["read", "write", "list"]):
            categories["File I/O"].append((name, desc))
        elif "grep" in name or "search" in name.lower():
            categories["Code Search"].append((name, desc))
        elif any(x in name for x in ["replace", "insert", "delete", "append"]):
            categories["Edit"].append((name, desc))
        elif any(x in name for x in ["copy", "move", "create", "path"]):
            categories["Filesystem"].append((name, desc))
        elif "shell" in name or "process" in name:
            categories["Shell"].append((name, desc))
        elif "plan" in name:
            categories["Planning"].append((name, desc))
        elif hasattr(tool, "__class__") and "MCP" in tool.__class__.__name__:
            categories["MCP"].append((name, desc))
        else:
            categories["External"].append((name, desc))

    # Print by category
    for category, tool_list in categories.items():
        if not tool_list:
            continue

        console.print(f"[bold magenta]{category}:[/bold magenta]")
        for name, desc in sorted(tool_list):
            # Truncate long descriptions
            desc_short = desc[:80] + "..." if len(desc) > 80 else desc
            console.print(f"  [bold]{name}[/bold]")
            console.print(f"    [dim]{desc_short}[/dim]")
        console.print()

    console.print(f"[dim]Total: {len(tools)} tools[/dim]\n")
    return "tools"


# Command Registry

COMMANDS = {
    "help": Command(
        name="help",
        description="Show this help message",
        handler=_cmd_help,
        aliases=["h", "?"],
    ),
    "clear": Command(
        name="clear",
        description="Clear screen",
        handler=_cmd_clear,
        aliases=["cls"],
    ),
    "exit": Command(
        name="exit",
        description="Exit the application",
        handler=_cmd_exit,
        aliases=["quit", "q"],
    ),
    "tools": Command(
        name="tools",
        description="List all available tools",
        handler=_cmd_tools,
        aliases=["t"],
    ),
}

# Auto-generated alias map
_ALIAS_MAP = {}
for cmd_name, cmd in COMMANDS.items():
    if cmd.aliases:
        for alias in cmd.aliases:
            _ALIAS_MAP[alias] = cmd_name


# Command Execution


def execute_command(user_input: str) -> str | None:
    """
    Execute a command if input matches.

    Args:
        user_input: Raw user input (may have "/" prefix)

    Returns:
        Command name if executed, None otherwise
    """
    # Normalize: strip, lowercase, remove "/"
    normalized = user_input.strip().lower()
    if normalized.startswith("/"):
        normalized = normalized[1:]

    # Resolve alias
    cmd_name = _ALIAS_MAP.get(normalized, normalized)

    # Execute
    cmd = COMMANDS.get(cmd_name)
    if cmd:
        return cmd.handler()

    return None


def get_all_commands() -> list[tuple[str, str]]:
    """Get all commands for completion (includes aliases)"""
    result = []
    for cmd in COMMANDS.values():
        result.append((cmd.name, cmd.description))
        if cmd.aliases:
            for alias in cmd.aliases:
                result.append((alias, f"{cmd.description} (alias)"))
    return result


# Slash Command Completer


class SlashCommandCompleter(Completer):
    """
    Completer for slash commands.
    Triggers only when input starts with "/".
    """

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor

        # Only trigger on "/"
        if not text.startswith("/"):
            return

        # Match prefix after "/"
        prefix = text[1:].lower()

        for cmd_name, description in get_all_commands():
            if cmd_name.lower().startswith(prefix):
                yield Completion(
                    text=f"/{cmd_name}",
                    start_position=-len(text),
                    display=f"/{cmd_name}",
                    display_meta=description,
                )
