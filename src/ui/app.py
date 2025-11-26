"""
═══════════════════════════════════════════════════════════════
TUI Application Main Controller
═══════════════════════════════════════════════════════════════
Responsibilities:
  - Manage user input loop
  - Call Agent to execute tasks
  - Render execution results
"""

from langchain_core.messages import HumanMessage
from rich.prompt import Prompt

from ..agent.graph import agent_graph
from ..utils.logger import logger
from .components import (
    console,
    render_message,
    render_separator,
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
        self.state = {"messages": [], "current_task": "", "is_finished": False}
        logger.info("TUI Application initialized")

    def run(self):
        """Start application main loop"""
        render_welcome()

        while True:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")

                # Exit command
                if user_input.lower() in ["exit", "quit", "q"]:
                    console.print("\n[yellow]Goodbye! 👋[/yellow]\n")
                    logger.info("Application exit requested by user")
                    break

                # Skip empty input
                if not user_input.strip():
                    continue

                # Handle user request
                self._handle_user_input(user_input)

                render_separator()

            except KeyboardInterrupt:
                console.print("\n\n[yellow]Interrupted[/yellow]\n")
                logger.warning("Application interrupted by user")
                break
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]\n")
                logger.exception("An unexpected error occurred")

    def _handle_user_input(self, user_input: str):
        """Handle user input (Internal method)"""
        logger.info(f"User input: {user_input}")

        # Add user message to state
        user_message = HumanMessage(content=user_input)
        self.state["messages"].append(user_message)

        # Display user message
        render_message(user_message)

        # Display thinking indicator
        progress = show_thinking()

        try:
            # Execute Agent (Streaming)
            for event in self.graph.stream(self.state):
                # Update state
                for node_name, node_output in event.items():
                    if "messages" in node_output:
                        new_messages = node_output["messages"]

                        # Render new messages
                        for msg in new_messages:
                            # Stop thinking indicator (on first output)
                            if progress:
                                progress.stop()
                                progress = None

                            render_message(msg)

                        # Update local state
                        self.state["messages"].extend(new_messages)

        finally:
            # Ensure progress bar stops
            if progress:
                progress.stop()


# ═══════════════════════════════════════════════════════════════
# Application Entry Point
# ═══════════════════════════════════════════════════════════════


def main():
    """Start TUI Application"""
    app = TUIApp()
    app.run()


if __name__ == "__main__":
    main()
