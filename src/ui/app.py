"""
═══════════════════════════════════════════════════════════════
TUI Application Main Controller
═══════════════════════════════════════════════════════════════
Responsibilities:
  - Manage user input loop
  - Call Agent to execute tasks
  - Render execution results
"""

import threading
import time
import uuid

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style as PromptStyle
from rich.markup import escape
from rich.prompt import Prompt

from ..agent.graph import agent_graph
from ..utils.event_bus import drain_tool_events
from ..utils.logger import logger
from .components import (
    console,
    render_message,
    render_separator,
    render_tool_confirmation,
    render_tool_execution,
    render_welcome,
    show_thinking,
    start_tool_spinner,
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
        self._tool_event_start_times = {}
        self._active_spinners = {}  # call_id -> Status
        self._tool_event_lock = threading.Lock()
        self._event_stop = threading.Event()
        self._event_thread = threading.Thread(
            target=self._tool_event_consumer, daemon=True
        )
        self._event_thread.start()
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

        try:
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
        finally:
            self._shutdown_event_thread()

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

        # Display thinking indicator
        progress = show_thinking("Analyzing request")

        input_payload = {"messages": [user_message]}

        try:
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

                                    continue

                                # Tool Message - show completion with timing
                                elif isinstance(msg, ToolMessage):
                                    continue

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

    def _tool_event_consumer(self):
        while True:
            events = drain_tool_events()
            if not events:
                if self._event_stop.is_set():
                    break
                time.sleep(0.05)
                continue

            for event in events:
                self._process_tool_event(event)

            try:
                app = getattr(self.session, "app", None)
                if app is not None:
                    app.invalidate()
            except Exception:
                pass

        # Flush any remaining events before exit
        remaining = drain_tool_events()
        for event in remaining:
            self._process_tool_event(event)

    def _process_tool_event(self, event):
        event_type = event.get("event_type")
        tool_name = event.get("tool", "Unknown")
        worker = event.get("worker")

        if event_type == "tool_started":
            call_id = event.get("call_id")
            timestamp = event.get("timestamp", time.time())
            if call_id:
                with self._tool_event_lock:
                    self._tool_event_start_times[call_id] = timestamp

            # Start spinner instead of printing static line
            spinner = start_tool_spinner(tool_name, event.get("args"))
            if call_id:
                self._active_spinners[call_id] = spinner
            return

        if event_type == "tool_finished":
            call_id = event.get("call_id")
            duration = event.get("duration")
            start_ts = None
            if call_id:
                with self._tool_event_lock:
                    start_ts = self._tool_event_start_times.pop(call_id, None)

            # Stop spinner
            if call_id and call_id in self._active_spinners:
                spinner = self._active_spinners.pop(call_id)
                spinner.stop()

            if duration is None and start_ts is not None:
                duration = max(0.0, event.get("timestamp", time.time()) - start_ts)
            status = event.get("status", "completed")
            render_tool_execution(
                tool_name,
                event.get("args"),  # Pass args to render_tool_execution for preview
                status=status,
                duration=duration,
                error=event.get("error"),
                worker=worker,
            )
            preview = event.get("result_preview")
            if status == "completed" and preview:
                console.print(f"  [dim]{escape(preview)}[/dim]")
            return

        if event_type == "tool_rejected":
            # Stop spinner if exists (though rejected usually happens before start,
            # but if we had a pre-check spinner, we'd stop it here)
            # In current flow, rejection happens before tool_started usually,
            # but if we change flow, good to be safe.
            render_tool_execution(
                tool_name, event.get("args"), status="rejected", worker=worker
            )
            return

    def _shutdown_event_thread(self):
        self._event_stop.set()
        if self._event_thread.is_alive():
            self._event_thread.join(timeout=1.0)

    def _handle_interrupt(self, interrupt_value):
        """Handle tool execution interrupt"""
        tool_name = interrupt_value.get("tool")
        args = interrupt_value.get("args")
        description = interrupt_value.get("description")

        render_tool_confirmation(tool_name, args, description)

        console.print("[dim]y: Approve | n: Reject | a: Always Allow (Workspace)[/dim]")
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
            reason = Prompt.ask("[dim]Reason (optional)[/dim]", default="")
            console.print(f"\n[red]❌ Rejected.[/red]")
            return {"action": "reject", "reason": reason}
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
