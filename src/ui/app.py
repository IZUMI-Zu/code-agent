"""
═══════════════════════════════════════════════════════════════
TUI Application Main Controller
═══════════════════════════════════════════════════════════════
Responsibilities:
  - Manage user input loop
  - Call Agent to execute tasks
  - Render execution results with streaming support

Design Philosophy (Best Practice from LangGraph docs):
  - Use stream_mode="messages" for token-level LLM streaming
  - Sync stream() is the recommended approach
  - LangChain auto-enables streaming for model.invoke() calls
"""

import threading
import time
import uuid

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from langgraph.types import Command
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
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
    StreamingText,
)


class TUIApp:
    """Main Controller for TUI Application"""

    def __init__(self):
        self.graph = agent_graph
        self.thread_id = str(uuid.uuid4())
        self.config = {"configurable": {"thread_id": self.thread_id}}
        self.state = {"messages": [], "current_task": "", "is_finished": False}
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
                        logger.info("Application exit requested by user")
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
        Handle user input with token-level streaming

        Best Practice (from LangGraph docs):
          - Use stream_mode="messages" for LLM token streaming
          - Returns tuple (message_chunk, metadata)
          - LangChain auto-enables streaming for model.invoke() in nodes
        """
        logger.info(f"User input: {user_input}")

        user_message = HumanMessage(content=user_input)
        self.state["messages"].append(user_message)

        progress = show_thinking("Analyzing request")
        input_payload = {"messages": [user_message]}

        # Streaming state
        streaming_text = None
        current_node = None
        
        # Worker name mapping for display
        worker_labels = {
            "Planner": "[magenta]Planner[/magenta]",
            "Coder": "[blue]Coder[/blue]",
            "Reviewer": "[yellow]Reviewer[/yellow]",
        }

        try:
            while True:
                # Use stream_mode=["messages", "updates"] for both token streaming and state updates
                # subgraphs=True to capture tokens from worker agents (which are subgraphs)
                for event in self.graph.stream(
                    input_payload, 
                    config=self.config, 
                    stream_mode=["messages", "updates"],
                    subgraphs=True,
                ):
                    # Process any pending tool events first
                    self._process_pending_events()
                    # Handle different stream formats
                    # With multiple stream modes and subgraphs, format is:
                    # (namespace_tuple, (stream_mode, data))
                    if not isinstance(event, tuple) or len(event) != 2:
                        continue
                    
                    namespace, inner = event
                    
                    # Handle updates mode (state changes)
                    if isinstance(inner, tuple) and len(inner) == 2:
                        stream_mode, data = inner
                        if stream_mode == "updates":
                            # State update - just continue, tool events handled via event bus
                            continue
                        elif stream_mode == "messages":
                            chunk, metadata = data if isinstance(data, tuple) else (data, {})
                        else:
                            continue
                    else:
                        continue
                    
                    metadata = metadata if isinstance(metadata, dict) else {}
                    node_name = metadata.get("langgraph_node", "")

                    # Stop thinking indicator on first output
                    if progress:
                        progress.stop()
                        progress = None

                    # Handle AIMessageChunk (streaming tokens)
                    if isinstance(chunk, AIMessageChunk):
                        content = chunk.content if hasattr(chunk, "content") else ""

                        # Skip empty content or tool call chunks
                        if not content:
                            continue

                        # Check if we're starting a new streaming block
                        if streaming_text is None:
                            # Flush any pending tool events before starting text output
                            self._flush_tool_events()
                            # Show worker label if available
                            label = worker_labels.get(node_name, "[green]Assistant[/green]")
                            console.print(f"\n[bold]{label}:[/bold]")
                            streaming_text = StreamingText()
                            streaming_text.start()
                            current_node = node_name

                        # If node changed, finish current stream and start new
                        elif current_node != node_name:
                            streaming_text.finish()
                            # Flush events between different workers
                            self._flush_tool_events()
                            label = worker_labels.get(node_name, "[green]Assistant[/green]")
                            console.print(f"\n[bold]{label}:[/bold]")
                            streaming_text = StreamingText()
                            streaming_text.start()
                            current_node = node_name

                        streaming_text.append(content)

                    # Handle complete AIMessage (usually after streaming ends)
                    elif isinstance(chunk, AIMessage):
                        if streaming_text:
                            streaming_text.finish()
                            streaming_text = None
                            current_node = None
                            # Resume background event processing after text completes
                            self._resume_tool_events()

                # Finish streaming if still active
                if streaming_text:
                    streaming_text.finish()
                    streaming_text = None
                    self._resume_tool_events()

                # Check for interrupts (tool confirmations)
                snapshot = self.graph.get_state(self.config)
                if snapshot.next:
                    tasks = getattr(snapshot, "tasks", [])
                    if tasks and tasks[0].interrupts:
                        # Stop progress spinner before showing confirmation
                        if progress:
                            progress.stop()
                            progress = None
                        
                        # Flush any pending tool events
                        self._flush_tool_events()
                        
                        interrupt_value = tasks[0].interrupts[0].value
                        decision = self._handle_interrupt(interrupt_value)
                        input_payload = Command(resume=decision)
                        progress = show_thinking("Continuing")
                        continue

                break

        finally:
            if progress:
                progress.stop()
            if streaming_text:
                streaming_text.finish()
            # Always ensure event processing is resumed
            self._resume_tool_events()

    def _tool_event_consumer(self):
        """Background thread for tool event processing"""
        while True:
            if self._event_stop.is_set():
                break
                
            events = drain_tool_events()
            if not events:
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

        remaining = drain_tool_events()
        for event in remaining:
            self._process_tool_event(event)

    def _process_tool_event(self, event):
        """Process a single tool event"""
        event_type = event.get("event_type")
        tool_name = event.get("tool", "Unknown")
        worker = event.get("worker")

        # Shell streaming events
        if event_type == "shell_started":
            command = event.get("command", "")
            cwd = event.get("cwd", ".")
            for call_id, spinner in list(self._active_spinners.items()):
                spinner.stop()
            self._active_spinners.clear()
            render_shell_start(command, cwd)
            return

        if event_type == "shell_output":
            line = event.get("line", "")
            stream = event.get("stream", "stdout")
            render_shell_output(line, stream)
            return

        if event_type == "shell_finished":
            return_code = event.get("return_code", 0)
            status = event.get("status", "completed")
            render_shell_finished(return_code, status)
            return

        # Regular tool events
        if event_type == "tool_started":
            call_id = event.get("call_id")
            timestamp = event.get("timestamp", time.time())
            if call_id:
                with self._tool_event_lock:
                    self._tool_event_start_times[call_id] = timestamp

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

            if call_id and call_id in self._active_spinners:
                spinner = self._active_spinners.pop(call_id)
                spinner.stop()

            if duration is None and start_ts is not None:
                duration = max(0.0, event.get("timestamp", time.time()) - start_ts)
            status = event.get("status", "completed")
            render_tool_execution(
                tool_name,
                event.get("args"),
                status=status,
                duration=duration,
                error=event.get("error"),
                worker=worker,
            )
            preview = event.get("result_preview")
            if status == "completed" and preview:
                from rich.markup import escape
                lines = preview.split("\n")
                for line in lines:
                    console.print(f"  [dim]{escape(line)}[/dim]")
            return

        if event_type == "tool_rejected":
            render_tool_execution(
                tool_name, event.get("args"), status="rejected", worker=worker
            )
            return

    def _process_pending_events(self):
        """Process any pending tool events without blocking."""
        events = drain_tool_events()
        for event in events:
            self._process_tool_event(event)

    def _flush_tool_events(self, timeout: float = 0.3):
        """
        Flush all pending tool events in main thread before AI text output.
        This ensures tool output is displayed before AI text starts streaming.
        """
        # Stop any active spinners first
        for call_id, spinner in list(self._active_spinners.items()):
            spinner.stop()
        self._active_spinners.clear()
        
        # Process all pending events in main thread
        deadline = time.time() + timeout
        while time.time() < deadline:
            events = drain_tool_events()
            if not events:
                # Small wait to catch any late-arriving events
                time.sleep(0.03)
                events = drain_tool_events()
                if not events:
                    break
            for event in events:
                self._process_tool_event(event)
    
    def _resume_tool_events(self):
        """Resume background tool event processing (no-op now, kept for compatibility)"""
        pass

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
            console.print(f"\n[green]✓ Approved. Executing {tool_name}...[/green]")
            return {"action": "approve"}
        elif choice == "n":
            reason = Prompt.ask("[dim]Reason (optional)[/dim]", default="")
            console.print("\n[red]❌ Rejected.[/red]")
            return {"action": "reject", "reason": reason}
        elif choice == "a":
            console.print(
                f"\n[green]✓ Always allowing {tool_name} for this session...[/green]"
            )
            return {"action": "allow_pattern", "pattern": tool_name}


def main():
    """Start TUI Application"""
    app = TUIApp()
    app.run()


if __name__ == "__main__":
    main()
