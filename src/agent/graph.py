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


def create_worker(name: str, system_prompt: str, tools: list):
    """Create a Worker Agent"""
    model = get_model()
    agent = create_agent(model, tools, system_prompt=system_prompt)
    return agent


# Get tools
registry = get_registry()
all_tools = registry.get_all_tools()
lc_tools = [wrap_tool_with_confirmation(t.to_langchain_tool()) for t in all_tools]
lc_tools_without_plan = [t for t in lc_tools if t.name != "submit_plan"]

# Create worker agents
planner_agent = create_worker("Planner", PLANNER_PROMPT, lc_tools)
coder_agent = create_worker("Coder", CODER_PROMPT, lc_tools_without_plan)
reviewer_agent = create_worker("Reviewer", REVIEWER_PROMPT, lc_tools_without_plan)

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

            # For Coder: inject Plan into messages
            if name == "Coder" and state.get("plan"):
                from langchain_core.messages import SystemMessage
                plan = state["plan"]
                plan_text = f"## Plan to Implement\n\nSummary: {plan.summary}\n\nTasks:\n"
                for task in plan.tasks:
                    plan_text += f"- Task {task.id}: {task.description}\n"
                plan_text += "\nImplement these tasks using the available tools. Do NOT create a new plan."
                
                plan_msg = SystemMessage(content=plan_text)
                state = {**state, "messages": list(state["messages"]) + [plan_msg]}
                logger.info(f"[{name}] Injected plan into messages")

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
