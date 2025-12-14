"""
Agent Core - Multi-Agent System
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

from code_agent.config import settings
from code_agent.prompts import (
    CODER_PROMPT,
    PLANNER_PROMPT,
    REVIEWER_PROMPT,
)
from code_agent.tools.registry import get_registry
from code_agent.utils.logger import logger

from .context import worker_context
from .human_in_the_loop import wrap_tool_with_confirmation
from .state import AgentState, Plan


def trim_messages(messages: list, max_tokens: int = 8000, keep_last: int = 20):
    """
    Intelligent message trimming that preserves System Context.

    Strategy:
    1. ALWAYS keep all SystemMessages (they contain core instructions & rules).
    2. Keep the last `keep_last` messages (to maintain immediate conversation flow).
    3. Trim the middle if necessary.

    Note: This is a simplified token estimation (approx 4 chars/token).
    """
    from langchain_core.messages import SystemMessage

    # 1. Separate System Messages (Must Keep)
    system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
    other_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

    # 2. Check if we even need to trim
    # Simple estimation: 1 msg ≈ 100 tokens? Let's use char count / 4
    total_chars = sum(len(str(m.content)) for m in messages)
    est_tokens = total_chars / 4

    if est_tokens < max_tokens:
        return messages

    # 3. Trim "Other" messages (keep last N)
    if len(other_msgs) > keep_last:
        trimmed_others = other_msgs[-keep_last:]
        logger.info(f"Trimming context: Dropped {len(other_msgs) - keep_last} old messages to save space.")
    else:
        trimmed_others = other_msgs

    # 4. Reconstruct: System Messages + Trimmed Others
    # Note: This might reorder messages if SystemMessages were interleaved,
    # but for our Agent architecture, System Messages are usually
    # either at the start (Prompt) or injected immediately before execution (Context).
    # So placing them at the top is generally correct and safer for instruction following.
    return system_msgs + trimmed_others


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


# Tool Loading (with MCP support)
# MCP tools are loaded asynchronously on first use
# This avoids blocking the module import

registry = get_registry()

# MCP server configuration
# You can customize this in your .env or config file
MCP_SERVER_CONFIG = {
    "fetch": {
        "transport": "stdio",
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

# Tools for Planner: Read + Scaffolding + Planning
# Per LangGraph docs: "Each specialist should have the tools needed to complete their responsibilities"
# Planner is responsible for:
#   1. Analyzing project requirements
#   2. Creating project structure (scaffolding)
#   3. Generating implementation plan
# Therefore, it needs scaffolding tools (create_directory, write_file) for config files
PLANNER_ALLOWED_TOOLS = {
    # Read tools (for context)
    "read_file",
    "list_files",
    "path_exists",
    "grep_search",
    # Planning tools
    "submit_plan",
    "web_search",
    # MCP tools (if loaded)
    "fetch",
    "fetch_html",
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
    "process_manager",
}
lc_tools_for_reviewer = [t for t in lc_tools if t.name in REVIEWER_ALLOWED_TOOLS]

# Create Summarization Middleware (prevent context window overflow)
# Auto-summarize old messages when conversation gets too long
# Reference: https://docs.langchain.com/oss/python/langchain/middleware/built-in

# Create model instance for summarization (use lightweight model)
summarization_model = get_model("lightweight")

summarization = SummarizationMiddleware(
    model=summarization_model,  # Pass instance, not string
    max_tokens_before_summary=settings.summarization_trigger_tokens,
    messages_to_keep=settings.summarization_keep_messages,
)

# Create worker agents with appropriate tool sets
# REMOVED: ToolCallLimitMiddleware (was misused for workflow control)
# Workflow control is now handled by state + supervisor routing
# Per LangGraph docs: middleware is for cross-cutting concerns, NOT workflow logic
# DISABLED: SummarizationMiddleware (causes System Prompt loss)
# We rely on large context window (128k) of modern models instead.
planner_agent = create_worker("Planner", PLANNER_PROMPT, lc_tools_for_planner, middleware=[])
coder_agent = create_worker("Coder", CODER_PROMPT, lc_tools_for_coder, middleware=[])
reviewer_agent = create_worker("Reviewer", REVIEWER_PROMPT, lc_tools_for_reviewer, middleware=[])

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

    # Helper functions
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

    # Safety Warning: High iteration count (soft limit, not forced termination)
    # Good Taste: Let the task complete naturally (review_status="passed")
    # rather than forcing termination. max_iterations is a WARNING, not a HARD LIMIT.
    # User can always Ctrl+C if truly stuck.
    if iteration_count >= max_iterations:
        logger.error(
            f"Supervisor: Max iterations reached ({iteration_count}/{max_iterations}). "
            f"Terminating to prevent infinite loop."
        )
        return {"next": "FINISH", "phase": "done"}

    # New user message → Route to Planner (but preserve context!)
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

    # Phase-based routing with feedback loops
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
        # CRITICAL: Feedback loop implementation
        # Check Reviewer's verdict and decide whether to iterate
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
        # This means Reviewer's output was not parseable
        # CRITICAL FIX: Don't silently finish - expose the problem and retry
        logger.error(
            "Supervisor: Review status is 'pending' after Reviewer execution. "
            "This indicates a parsing failure. Routing back to Reviewer to retry."
        )

        # Safety: Only retry once to avoid infinite loop
        if iteration_count > 0:
            logger.error(
                "Supervisor: Reviewer parsing failed twice. "
                "This is a critical bug - Reviewer is not following output format. "
                "Forcing FINISH to prevent infinite loop."
            )
            return {"next": "FINISH", "phase": "done"}

        # First failure: retry Reviewer with explicit instructions
        return {
            "next": "Reviewer",
            "phase": "reviewing",
            "iteration_count": iteration_count + 1,
        }

    if phase == "done":
        return {"next": "FINISH"}

    # Unknown phase, route to Planner as fallback
    logger.warning(f"Supervisor: Unknown phase '{phase}', routing to Planner")
    return {"next": "Planner", "phase": "planning"}


def create_multi_agent_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("Supervisor", supervisor_node)

    # Worker Node Factory (Regular Function for stream_mode="messages")
    # Best Practice from LangGraph docs:
    #   - Use regular functions (not generators)
    #   - LLM calls with model.invoke() auto-enable streaming
    #   - External stream_mode="messages" captures token-level output
    #
    # This allows the main graph's stream() to capture LLM tokens
    # from inside the worker agent's execution.
    def make_worker_node(agent_graph, name: str):
        """
        Create a regular function worker node that supports streaming

        Args:
            agent_graph: The compiled agent graph (from create_agent)
            name: Worker name for logging

        Returns:
            Regular function that returns state updates
        """

        def worker_node(state: AgentState, config):
            """
            Regular node: invokes worker and returns final state

            Architecture: Auto-streaming (LangChain official pattern)
            - Accept config parameter (CRITICAL for streaming to work)
            - Pass config to agent_graph.invoke()
            - LangChain auto-enables streaming via callback propagation
            - Outer graph with stream_mode="messages" + subgraphs=True captures tokens

            Reference: https://github.com/langchain-ai/langgraph/issues/137
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

            # For Coder: inject Plan and PREVIOUS FAILURES into messages
            plan = state.get("plan")
            if name == "Coder" and plan:
                # 1. Inject Previous Failures (Memory)
                issues = state.get("issues_found", [])
                failure_context = ""
                if issues:
                    failure_context = "\n\n🚨 PREVIOUS ATTEMPT FAILED 🚨\nThe Reviewer found these issues with the last implementation:\n"
                    for i, issue in enumerate(issues, 1):
                        failure_context += f"{i}. {issue}\n"
                    failure_context += "\nYOU MUST FIX THESE ISSUES. Do not repeat the same mistakes.\n"
                    logger.info(f"[{name}] Injected {len(issues)} previous failures into context")

                plan_text = f"""## Plan to Implement

Summary: {plan.summary}
{failure_context}
Tasks:
"""
                for task in plan.tasks:
                    plan_text += f"- Task {task.id}: {task.description}\n"

                plan_text += """
CRITICAL WORKFLOW (MANDATORY):
1. RESEARCH FIRST (For Setups/Configs):
   - Check package.json for core versions (Vite, Next.js)
   - Search for "setup <lib> for <framework> <version>"
   - NEVER guess commands (like `init -p`)

2. CHECK WORKSPACE:
   - list_files() to see what exists
   - read_file() to check content
   - If correct, SKIP task

3. IMPLEMENT:
   - Only write/modify files that are missing or incorrect
   - Use str_replace for existing files

4. STOP immediately after completing NEW work

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
                # Use SystemMessage for instruction injection to ensure high priority
                # (System messages should be at the start)
                plan_msg = SystemMessage(content=plan_text)

                # Apply Smart Trimming (Preserve System Prompts + Last 20 messages)
                current_messages = list(state["messages"])
                trimmed_messages = trim_messages(current_messages, max_tokens=100000, keep_last=30)

                state = {**state, "messages": [plan_msg, *trimmed_messages]}
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
                # Use SystemMessage for instruction injection
                review_msg = SystemMessage(content=review_context)

                # Apply Smart Trimming
                current_messages = list(state["messages"])
                trimmed_messages = trim_messages(current_messages, max_tokens=100000, keep_last=30)

                state = {**state, "messages": [review_msg, *trimmed_messages]}
                logger.info(f"[{name}] Injected review context")

            # Invoke worker agent with PlanSubmittedException handling
            # For Planner: catch PlanSubmittedException to immediately stop
            # after submit_plan is called. This is more reliable than
            # prompt-based "STOP NOW" instructions.
            #
            # Reference: LangGraph docs recommend using exceptions for
            # immediate termination of agent loops.
            from code_agent.tools.planning import PlanSubmittedException

            try:
                with worker_context(name):
                    # Invoke worker agent with config (enables auto-streaming)
                    # CRITICAL: Pass config to enable LangChain's auto-streaming
                    # The outer graph (with subgraphs=True) will capture streamed tokens
                    # via callback propagation. This is the official LangChain pattern.

                    # Ensure we use the trimmed messages in the state passed to the agent
                    # Note: We modified 'state' above for Coder/Reviewer, but for Planner (or fallback)
                    # we should also apply trimming if not done.
                    if name == "Planner":
                        current_messages = list(state["messages"])
                        # Planner needs more history to understand user intent, keep more
                        trimmed_messages = trim_messages(current_messages, max_tokens=100000, keep_last=50)
                        state = {**state, "messages": trimmed_messages}

                    result = agent_graph.invoke(state, config=config)

                # Extract messages from result
                new_messages = result.get("messages", [])
                if not isinstance(new_messages, list):
                    new_messages = [new_messages]

                # Build return state
                return_state = {"messages": new_messages}

                # Extract Plan if this is Planner (fallback for normal completion)
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
                # Plan submitted! Extract plan and return immediately.
                # This is the preferred path - agent stopped immediately after
                # submit_plan was called, no extra tool calls.
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

            # Extract review_status if this is Reviewer
            if name == "Reviewer":
                # Extract tool calls from messages
                tool_calls_made = []
                for msg in new_messages:
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        tool_calls_made.extend([tc["name"] for tc in msg.tool_calls])

                # Check if Reviewer actually ran verification tools
                # Required tools: shell (for build/test) OR read_file (for code inspection)
                verification_tools = {"shell", "read_file", "list_files"}
                tools_used = set(tool_calls_made) & verification_tools

                if not tools_used:
                    # Reviewer didn't execute ANY verification tools!
                    logger.warning(
                        f"[{name}] CRITICAL: Reviewer did not execute any verification tools. "
                        f"Tool calls made: {tool_calls_made}. "
                        f"This is 'visual inspection' without actual validation."
                    )

                    # Return a special status to force retry
                    from langchain_core.messages import AIMessage

                    warning_msg = AIMessage(
                        content="⚠️ Reviewer Warning: You must execute verification tools (shell/read_file) "
                        "to validate the implementation. Visual inspection is not sufficient. "
                        "Please run build commands and check actual files."
                    )
                    return {
                        "messages": [*new_messages, warning_msg],
                        "review_status": "pending",  # Will trigger retry in supervisor
                        "issues_found": [
                            "Reviewer skipped verification tools. Must run shell commands or read files to validate."
                        ],
                    }

                logger.info(f"[{name}] Verification tools used: {list(tools_used)}")

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
                        from code_agent.agent.structured_output import ReviewResult

                        # Extract JSON from content (LLM might add extra text)
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


# Async Initialization (for MCP tools)


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
