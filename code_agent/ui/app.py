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

from .components import (
    console,
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
        self.session = PromptSession()
        self._tool_event_start_times = {}
        self._active_spinners = {}
        self._tool_event_lock = threading.Lock()
        self._event_stop = threading.Event()
        self._event_thread = threading.Thread(target=self._tool_event_consumer, daemon=True)
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
        Handle user input - Timeline style:
        1. Start timeline marker after user input
        2. Agent output in chat bubble style
        3. Tool calls displayed in timeline
        """
        logger.info(f"User input: {user_input}")

        # Timeline 开始标记
        console.print()
        console.print("[dim]│[/dim]")

        user_message = HumanMessage(content=user_input)
        progress = show_thinking("Processing")
        input_payload = {"messages": [user_message]}

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
                        subgraphs=True,  # ✅ Enable subgraph token streaming
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
                        if progress:
                            progress.stop()
                            progress = None

                        # Filter streaming messages for clean UX (Good Taste)
                        # Architecture: Use metadata to understand structure, not content to guess
                        #
                        # Only show: LLM thinking from worker agents (Planner/Coder/Reviewer)
                        # Skip: tool nodes, supervisor, malformed messages

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
                                if current_node:  # Add spacing between workers
                                    console.print()
                                    console.print("[dim]│[/dim]")
                                current_node = worker_name

                                # Agent 标识 (Timeline 风格, 聊天气泡)
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
                                agent_color = agent_colors.get(worker_name, "green")

                                console.print()
                                console.print(f"[bold {agent_color}]{icon} {worker_name}:[/bold {agent_color}]")

                            # Stream token output (chat bubble style, 左边框)
                            # No content filtering needed - node type already ensures clean output
                            if hasattr(chunk, "content") and chunk.content:
                                # 为每个 token 添加左边框 (如果是新行)
                                for char in chunk.content:
                                    console.print(char, end="", markup=False)

                    # Add final newline after streaming completes
                    if current_node:
                        console.print()

                except KeyboardInterrupt:
                    # User pressed Ctrl+C during streaming
                    console.print("\n\n[yellow]⚠ Execution interrupted by user[/yellow]")
                    raise  # Re-raise to outer handler

                # Flush any remaining tool events
                self._flush_tool_events()

                # Timeline 结束标记
                console.print("[dim]│[/dim]")

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

            # Show result preview with syntax highlighting
            preview = event.get("result_preview")
            if event.get("status") == "completed" and preview:
                render_tool_result_preview(preview, tool_name)
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
    import asyncio

    # Initialize MCP tools before starting the app
    from code_agent.agent.graph import initialize_mcp_tools

    try:
        logger.info("Initializing MCP tools...")
        asyncio.run(initialize_mcp_tools())
        logger.info("MCP tools initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize MCP tools: {e}")
        logger.warning("Continuing with built-in tools only")

    app = TUIApp()
    app.run()


if __name__ == "__main__":
    main()
