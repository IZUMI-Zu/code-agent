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

import json
import re
from typing import Literal

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from src.config import settings
from src.prompts import (
    CODER_PROMPT,
    PLANNER_PROMPT,
    REVIEWER_PROMPT,
)
from src.tools.registry import get_registry
from src.utils.logger import logger

from .context import worker_context
from .human_in_the_loop import wrap_tool_with_confirmation
from .state import AgentState, Plan


def get_model(task_type: Literal["lightweight", "reasoning"] = "reasoning"):
    """
    Get model instance based on task complexity

    Architecture: Model Stratification (Claude Code pattern)
    - lightweight: Fast, cheap models for simple checks (topic detection, validation)
    - reasoning: Powerful models for complex tasks (planning, coding, reviewing)

    Performance gain: 3-5x faster for lightweight tasks, 70% cost reduction
    """
    model_name = settings.lightweight_model if task_type == "lightweight" else settings.reasoning_model
    return ChatOpenAI(
        model=model_name,
        temperature=0,
        timeout=60,
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key,
    )


def create_worker(name: str, system_prompt: str, tools: list, middleware: list | None = None):
    """Create a Worker Agent"""
    model = get_model()
    agent = create_agent(model, tools, system_prompt=system_prompt, middleware=middleware or [])
    return agent


# ═══════════════════════════════════════════════════════════════
# Tool Loading (with MCP support)
# ═══════════════════════════════════════════════════════════════
# MCP tools are loaded asynchronously on first use
# This avoids blocking the module import

registry = get_registry()

# MCP server configuration
# You can customize this in your .env or config file
MCP_SERVER_CONFIG = {
    "fetch": {
        "transport": "stdio",  # 本地进程通信(uvx 服务器)
        "command": "uvx",
        "args": ["mcp-server-fetch"],
    }
}


def _get_tools_for_agent(include_mcp: bool = True):
    """
    Get tools for agents (with optional MCP tools)

    Args:
        include_mcp: Whether to include MCP tools

    Returns:
        List of LangChain tools
    """
    all_tools = registry.get_all_tools_with_mcp() if include_mcp else registry.get_all_tools()

    # Convert to LangChain tools and wrap with confirmation
    lc_tools = []
    for tool in all_tools:
        if hasattr(tool, "to_langchain_tool"):
            # Built-in tool
            lc_tool = tool.to_langchain_tool()
            lc_tools.append(wrap_tool_with_confirmation(lc_tool))
        else:
            # MCP tool (already a LangChain tool)
            # Type assertion: we know MCP tools are BaseTool instances
            if isinstance(tool, BaseTool):
                lc_tools.append(wrap_tool_with_confirmation(tool))

    return lc_tools


# Get initial tools (without MCP, loaded synchronously)
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
    "grep_search",  # Code search
    # Scaffolding tools (NEW: enables project structure creation)
    "create_directory",  # For directory structure
    "write_file",  # For config files (package.json, requirements.txt, etc.)
    # Planning tools
    "submit_plan",
    "web_search",
    # MCP tools (if loaded)
    "fetch",  # From mcp-server-fetch
    "fetch_html",  # From mcp-server-fetch
}
lc_tools_for_planner = [t for t in lc_tools if t.name in PLANNER_ALLOWED_TOOLS]

# Tools for Coder: all tools EXCEPT submit_plan
lc_tools_for_coder = [t for t in lc_tools if t.name != "submit_plan"]

# Tools for Reviewer: read tools + shell for testing (NO write/create/delete)
REVIEWER_ALLOWED_TOOLS = {
    "read_file",
    "list_files",
    "path_exists",
    "grep_search",  # Code search
    "shell",
    "web_search",
}
lc_tools_for_reviewer = [t for t in lc_tools if t.name in REVIEWER_ALLOWED_TOOLS]

# ═══════════════════════════════════════════════════════════════
# Create Summarization Middleware (prevent context window overflow)
# ═══════════════════════════════════════════════════════════════
# Auto-summarize old messages when conversation gets too long
# Reference: https://docs.langchain.com/oss/python/langchain/middleware/built-in

# Create model instance for summarization (use lightweight model)
summarization_model = get_model("lightweight")

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
planner_agent = create_worker("Planner", PLANNER_PROMPT, lc_tools_for_planner, middleware=[summarization])
coder_agent = create_worker("Coder", CODER_PROMPT, lc_tools_for_coder, middleware=[summarization])
reviewer_agent = create_worker("Reviewer", REVIEWER_PROMPT, lc_tools_for_reviewer, middleware=[summarization])

logger.info(f"Planner tools: {[t.name for t in lc_tools_for_planner]}")
logger.info(f"Coder tools: {[t.name for t in lc_tools_for_coder]}")
logger.info(f"Reviewer tools: {[t.name for t in lc_tools_for_reviewer]}")

members = ["Planner", "Coder", "Reviewer"]
options = ["FINISH", *members]


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

    logger.info(f"Supervisor: phase={phase}, iteration={iteration_count}/{max_iterations}, review={review_status}")

    # ═══════════════════════════════════════════════════════════════
    # Helper functions
    # ═══════════════════════════════════════════════════════════════
    def is_last_message_from_user():
        if not messages:
            return False
        last_msg = messages[-1]
        if hasattr(last_msg, "type") and last_msg.type == "human":
            return True
        return last_msg.__class__.__name__ == "HumanMessage"

    def count_user_messages():
        count = 0
        for msg in messages:
            if (hasattr(msg, "type") and msg.type == "human") or msg.__class__.__name__ == "HumanMessage":
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
    # New user message → Route to Planner (but preserve context!)
    # ═══════════════════════════════════════════════════════════════
    if is_last_message_from_user():
        user_msg_count = count_user_messages()
        logger.info(f"Supervisor: User message #{user_msg_count} detected, routing to Planner")

        # CRITICAL: Don't reset plan for follow-up messages!
        # User might be providing feedback on existing work.
        # Planner will check workspace and decide if it's a fix or new project.
        if user_msg_count == 1:
            # First message: full reset
            logger.info("Supervisor: First user message, full reset")
            return {
                "next": "Planner",
                "phase": "planning",
                "plan": None,
                "iteration_count": 0,
                "review_status": "pending",
                "issues_found": [],
            }
        # Follow-up message: preserve plan, reset iteration
        logger.info("Supervisor: Follow-up message, preserving plan context")
        return {
            "next": "Planner",
            "phase": "planning",
            # Keep existing plan (Planner can see what was done before)
            "iteration_count": 0,  # Reset iteration for new round
            "review_status": "pending",
            "issues_found": [],
        }

    # ═══════════════════════════════════════════════════════════════
    # Phase-based routing with feedback loops
    # ═══════════════════════════════════════════════════════════════
    if phase == "planning":
        if plan is not None:
            logger.info("Supervisor: Plan submitted, moving to coding phase")
            return {"next": "Coder", "phase": "coding"}
        logger.info("Supervisor: Planning complete without plan, finishing")
        return {"next": "FINISH", "phase": "done"}

    if phase == "coding":
        logger.info("Supervisor: Coding done, moving to review phase")
        return {
            "next": "Reviewer",
            "phase": "reviewing",
            "review_status": "pending",  # Reset review status before review
        }

    if phase == "reviewing":
        # ═══════════════════════════════════════════════════════════════
        # CRITICAL: Feedback loop implementation
        # Check Reviewer's verdict and decide whether to iterate
        # ═══════════════════════════════════════════════════════════════
        if review_status == "needs_fixes":
            logger.info("Supervisor: Review FAILED, routing back to Coder (feedback loop)")
            return {
                "next": "Coder",
                "phase": "coding",
                "iteration_count": iteration_count + 1,  # Increment iteration
            }
        if review_status == "passed":
            logger.info("Supervisor: Review PASSED, finishing")
            return {"next": "FINISH", "phase": "done"}
        # review_status is "pending" - this shouldn't happen!
        # Log warning and route back to Reviewer for re-review
        logger.warning(
            "Supervisor: Review status is 'pending' after Reviewer execution. "
            "This indicates a parsing failure. Finishing anyway to avoid infinite loop."
        )
        return {"next": "FINISH", "phase": "done"}

    if phase == "done":
        return {"next": "FINISH"}

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
                if (hasattr(msg, "type") and msg.type == "human") or msg.__class__.__name__ == "HumanMessage"
            )

            # For Planner: inject context about the conversation state
            if name == "Planner" and user_msg_count > 1:
                prev_plan_summary = ""
                plan = state.get("plan")
                if plan:
                    prev_plan_summary = f"\n\nPrevious plan summary: {plan.summary}"

                context_text = f"""## Context
This is message #{user_msg_count} from the user in this conversation.
The user has previously requested work and is now providing FEEDBACK.{prev_plan_summary}

MANDATORY WORKFLOW:
1. FIRST: Use list_files(".") to see what exists in the workspace
2. THEN: Use read_file() to check current state
3. FINALLY: Plan INCREMENTAL fixes (not full rebuild!)

The user is likely reporting:
- Bugs in existing code
- Missing features
- Requests for changes

DO NOT rebuild from scratch! Check what exists and plan targeted fixes.
"""
                context_msg = SystemMessage(content=context_text)
                state = {**state, "messages": [context_msg, *list(state["messages"])]}
                logger.info(f"[{name}] Injected context (user message #{user_msg_count})")

            # For Coder: inject Plan into messages with CRITICAL instructions
            plan = state.get("plan")
            if name == "Coder" and plan:
                plan_text = f"""## Plan to Implement

Summary: {plan.summary}

Tasks:
"""
                for task in plan.tasks:
                    plan_text += f"- Task {task.id}: {task.description}\n"

                plan_text += """
CRITICAL WORKFLOW (MANDATORY):
1. BEFORE implementing ANY task, use list_files() to check what exists
2. Use read_file() to check if work is already done
3. If a file already exists and looks correct, SKIP that task
4. Only write/modify files that are missing or incorrect
5. After completing all NEW work, STOP immediately

WHY THIS MATTERS:
- Avoid overwriting existing work
- Detect completed tasks
- Make minimal, targeted changes
- Don't repeat yourself!

EXAMPLE:
Task: "Create Header.jsx"
Step 1: list_files("src/components/layout/")
Step 2: If Header.jsx exists, read_file() to check it
Step 3: If it looks good, SKIP this task
Step 4: Move to next task

Implement these tasks using the available tools. Do NOT create a new plan.
"""
                plan_msg = SystemMessage(content=plan_text)
                state = {**state, "messages": [*list(state["messages"]), plan_msg]}
                logger.info(f"[{name}] Injected plan with anti-duplication instructions")

            # For Reviewer: inject context about what to review
            plan = state.get("plan")
            if name == "Reviewer" and plan:
                review_context = f"""## Review Context
The Coder just implemented the following plan:
Summary: {plan.summary}

Tasks completed:
"""
                for task in plan.tasks:
                    review_context += f"- Task {task.id}: {task.description}\n"
                review_context += """
Your job is to VERIFY the implementation:
1. Use list_files(".") to check what files exist in the workspace
2. Use read_file to examine the code
3. Use shell to test if the application runs
4. Report any issues found
"""
                review_msg = SystemMessage(content=review_context)
                state = {**state, "messages": [*list(state["messages"]), review_msg]}
                logger.info(f"[{name}] Injected review context")

            # ═══════════════════════════════════════════════════════════════
            # Invoke worker agent with PlanSubmittedException handling
            # ═══════════════════════════════════════════════════════════════
            # For Planner: catch PlanSubmittedException to immediately stop
            # after submit_plan is called. This is more reliable than
            # prompt-based "STOP NOW" instructions.
            #
            # Reference: LangGraph docs recommend using exceptions for
            # immediate termination of agent loops.
            # ═══════════════════════════════════════════════════════════════
            from src.tools.planning import PlanSubmittedException

            try:
                with worker_context(name):
                    result = agent_graph.invoke(state)

                # Extract messages from result
                new_messages = result.get("messages", [])
                if not isinstance(new_messages, list):
                    new_messages = [new_messages]

                # Build return state
                return_state = {"messages": new_messages}

                # ═══════════════════════════════════════════════════════════════
                # Extract Plan if this is Planner (fallback for normal completion)
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
                                                plan = Plan(**json.loads(plan_data))
                                            else:
                                                logger.error(f"[{name}] Unknown plan_data type: {type(plan_data)}")
                                                continue
                                            return_state["plan"] = plan  # type: ignore  # noqa: PGH003
                                            logger.info(f"[{name}] Plan extracted from tool call")
                                    except Exception as e:
                                        logger.error(f"[{name}] Plan extraction failed: {e}")

            except PlanSubmittedException as e:
                # ═══════════════════════════════════════════════════════════════
                # Plan submitted! Extract plan and return immediately.
                # This is the preferred path - agent stopped immediately after
                # submit_plan was called, no extra tool calls.
                # ═══════════════════════════════════════════════════════════════
                logger.info(f"[{name}] Plan submitted via exception - stopping immediately")
                from langchain_core.messages import AIMessage

                # Create a summary message for the conversation
                summary_msg = AIMessage(
                    content=f"Plan submitted successfully with {len(e.plan.tasks)} tasks. "
                    f"The Coder agent will now implement this plan."
                )
                return {
                    "messages": [summary_msg],
                    "plan": e.plan,
                }

            # ═══════════════════════════════════════════════════════════════
            # Extract review_status if this is Reviewer
            # ═══════════════════════════════════════════════════════════════
            if name == "Reviewer":
                # Parse Reviewer's structured output
                # Architecture: Use structured output instead of fragile string matching
                review_status = "pending"
                issues = []

                for msg in reversed(new_messages):
                    content = msg.content if hasattr(msg, "content") else str(msg)
                    if not content:
                        continue

                    # Try to parse as JSON (structured output)
                    try:
                        from src.agent.structured_output import ReviewResult

                        # ═══════════════════════════════════════════════════════════════
                        # Extract JSON from content (LLM might add extra text)
                        # ═══════════════════════════════════════════════════════════════
                        # Try direct parsing first
                        try:
                            review_data = json.loads(content)
                        except json.JSONDecodeError:
                            # Fallback: Extract JSON block using regex
                            # Look for {...} pattern (non-greedy, handles nested braces)
                            json_match = re.search(r"\{(?:[^{}]|\{[^{}]*\})*\}", content, re.DOTALL)
                            if json_match:
                                json_str = json_match.group(0)
                                review_data = json.loads(json_str)
                            else:
                                raise json.JSONDecodeError("No JSON found", content, 0) from None

                        review_result = ReviewResult(**review_data)

                        review_status = review_result.status
                        issues = review_result.issues

                        logger.info(
                            f"[{name}] Structured output parsed: status={review_status}, "
                            f"issues={len(issues)}, files_checked={len(review_result.files_checked)}"
                        )
                        break
                    except (json.JSONDecodeError, Exception):
                        # Fallback: try old string matching (for backward compatibility)
                        if "REVIEW: PASSED" in content or "REVIEW:PASSED" in content:
                            review_status = "passed"
                            logger.info(f"[{name}] Fallback: Detected PASSED status via string matching")
                            break
                        if "REVIEW: NEEDS_FIXES" in content or "REVIEW:NEEDS_FIXES" in content:
                            review_status = "needs_fixes"
                            logger.info(f"[{name}] Fallback: Detected NEEDS_FIXES status via string matching")
                            # Try to extract issues (look for numbered list)
                            issue_matches = re.findall(r"^\d+\.\s*(.+)$", content, re.MULTILINE)
                            if issue_matches:
                                issues = issue_matches
                                logger.info(f"[{name}] Fallback: Extracted {len(issues)} issues")
                            break

                return_state["review_status"] = review_status  # type: ignore  # noqa: PGH003
                if issues:
                    return_state["issues_found"] = issues  # type: ignore  # noqa: PGH003

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


# ═══════════════════════════════════════════════════════════════
# Async Initialization (for MCP tools)
# ═══════════════════════════════════════════════════════════════


async def initialize_mcp_tools():
    """
    Initialize MCP tools asynchronously

    This should be called once at application startup.
    After calling this, agents will have access to MCP tools.

    Example:
        >>> import asyncio
        >>> asyncio.run(initialize_mcp_tools())
    """
    global lc_tools, lc_tools_for_planner, lc_tools_for_coder, lc_tools_for_reviewer

    try:
        logger.info("Initializing MCP tools...")

        # Load MCP tools
        await registry.load_mcp_tools(MCP_SERVER_CONFIG)

        # Refresh tool lists
        lc_tools = _get_tools_for_agent(include_mcp=True)

        # Update agent-specific tool lists
        lc_tools_for_planner = [t for t in lc_tools if t.name in PLANNER_ALLOWED_TOOLS]
        lc_tools_for_coder = [t for t in lc_tools if t.name != "submit_plan"]
        lc_tools_for_reviewer = [t for t in lc_tools if t.name in REVIEWER_ALLOWED_TOOLS]

        logger.info(f"MCP tools initialized. Total tools: {len(lc_tools)}")
        logger.info(f"  Planner: {len(lc_tools_for_planner)} tools")
        logger.info(f"  Coder: {len(lc_tools_for_coder)} tools")
        logger.info(f"  Reviewer: {len(lc_tools_for_reviewer)} tools")

    except Exception as e:
        logger.error(f"Failed to initialize MCP tools: {e}")
        logger.warning("Continuing with built-in tools only")


# Export global Agent
agent_graph = create_multi_agent_graph()
