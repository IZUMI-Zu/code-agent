"""
TUI Application Main Controller
"""

import threading
import time
import uuid
from typing import TYPE_CHECKING, Any, cast

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from rich.markdown import Markdown
from rich.prompt import Prompt

from code_agent.agent.graph import agent_graph
from code_agent.utils.event_bus import drain_tool_events
from code_agent.utils.logger import logger

from .commands import SlashCommandCompleter, execute_command
from .components import (
    StreamingPanel,
    console,
    render_agent_header,
    render_separator,
    render_shell_finished,
    render_shell_output,
    render_shell_start,
    render_tool_confirmation,
    render_tool_execution,
    render_tool_result_preview,
    render_welcome,
    show_thinking,
    start_tool_spinner,
)

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig


class TUIApp:
    """Main Controller for TUI Application"""

    def __init__(self):
        self.graph = agent_graph
        self.thread_id = str(uuid.uuid4())
        self.config = cast("RunnableConfig", {"configurable": {"thread_id": self.thread_id}})
        self.session = PromptSession(completer=SlashCommandCompleter())
        self._tool_event_start_times = {}
        self._active_spinners = {}
        self._thinking_status = None
        self._tool_event_lock = threading.Lock()
        self._spinner_lock = threading.Lock()
        self._event_stop = threading.Event()
        self._event_thread = threading.Thread(target=self._tool_event_consumer, daemon=True)
        self._event_thread.start()
        # Track current streaming panel to prevent concurrent console writes
        self._current_streaming_panel = None
        self._streaming_panel_lock = threading.Lock()
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

                    if not user_input.strip():
                        continue
                    cmd_result = execute_command(user_input)
                    if cmd_result == "exit":
                        break
                    if cmd_result:
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

    def _start_thinking(self, message: str = "Processing"):
        """Start the main thinking spinner safely"""
        with self._spinner_lock:
            # Don't start thinking if we are streaming text
            with self._streaming_panel_lock:
                if self._current_streaming_panel and not self._current_streaming_panel._finished:
                    return

            if self._thinking_status:
                return
            self._thinking_status = show_thinking(message)

    def _stop_thinking(self):
        """Stop the main thinking spinner safely"""
        with self._spinner_lock:
            if self._thinking_status:
                self._thinking_status.stop()
                self._thinking_status = None

    def _handle_user_input(self, user_input: str):
        """
        Handle user input - Timeline style:
        1. Start timeline marker after user input
        2. Agent output in chat bubble style
        3. Tool calls displayed in timeline
        """
        logger.info(f"User input: {user_input}")

        console.print()
        console.print("[dim]│[/dim]")

        user_message = HumanMessage(content=user_input)
        self._start_thinking("Processing")
        input_payload = {"messages": [user_message]}

        # Streaming Panel instance
        streaming_panel = None

        try:
            while True:
                # Stream with messages mode to capture LLM tokens
                # subgraphs=True enables streaming from nested agent graphs
                current_node = None

                try:
                    for item in self.graph.stream(
                        cast("Any", input_payload),
                        config=self.config,
                        stream_mode="messages",
                        subgraphs=True,
                    ):
                        # Unpack nested tuple: (namespace, (chunk, metadata))
                        if isinstance(item, tuple) and len(item) == 2:
                            _, inner = item
                            if isinstance(inner, tuple) and len(inner) == 2:
                                chunk, metadata = inner
                            else:
                                continue  # Skip malformed items
                        else:
                            continue  # Skip non-tuple items

                        # Stop spinner on first token
                        self._stop_thinking()

                        # Extract metadata
                        node_type = metadata.get("langgraph_node", "")
                        checkpoint_ns = metadata.get("checkpoint_ns", "")

                        # Identify worker agent from checkpoint namespace
                        worker_name = None
                        if "Planner:" in checkpoint_ns:
                            worker_name = "Planner"
                        elif "Coder:" in checkpoint_ns:
                            worker_name = "Coder"
                        elif "Reviewer:" in checkpoint_ns:
                            worker_name = "Reviewer"

                        # Only show content from "model" nodes within worker agents
                        # This filters out: tools, supervisor, and other internal nodes
                        if worker_name and node_type == "model":
                            # Print worker header on first token from new worker
                            if worker_name != current_node:
                                # Finish previous stream if active
                                if streaming_panel:
                                    streaming_panel.finish()
                                    with self._streaming_panel_lock:
                                        self._current_streaming_panel = None
                                    streaming_panel = None

                                current_node = worker_name
                                render_agent_header(worker_name)

                                # Start new streaming panel for this agent
                                streaming_panel = StreamingPanel()
                                streaming_panel.start()

                            # Restart panel if it was finished by tool events
                            elif not streaming_panel or streaming_panel._finished:
                                # Add newline before starting new panel to separate from tool output
                                console.print()
                                streaming_panel = StreamingPanel()
                                streaming_panel.start()

                            # Stream token output
                            # No content filtering needed - node type already ensures clean output
                            if hasattr(chunk, "content") and chunk.content and streaming_panel:
                                # Append text instead of raw printing
                                # StreamingPanel handles the Table structure and Markdown rendering
                                streaming_panel.append(chunk.content)
                                # Track active panel for tool event coordination
                                with self._streaming_panel_lock:
                                    self._current_streaming_panel = streaming_panel

                    # Finish streaming when done
                    if streaming_panel:
                        streaming_panel.finish()
                        with self._streaming_panel_lock:
                            self._current_streaming_panel = None
                        streaming_panel = None

                    # Add final newline after streaming completes
                    if current_node:
                        console.print()

                except KeyboardInterrupt:
                    if streaming_panel:
                        streaming_panel.finish()
                        with self._streaming_panel_lock:
                            self._current_streaming_panel = None
                    # User pressed Ctrl+C during streaming
                    console.print("\n\n[yellow]⚠ Execution interrupted by user[/yellow]")
                    raise  # Re-raise to outer handler

                # Flush any remaining tool events
                self._flush_tool_events()

                console.print("[dim]│[/dim]")
                # Check for interrupts (tool confirmations)
                snapshot = self.graph.get_state(self.config)
                if snapshot.next:
                    tasks = getattr(snapshot, "tasks", [])
                    if tasks and tasks[0].interrupts:
                        interrupt_value = tasks[0].interrupts[0].value
                        decision = self._handle_interrupt(interrupt_value)
                        input_payload = Command(resume=decision)
                        self._start_thinking("Continuing")
                        continue

                break

        finally:
            self._stop_thinking()
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
                content = msg.content
                if isinstance(content, list):
                    text_parts = []
                    for part in content:
                        if isinstance(part, str):
                            text_parts.append(part)
                        elif isinstance(part, dict) and "text" in part:
                            text_parts.append(str(part["text"]))
                    content = "".join(text_parts)

                content = content.strip()
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
        """
        Process and display a single tool event
        """
        with self._streaming_panel_lock:
            if self._current_streaming_panel and not self._current_streaming_panel._finished:
                # Finish current stream to allow clean tool event rendering
                # If LLM continues streaming after tool execution, a new panel will be created
                self._current_streaming_panel.finish()
                self._current_streaming_panel = None

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
            self._start_thinking()
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

            # Show result preview with syntax highlighting
            preview = event.get("result_preview")
            if event.get("status") == "completed" and preview:
                render_tool_result_preview(preview, tool_name)

            self._start_thinking()
            return

        if event_type == "tool_rejected":
            render_tool_execution(tool_name, event.get("args"), status="rejected", worker=worker)
            self._start_thinking()
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
        choice = Prompt.ask(
            "Action",
            choices=["y", "n", "a"],
            default="y",
            show_choices=False,
            show_default=False,
        )

        if choice == "y":
            console.print("\n[green]✓ Approved[/green]")
            return {"action": "approve"}
        if choice == "n":
            reason = Prompt.ask("[dim]Reason (optional)[/dim]", default="")
            console.print("\n[red]✗ Rejected[/red]")
            return {"action": "reject", "reason": reason}
        # "a"
        console.print(f"\n[green]✓ Always allowing {tool_name}[/green]")
        return {"action": "allow_pattern", "pattern": tool_name}


def main():
    """Start TUI Application"""
    app = TUIApp()
    app.run()


if __name__ == "__main__":
    main()
