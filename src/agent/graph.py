"""
═══════════════════════════════════════════════════════════════
Agent Core - Multi-Agent System
═══════════════════════════════════════════════════════════════
Architecture:
  - Supervisor (Orchestrator): Manages task distribution and coordination
  - Planner: Project planning
  - Coder: Code generation
  - Reviewer: Code review

Streaming Design (Best Practice):
  - Worker nodes use regular functions (not generators)
  - LLM calls use model.invoke() - LangChain auto-enables streaming
  - External stream_mode="messages" captures token-level output
"""

from typing import Literal

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from ..config import settings
from ..prompts import (
    CODER_PROMPT,
    PLANNER_PROMPT,
    REVIEWER_PROMPT,
)
from ..tools.registry import get_registry
from ..utils.logger import logger
from .context import worker_context
from .human_in_the_loop import wrap_tool_with_confirmation
from .state import AgentState, Plan


def get_model():
    return ChatOpenAI(
        model=settings.openai_model_name,
        temperature=0,
        timeout=60,
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key,
    )


def create_worker(name: str, system_prompt: str, tools: list, middleware: list = None):
    """Create a Worker Agent"""
    model = get_model()
    agent = create_agent(
        model, tools, system_prompt=system_prompt, middleware=middleware or []
    )
    return agent


# Get tools
registry = get_registry()
all_tools = registry.get_all_tools()
lc_tools = [wrap_tool_with_confirmation(t.to_langchain_tool()) for t in all_tools]

# ═══════════════════════════════════════════════════════════════
# Tools for Planner: Read + Scaffolding + Planning
# ═══════════════════════════════════════════════════════════════
# Per LangGraph docs: "Each specialist should have the tools needed to complete their responsibilities"
# Planner is responsible for:
#   1. Analyzing project requirements
#   2. Creating project structure (scaffolding)
#   3. Generating implementation plan
# Therefore, it needs scaffolding tools (create_directory, write_file) for config files
PLANNER_ALLOWED_TOOLS = {
    # Read tools
    "read_file",
    "list_files",
    "path_exists",
    # Scaffolding tools (NEW: enables project structure creation)
    "create_directory",  # For directory structure
    "write_file",  # For config files (package.json, requirements.txt, etc.)
    # Planning tools
    "submit_plan",
    "web_search",
}
lc_tools_for_planner = [t for t in lc_tools if t.name in PLANNER_ALLOWED_TOOLS]

# Tools for Coder: all tools EXCEPT submit_plan
lc_tools_for_coder = [t for t in lc_tools if t.name != "submit_plan"]

# Tools for Reviewer: read tools + shell for testing (NO write/create/delete)
REVIEWER_ALLOWED_TOOLS = {
    "read_file",
    "list_files",
    "path_exists",
    "shell",
    "web_search",
}
lc_tools_for_reviewer = [t for t in lc_tools if t.name in REVIEWER_ALLOWED_TOOLS]

# ═══════════════════════════════════════════════════════════════
# Create Summarization Middleware (prevent context window overflow)
# ═══════════════════════════════════════════════════════════════
# Auto-summarize old messages when conversation gets too long
# Reference: https://docs.langchain.com/oss/python/langchain/middleware/built-in
from langchain.agents.middleware import SummarizationMiddleware

# Create model instance with same endpoint as main model
# This ensures summarization uses the same base_url (e.g., custom proxy/API)
summarization_model = ChatOpenAI(
    model=settings.summarization_model,
    temperature=0,
    timeout=60,
    base_url=settings.openai_base_url,  # Same endpoint as main model
    api_key=settings.openai_api_key,
)

summarization = SummarizationMiddleware(
    model=summarization_model,  # Pass instance, not string
    max_tokens_before_summary=settings.summarization_trigger_tokens,
    messages_to_keep=settings.summarization_keep_messages,
)

# ═══════════════════════════════════════════════════════════════
# Create worker agents with appropriate tool sets
# ═══════════════════════════════════════════════════════════════
# REMOVED: ToolCallLimitMiddleware (was misused for workflow control)
# Workflow control is now handled by state + supervisor routing
# Per LangGraph docs: middleware is for cross-cutting concerns, NOT workflow logic
# ADDED: SummarizationMiddleware (proper use case - cross-cutting concern)
planner_agent = create_worker(
    "Planner", PLANNER_PROMPT, lc_tools_for_planner, middleware=[summarization]
)
coder_agent = create_worker(
    "Coder", CODER_PROMPT, lc_tools_for_coder, middleware=[summarization]
)
reviewer_agent = create_worker(
    "Reviewer", REVIEWER_PROMPT, lc_tools_for_reviewer, middleware=[summarization]
)

logger.info(f"Planner tools: {[t.name for t in lc_tools_for_planner]}")
logger.info(f"Coder tools: {[t.name for t in lc_tools_for_coder]}")
logger.info(f"Reviewer tools: {[t.name for t in lc_tools_for_reviewer]}")

members = ["Planner", "Coder", "Reviewer"]
options = ["FINISH"] + members


class Router(BaseModel):
    """Worker selection router"""

    next: Literal["Planner", "Coder", "Reviewer", "FINISH"]


def supervisor_node(state: AgentState):
    """
    Supervisor Node: Intelligent routing with feedback loops

    Based on LangGraph best practices:
    - Conditional edges for loop creation
    - State-based termination conditions
    - Recursion limits for safety

    Reference: https://docs.langchain.com/oss/python/langgraph/use-graph-api
    """
    phase = state.get("phase", "planning")
    plan = state.get("plan")
    messages = state.get("messages", [])
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 15)
    review_status = state.get("review_status", "pending")

    logger.info(
        f"Supervisor: phase={phase}, iteration={iteration_count}/{max_iterations}, review={review_status}"
    )

    # ═══════════════════════════════════════════════════════════════
    # Helper functions
    # ═══════════════════════════════════════════════════════════════
    def is_last_message_from_user():
        if not messages:
            return False
        last_msg = messages[-1]
        if hasattr(last_msg, "type") and last_msg.type == "human":
            return True
        if last_msg.__class__.__name__ == "HumanMessage":
            return True
        return False

    def count_user_messages():
        count = 0
        for msg in messages:
            if hasattr(msg, "type") and msg.type == "human":
                count += 1
            elif msg.__class__.__name__ == "HumanMessage":
                count += 1
        return count

    # ═══════════════════════════════════════════════════════════════
    # Safety Warning: High iteration count (soft limit, not forced termination)
    # ═══════════════════════════════════════════════════════════════
    # Good Taste: Let the task complete naturally (review_status="passed")
    # rather than forcing termination. max_iterations is a WARNING, not a HARD LIMIT.
    # User can always Ctrl+C if truly stuck.
    if iteration_count >= max_iterations:
        logger.warning(
            f"Supervisor: High iteration count ({iteration_count}/{max_iterations}). "
            f"Continuing but may be stuck in a loop. User can interrupt with Ctrl+C."
        )

    # ═══════════════════════════════════════════════════════════════
    # New user message → Reset and route to Planner
    # ═══════════════════════════════════════════════════════════════
    if is_last_message_from_user():
        user_msg_count = count_user_messages()
        logger.info(
            f"Supervisor: User message #{user_msg_count} detected, routing to Planner"
        )
        return {
            "next": "Planner",
            "phase": "planning",
            "plan": None,  # Reset plan
            "iteration_count": 0,  # Reset iteration counter
            "review_status": "pending",  # Reset review status
            "issues_found": [],  # Clear issues
        }

    # ═══════════════════════════════════════════════════════════════
    # Phase-based routing with feedback loops
    # ═══════════════════════════════════════════════════════════════
    if phase == "planning":
        if plan is not None:
            logger.info("Supervisor: Plan submitted, moving to coding phase")
            return {"next": "Coder", "phase": "coding"}
        else:
            logger.info("Supervisor: Planning complete without plan, finishing")
            return {"next": "FINISH", "phase": "done"}

    elif phase == "coding":
        logger.info("Supervisor: Coding done, moving to review phase")
        return {
            "next": "Reviewer",
            "phase": "reviewing",
            "review_status": "pending",  # Reset review status before review
        }

    elif phase == "reviewing":
        # ═══════════════════════════════════════════════════════════════
        # CRITICAL: Feedback loop implementation
        # Check Reviewer's verdict and decide whether to iterate
        # ═══════════════════════════════════════════════════════════════
        if review_status == "needs_fixes":
            logger.info(
                "Supervisor: Review FAILED, routing back to Coder (feedback loop)"
            )
            return {
                "next": "Coder",
                "phase": "coding",
                "iteration_count": iteration_count + 1,  # Increment iteration
            }
        else:
            # review_status is "passed" or "pending" (assume passed if not explicitly failed)
            logger.info("Supervisor: Review PASSED, finishing")
            return {"next": "FINISH", "phase": "done"}

    elif phase == "done":
        return {"next": "FINISH"}

    else:
        # Unknown phase, route to Planner as fallback
        logger.warning(f"Supervisor: Unknown phase '{phase}', routing to Planner")
        return {"next": "Planner", "phase": "planning"}


def create_multi_agent_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("Supervisor", supervisor_node)

    # ═══════════════════════════════════════════════════════════════
    # Worker Node Factory (Regular Function for stream_mode="messages")
    # ═══════════════════════════════════════════════════════════════
    # Best Practice from LangGraph docs:
    #   - Use regular functions (not generators)
    #   - LLM calls with model.invoke() auto-enable streaming
    #   - External stream_mode="messages" captures token-level output
    #
    # This allows the main graph's stream() to capture LLM tokens
    # from inside the worker agent's execution.
    # ═══════════════════════════════════════════════════════════════

    def make_worker_node(agent_graph, name: str):
        """
        Create a regular function worker node that supports streaming

        Args:
            agent_graph: The compiled agent graph (from create_agent)
            name: Worker name for logging

        Returns:
            Regular function that returns state updates
        """

        def worker_node(state: AgentState):
            """
            Regular node: invokes worker and returns final state

            Note: Even though we use invoke(), LangChain auto-enables
            streaming when the outer graph uses stream_mode="messages"
            """
            logger.info(f"[{name}] Starting execution...")

            from langchain_core.messages import SystemMessage

            # Count user messages to determine context
            user_msg_count = sum(
                1
                for msg in state.get("messages", [])
                if (hasattr(msg, "type") and msg.type == "human")
                or msg.__class__.__name__ == "HumanMessage"
            )

            # For Planner: inject context about the conversation state
            if name == "Planner" and user_msg_count > 1:
                context_text = f"""## Context
This is message #{user_msg_count} from the user in this conversation.
The user has previously requested work and is now providing FEEDBACK.
Focus on addressing their LATEST message - they are likely reporting issues with what was built.
Use tools (list_files, read_file) to investigate the current state before planning fixes.
"""
                context_msg = SystemMessage(content=context_text)
                state = {**state, "messages": [context_msg] + list(state["messages"])}
                logger.info(
                    f"[{name}] Injected context (user message #{user_msg_count})"
                )

            # For Coder: inject Plan into messages
            if name == "Coder" and state.get("plan"):
                plan = state["plan"]
                plan_text = (
                    f"## Plan to Implement\n\nSummary: {plan.summary}\n\nTasks:\n"
                )
                for task in plan.tasks:
                    plan_text += f"- Task {task.id}: {task.description}\n"
                plan_text += "\nImplement these tasks using the available tools. Do NOT create a new plan."

                plan_msg = SystemMessage(content=plan_text)
                state = {**state, "messages": list(state["messages"]) + [plan_msg]}
                logger.info(f"[{name}] Injected plan into messages")

            # For Reviewer: inject context about what to review
            if name == "Reviewer" and state.get("plan"):
                plan = state["plan"]
                review_context = f"""## Review Context
The Coder just implemented the following plan:
Summary: {plan.summary}

Tasks completed:
"""
                for task in plan.tasks:
                    review_context += f"- Task {task.id}: {task.description}\n"
                review_context += """
Your job is to VERIFY the implementation:
1. Use list_files to check what files exist in 'playground/' directory
2. Use read_file to examine the code
3. Use shell to test if the application runs
4. Report any issues found
"""
                review_msg = SystemMessage(content=review_context)
                state = {**state, "messages": list(state["messages"]) + [review_msg]}
                logger.info(f"[{name}] Injected review context")

            # Invoke worker agent (LangChain auto-streams when outer uses stream_mode="messages")
            with worker_context(name):
                result = agent_graph.invoke(state)

            # Extract messages from result
            new_messages = result.get("messages", [])
            if not isinstance(new_messages, list):
                new_messages = [new_messages]

            # Build return state
            return_state = {"messages": new_messages}

            # ═══════════════════════════════════════════════════════════════
            # Extract Plan if this is Planner
            # ═══════════════════════════════════════════════════════════════
            if name == "Planner":
                for msg in new_messages:
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            if tool_call["name"] == "submit_plan":
                                try:
                                    plan_data = tool_call["args"].get("plan")
                                    if plan_data:
                                        # Handle different types of plan_data
                                        if isinstance(plan_data, Plan):
                                            plan = plan_data
                                        elif isinstance(plan_data, dict):
                                            plan = Plan(**plan_data)
                                        elif isinstance(plan_data, str):
                                            # Try to parse as JSON
                                            import json

                                            plan = Plan(**json.loads(plan_data))
                                        else:
                                            logger.error(
                                                f"[{name}] Unknown plan_data type: {type(plan_data)}"
                                            )
                                            continue
                                        return_state["plan"] = plan
                                        logger.info(f"[{name}] Plan extracted")
                                except Exception as e:
                                    logger.error(
                                        f"[{name}] Plan extraction failed: {e}"
                                    )

            # ═══════════════════════════════════════════════════════════════
            # Extract review_status if this is Reviewer
            # ═══════════════════════════════════════════════════════════════
            if name == "Reviewer":
                # Parse Reviewer's last message to determine review status
                review_status = "pending"
                issues = []

                for msg in reversed(new_messages):
                    content = msg.content if hasattr(msg, "content") else str(msg)
                    if not content:
                        continue

                    # Look for explicit review markers
                    if "REVIEW: PASSED" in content or "REVIEW:PASSED" in content:
                        review_status = "passed"
                        logger.info(f"[{name}] Detected PASSED status")
                        break
                    elif (
                        "REVIEW: NEEDS_FIXES" in content
                        or "REVIEW:NEEDS_FIXES" in content
                    ):
                        review_status = "needs_fixes"
                        logger.info(f"[{name}] Detected NEEDS_FIXES status")
                        # Try to extract issues (look for numbered list)
                        import re

                        issue_matches = re.findall(
                            r"^\d+\.\s*(.+)$", content, re.MULTILINE
                        )
                        if issue_matches:
                            issues = issue_matches
                            logger.info(f"[{name}] Extracted {len(issues)} issues")
                        break

                return_state["review_status"] = review_status
                if issues:
                    return_state["issues_found"] = issues

            logger.info(f"[{name}] Completed with {len(new_messages)} messages")
            return return_state

        return worker_node

    # Add worker nodes
    workflow.add_node("Planner", make_worker_node(planner_agent, "Planner"))
    workflow.add_node("Coder", make_worker_node(coder_agent, "Coder"))
    workflow.add_node("Reviewer", make_worker_node(reviewer_agent, "Reviewer"))

    # Add edges
    workflow.add_edge(START, "Supervisor")

    workflow.add_conditional_edges(
        "Supervisor",
        lambda state: state["next"],
        {"Planner": "Planner", "Coder": "Coder", "Reviewer": "Reviewer", "FINISH": END},
    )

    workflow.add_edge("Planner", "Supervisor")
    workflow.add_edge("Coder", "Supervisor")
    workflow.add_edge("Reviewer", "Supervisor")

    return workflow.compile(checkpointer=MemorySaver())


# Export global Agent
agent_graph = create_multi_agent_graph()
