"""
═══════════════════════════════════════════════════════════════
TUI Application Main Controller
═══════════════════════════════════════════════════════════════
Responsibilities:
  - Manage user input loop
  - Call Agent to execute tasks
  - Render execution results
"""

import uuid

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style as PromptStyle
from rich.prompt import Prompt

from ..agent.graph import agent_graph
from ..utils.logger import logger
from .components import (
    console,
    render_message,
    render_separator,
    render_tool_confirmation,
    render_tool_execution,
    render_welcome,
    show_thinking,
)

# ═══════════════════════════════════════════════════════════════
# TUI Application Class
# ═══════════════════════════════════════════════════════════════


class TUIApp:
    """
    Main Controller for TUI Application

    Good Taste:
      - Loop logic is simple, no deep nesting
      - State management delegated to LangGraph, UI only responsible for display
    """

    def __init__(self):
        self.graph = agent_graph
        self.thread_id = str(uuid.uuid4())
        self.config = {"configurable": {"thread_id": self.thread_id}}
        self.state = {"messages": [], "current_task": "", "is_finished": False}
        self.session = PromptSession()  # Initialize prompt_toolkit session
        logger.info(f"TUI Application initialized with thread_id: {self.thread_id}")

    def _create_key_bindings(self):
        """Create custom key bindings"""
        kb = KeyBindings()

        @kb.add("enter")
        def _(event):
            """Enter to submit"""
            event.current_buffer.validate_and_handle()

        @kb.add("escape", "enter")
        def _(event):
            """Alt+Enter (Esc+Enter) to insert newline"""
            event.current_buffer.insert_text("\n")

        return kb

    def run(self):
        """Start application main loop"""
        render_welcome()
        kb = self._create_key_bindings()

        while True:
            try:
                # Get user input using prompt_toolkit for multiline support
                console.print()  # Add some spacing
                user_input = self.session.prompt(
                    HTML("<b><cyan>You</cyan></b>: "),
                    multiline=True,
                    key_bindings=kb,
                    bottom_toolbar=HTML(
                        " <b>[Enter]</b> to submit | <b>[Alt+Enter]</b> for newline | <b>[Ctrl+D]</b> to exit "
                    ),
                )

                # Exit command
                if user_input.lower().strip() in ["exit", "quit", "q"]:
                    console.print("\n[yellow]Goodbye! 👋[/yellow]\n")
                    logger.info("Application exit requested by user")
                    break

                # Clear screen command
                if user_input.lower().strip() == "clear":
                    console.clear()
                    render_welcome()
                    continue

                # Skip empty input
                if not user_input.strip():
                    continue

                # Handle user request
                self._handle_user_input(user_input)

                render_separator()

            except KeyboardInterrupt:
                # Handle Ctrl+C
                console.print("\n[yellow]Goodbye! 👋[/yellow]\n")
                break
            except EOFError:
                # Handle Ctrl+D
                console.print("\n[yellow]Goodbye! 👋[/yellow]\n")
                break
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]\n")
                logger.exception("An unexpected error occurred")

    def _handle_user_input(self, user_input: str):
        """
        Handle user input with real-time tool execution tracking

        Design Philosophy:
          - Stream mode "updates" for fine-grained execution visibility
          - Track tool execution time for performance awareness
          - Map tool_call_id -> tool_name for accurate reporting
          - User sees every step as it happens
        """
        logger.info(f"User input: {user_input}")

        # Add user message to state
        user_message = HumanMessage(content=user_input)
        self.state["messages"].append(user_message)

        # Note: User message already displayed by prompt_toolkit, no need to render again

        # Track tool execution
        tool_call_map = {}  # tool_call_id -> (tool_name, start_time)

        # Display thinking indicator
        progress = show_thinking("Analyzing request")

        input_payload = {"messages": [user_message]}

        try:
            import time

            while True:
                # Execute Agent with stream_mode="updates" for step-by-step visibility
                for chunk in self.graph.stream(
                    input_payload, config=self.config, stream_mode="updates"
                ):
                    # chunk is dict: {node_name: node_output}
                    for node_name, node_output in chunk.items():
                        logger.debug(f"Node {node_name} output: {node_output}")

                        # Stop thinking indicator on first real output
                        if progress and node_name != "__start__":
                            progress.stop()
                            progress = None

                        # Process messages from this node
                        if isinstance(node_output, dict) and "messages" in node_output:
                            new_messages = node_output["messages"]

                            for msg in new_messages:
                                # AI Message with tool calls - track and display
                                if (
                                    isinstance(msg, AIMessage)
                                    and hasattr(msg, "tool_calls")
                                    and msg.tool_calls
                                ):
                                    # First, render any reasoning/explanation text
                                    if hasattr(msg, "content") and msg.content.strip():
                                        render_message(msg)

                                    # Then display tool calls
                                    for tool_call in msg.tool_calls:
                                        tool_call_id = tool_call.get("id")
                                        tool_name = tool_call.get("name", "Unknown")
                                        tool_args = tool_call.get("args", {})

                                        # Track start time
                                        start_time = time.time()
                                        tool_call_map[tool_call_id] = (
                                            tool_name,
                                            start_time,
                                        )

                                        # Display tool execution start
                                        render_tool_execution(
                                            tool_name, tool_args, status="running"
                                        )

                                # Tool Message - show completion with timing
                                elif isinstance(msg, ToolMessage):
                                    tool_call_id = msg.tool_call_id
                                    tool_name = "Unknown"
                                    duration = None

                                    # Lookup tool name and calculate duration
                                    if tool_call_id in tool_call_map:
                                        tool_name, start_time = tool_call_map[
                                            tool_call_id
                                        ]
                                        duration = time.time() - start_time

                                    # Determine status
                                    is_error = (
                                        "error" in msg.content.lower()
                                        or "failed" in msg.content.lower()
                                        or (
                                            hasattr(msg, "status")
                                            and msg.status == "error"
                                        )
                                    )
                                    status = "failed" if is_error else "completed"

                                    # Extract error message if present
                                    error_msg = None
                                    if is_error:
                                        error_msg = msg.content[:200]

                                    # Display completion
                                    render_tool_execution(
                                        tool_name,
                                        status=status,
                                        duration=duration,
                                        error=error_msg,
                                    )

                                # Regular AI message - display
                                else:
                                    render_message(msg)

                            # Update local state
                            self.state["messages"].extend(new_messages)

                # Check for interrupts
                snapshot = self.graph.get_state(self.config)
                if snapshot.next:
                    tasks = getattr(snapshot, "tasks", [])
                    if tasks and tasks[0].interrupts:
                        interrupt_value = tasks[0].interrupts[0].value

                        if progress:
                            progress.stop()
                            progress = None

                        # Ask user
                        decision = self._handle_interrupt(interrupt_value)

                        # Resume
                        input_payload = Command(resume=decision)

                        # Restart thinking
                        progress = show_thinking("Executing tool")
                        continue

                break

        finally:
            # Ensure progress bar stops
            if progress:
                progress.stop()

    def _handle_interrupt(self, interrupt_value):
        """Handle tool execution interrupt"""
        tool_name = interrupt_value.get("tool")
        args = interrupt_value.get("args")
        description = interrupt_value.get("description")

        render_tool_confirmation(tool_name, args, description)

        console.print("[dim]y: Approve | n: Reject | a: Always Allow (Session)[/dim]")
        choice = Prompt.ask(
            "Action",
            choices=["y", "n", "a"],
            default="y",
            show_choices=False,
            show_default=False,
        )

        if choice == "y":
            console.print(f"\n[green]✅ Approved. Executing {tool_name}...[/green]")
            return {"action": "approve"}
        elif choice == "n":
            console.print(f"\n[red]❌ Rejected.[/red]")
            return {"action": "reject"}
        elif choice == "a":
            console.print(
                f"\n[green]✅ Always allowing {tool_name} for this session...[/green]"
            )
            return {"action": "allow_pattern", "pattern": tool_name}


# ═══════════════════════════════════════════════════════════════
# Application Entry Point
# ═══════════════════════════════════════════════════════════════


def main():
    """Start TUI Application"""
    app = TUIApp()
    app.run()


if __name__ == "__main__":
    main()
