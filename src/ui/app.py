"""
═══════════════════════════════════════════════════════════════
TUI Application Main Controller
═══════════════════════════════════════════════════════════════
Design: Claude Code style
  - Tool calls displayed in real-time during execution
  - Agent's final response displayed after all tools complete
"""

import threading
import time
import uuid

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from rich.markdown import Markdown
from rich.prompt import Prompt

from ..agent.graph import agent_graph
from ..utils.event_bus import drain_tool_events
from ..utils.logger import logger
from .components import (
    console,
    render_separator,
    render_shell_finished,
    render_shell_output,
    render_shell_start,
    render_tool_confirmation,
    render_tool_execution,
    render_welcome,
    show_thinking,
    start_tool_spinner,
)


class TUIApp:
    """Main Controller for TUI Application"""

    def __init__(self):
        self.graph = agent_graph
        self.thread_id = str(uuid.uuid4())
        self.config = {"configurable": {"thread_id": self.thread_id}}
        self.session = PromptSession()
        self._tool_event_start_times = {}
        self._active_spinners = {}
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
            event.current_buffer.validate_and_handle()

        @kb.add("escape", "enter")
        def _(event):
            event.current_buffer.insert_text("\n")

        return kb

    def run(self):
        """Start application main loop"""
        render_welcome()
        kb = self._create_key_bindings()

        try:
            while True:
                try:
                    console.print()
                    user_input = self.session.prompt(
                        HTML("<b><cyan>You</cyan></b>: "),
                        multiline=True,
                        key_bindings=kb,
                        bottom_toolbar=HTML(
                            " <b>[Enter]</b> to submit | <b>[Alt+Enter]</b> for newline | <b>[Ctrl+D]</b> to exit "
                        ),
                    )

                    if user_input.lower().strip() in ["exit", "quit", "q"]:
                        console.print("\n[yellow]Goodbye! 👋[/yellow]\n")
                        break

                    if user_input.lower().strip() == "clear":
                        console.clear()
                        render_welcome()
                        continue

                    if not user_input.strip():
                        continue

                    self._handle_user_input(user_input)
                    render_separator()

                except KeyboardInterrupt:
                    console.print("\n[yellow]Goodbye! 👋[/yellow]\n")
                    break
                except EOFError:
                    console.print("\n[yellow]Goodbye! 👋[/yellow]\n")
                    break
                except Exception as e:
                    console.print(f"\n[red]Error: {e}[/red]\n")
                    logger.exception("An unexpected error occurred")
        finally:
            self._shutdown_event_thread()

    def _handle_user_input(self, user_input: str):
        """
        Handle user input - Claude Code style:
        1. Show tool calls in real-time
        2. Show agent's final response after completion
        """
        logger.info(f"User input: {user_input}")

        user_message = HumanMessage(content=user_input)
        progress = show_thinking("Processing")
        input_payload = {"messages": [user_message]}

        try:
            while True:
                # Run graph and collect final state
                # Tool events are displayed in real-time via background thread
                final_state = None
                for state in self.graph.stream(
                    input_payload,
                    config=self.config,
                    stream_mode="values",
                ):
                    final_state = state

                # Stop spinner
                if progress:
                    progress.stop()
                    progress = None

                # Flush any remaining tool events
                self._flush_tool_events()

                # Check for interrupts (tool confirmations)
                snapshot = self.graph.get_state(self.config)
                if snapshot.next:
                    tasks = getattr(snapshot, "tasks", [])
                    if tasks and tasks[0].interrupts:
                        interrupt_value = tasks[0].interrupts[0].value
                        decision = self._handle_interrupt(interrupt_value)
                        input_payload = Command(resume=decision)
                        progress = show_thinking("Continuing")
                        continue

                # Display final agent response
                if final_state:
                    self._display_final_response(final_state)

                break

        finally:
            if progress:
                progress.stop()
            self._flush_tool_events()

    def _display_final_response(self, state):
        """Display the agent's final response from state"""
        messages = state.get("messages", [])
        if not messages:
            return

        # Find the last AI message with content
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                # Skip if it's just tool call info
                content = msg.content.strip()
                if content and not content.startswith("Tool call"):
                    console.print()
                    console.print("[bold green]Assistant:[/bold green]")
                    console.print(Markdown(content))
                    console.print()
                    break

    def _tool_event_consumer(self):
        """Background thread for real-time tool event display"""
        while not self._event_stop.is_set():
            events = drain_tool_events()
            if not events:
                time.sleep(0.05)
                continue

            for event in events:
                self._process_tool_event(event)

        # Process remaining events on shutdown
        for event in drain_tool_events():
            self._process_tool_event(event)

    def _process_tool_event(self, event):
        """Process and display a single tool event"""
        event_type = event.get("event_type")
        tool_name = event.get("tool", "Unknown")
        worker = event.get("worker")

        # Shell events
        if event_type == "shell_started":
            self._stop_all_spinners()
            render_shell_start(event.get("command", ""), event.get("cwd", "."))
            return

        if event_type == "shell_output":
            render_shell_output(event.get("line", ""), event.get("stream", "stdout"))
            return

        if event_type == "shell_finished":
            render_shell_finished(event.get("return_code", 0), event.get("status", "completed"))
            return

        # Tool started - show spinner
        if event_type == "tool_started":
            call_id = event.get("call_id")
            if call_id:
                with self._tool_event_lock:
                    self._tool_event_start_times[call_id] = event.get("timestamp", time.time())
                spinner = start_tool_spinner(tool_name, event.get("args"))
                self._active_spinners[call_id] = spinner
            return

        # Tool finished - show result
        if event_type == "tool_finished":
            call_id = event.get("call_id")
            duration = event.get("duration")

            # Stop spinner
            if call_id and call_id in self._active_spinners:
                self._active_spinners.pop(call_id).stop()

            # Calculate duration if not provided
            if duration is None and call_id:
                with self._tool_event_lock:
                    start_ts = self._tool_event_start_times.pop(call_id, None)
                if start_ts:
                    duration = time.time() - start_ts

            # Render tool execution result
            render_tool_execution(
                tool_name,
                event.get("args"),
                status=event.get("status", "completed"),
                duration=duration,
                error=event.get("error"),
                worker=worker,
            )

            # Show result preview
            preview = event.get("result_preview")
            if event.get("status") == "completed" and preview:
                from rich.markup import escape
                for line in preview.split("\n")[:3]:  # Limit to 3 lines
                    console.print(f"  [dim]{escape(line)}[/dim]")
            return

        if event_type == "tool_rejected":
            render_tool_execution(tool_name, event.get("args"), status="rejected", worker=worker)
            return

    def _stop_all_spinners(self):
        """Stop all active spinners"""
        for spinner in self._active_spinners.values():
            spinner.stop()
        self._active_spinners.clear()

    def _flush_tool_events(self, timeout: float = 0.2):
        """Flush pending tool events"""
        self._stop_all_spinners()
        deadline = time.time() + timeout
        while time.time() < deadline:
            events = drain_tool_events()
            if not events:
                time.sleep(0.02)
                if not drain_tool_events():
                    break
            for event in events:
                self._process_tool_event(event)

    def _shutdown_event_thread(self):
        """Shutdown background event thread"""
        self._event_stop.set()
        if self._event_thread.is_alive():
            self._event_thread.join(timeout=1.0)

    def _handle_interrupt(self, interrupt_value):
        """Handle tool confirmation interrupt"""
        tool_name = interrupt_value.get("tool")
        args = interrupt_value.get("args")
        description = interrupt_value.get("description")

        self._flush_tool_events()
        render_tool_confirmation(tool_name, args, description)

        console.print("[dim]y: Approve | n: Reject | a: Always Allow[/dim]")
        choice = Prompt.ask("Action", choices=["y", "n", "a"], default="y", show_choices=False, show_default=False)

        if choice == "y":
            console.print(f"\n[green]✓ Approved[/green]")
            return {"action": "approve"}
        elif choice == "n":
            reason = Prompt.ask("[dim]Reason (optional)[/dim]", default="")
            console.print("\n[red]❌ Rejected[/red]")
            return {"action": "reject", "reason": reason}
        else:  # "a"
            console.print(f"\n[green]✓ Always allowing {tool_name}[/green]")
            return {"action": "allow_pattern", "pattern": tool_name}


def main():
    """Start TUI Application"""
    app = TUIApp()
    app.run()


if __name__ == "__main__":
    main()
