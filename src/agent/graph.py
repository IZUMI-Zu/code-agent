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
from langchain.agents.middleware import ToolCallLimitMiddleware
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
    agent = create_agent(model, tools, system_prompt=system_prompt, middleware=middleware or [])
    return agent


# Get tools
registry = get_registry()
all_tools = registry.get_all_tools()
lc_tools = [wrap_tool_with_confirmation(t.to_langchain_tool()) for t in all_tools]

# Tools for Planner: ONLY read tools + submit_plan (NO write/create/delete)
# This ensures Planner only plans, doesn't implement
PLANNER_ALLOWED_TOOLS = {"read_file", "list_files", "path_exists", "submit_plan", "web_search"}
lc_tools_for_planner = [t for t in lc_tools if t.name in PLANNER_ALLOWED_TOOLS]

# Tools for Coder: all tools EXCEPT submit_plan
lc_tools_for_coder = [t for t in lc_tools if t.name != "submit_plan"]

# Tools for Reviewer: read tools + shell for testing (NO write/create/delete)
REVIEWER_ALLOWED_TOOLS = {"read_file", "list_files", "path_exists", "shell", "web_search"}
lc_tools_for_reviewer = [t for t in lc_tools if t.name in REVIEWER_ALLOWED_TOOLS]

# Create worker agents with appropriate tool sets
# Planner: limit submit_plan to 1 call and stop immediately after
planner_middleware = [
    ToolCallLimitMiddleware(
        tool_name="submit_plan",
        run_limit=1,
        exit_behavior="end",  # Stop immediately after submit_plan is called
    )
]
planner_agent = create_worker("Planner", PLANNER_PROMPT, lc_tools_for_planner, middleware=planner_middleware)
coder_agent = create_worker("Coder", CODER_PROMPT, lc_tools_for_coder)
reviewer_agent = create_worker("Reviewer", REVIEWER_PROMPT, lc_tools_for_reviewer)

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
    Supervisor Node: Intelligent routing using hybrid approach
    """
    phase = state.get("phase", "planning")
    plan = state.get("plan")
    messages = state.get("messages", [])

    logger.info(f"Supervisor: Current phase = {phase}, messages count = {len(messages)}")

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

    if messages:
        last_msg = messages[-1]
        msg_type = getattr(last_msg, "type", None) or last_msg.__class__.__name__
        logger.info(f"Supervisor: Last message type = {msg_type}")

    # New user message -> route to Planner
    if is_last_message_from_user():
        user_msg_count = count_user_messages()
        logger.info(f"Supervisor: User message detected (total: {user_msg_count}), routing to Planner")
        return {"next": "Planner", "phase": "planning", "plan": None}

    # Phase-based routing
    if phase == "planning":
        if plan is not None:
            logger.info("Supervisor: Plan submitted, moving to coding phase")
            return {"next": "Coder", "phase": "coding"}
        else:
            logger.info("Supervisor: Planning phase complete without plan, finishing")
            return {"next": "FINISH", "phase": "done"}

    elif phase == "coding":
        logger.info("Supervisor: Coding done, moving to review phase")
        return {"next": "Reviewer", "phase": "reviewing"}

    elif phase == "reviewing":
        logger.info("Supervisor: Review done, finishing")
        return {"next": "FINISH", "phase": "done"}

    elif phase == "done":
        return {"next": "FINISH"}

    else:
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
                1 for msg in state.get("messages", [])
                if (hasattr(msg, "type") and msg.type == "human") or 
                   msg.__class__.__name__ == "HumanMessage"
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
                logger.info(f"[{name}] Injected context (user message #{user_msg_count})")

            # For Coder: inject Plan into messages
            if name == "Coder" and state.get("plan"):
                plan = state["plan"]
                plan_text = f"## Plan to Implement\n\nSummary: {plan.summary}\n\nTasks:\n"
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

            # Extract Plan if this is Planner
            if name == "Planner":
                for msg in new_messages:
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            if tool_call["name"] == "submit_plan":
                                try:
                                    plan_data = tool_call["args"].get("plan")
                                    if plan_data:
                                        plan = Plan(**plan_data)
                                        return_state["plan"] = plan
                                        logger.info(f"[{name}] Plan extracted")
                                except Exception as e:
                                    logger.error(f"[{name}] Plan extraction failed: {e}")

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
