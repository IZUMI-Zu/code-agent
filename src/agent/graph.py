"""
═══════════════════════════════════════════════════════════════
Agent Core - Multi-Agent System
═══════════════════════════════════════════════════════════════
Architecture:
  - Supervisor (Orchestrator): Manages task distribution and coordination
  - Planner: Project planning
  - Coder: Code generation
  - Reviewer: Code review
"""

from typing import Literal, cast

from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from ..config import settings
from ..prompts import (
    CODER_PROMPT,
    PLANNER_PROMPT,
    REVIEWER_PROMPT,
    SUPERVISOR_SYSTEM_PROMPT,
)
from ..tools.registry import get_registry
from ..utils.logger import logger
from .context import worker_context
from .human_in_the_loop import wrap_tool_with_confirmation
from .state import AgentState, Plan

# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════


def get_model():
    return ChatOpenAI(
        model=settings.openai_model_name,
        temperature=0,
        timeout=60,
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key,
    )


# ═══════════════════════════════════════════════════════════════
# Worker Agents
# ═══════════════════════════════════════════════════════════════


def create_worker(name: str, system_prompt: str, tools: list):
    """Create a Worker Agent"""
    model = get_model()

    # Use create_agent to create a standard ReAct Agent
    # It automatically handles the tool calling loop
    agent = create_agent(model, tools, system_prompt=system_prompt)

    return agent


# Get tools
registry = get_registry()
all_tools = registry.get_all_tools()
# Convert custom tools to LangChain tools
lc_tools = [wrap_tool_with_confirmation(t.to_langchain_tool()) for t in all_tools]

# Filter out submit_plan for non-Planner agents
lc_tools_without_plan = [t for t in lc_tools if t.name != "submit_plan"]

# 1. Planner Agent - has submit_plan tool
planner_agent = create_worker("Planner", PLANNER_PROMPT, lc_tools)

# 2. Coder Agent - no submit_plan tool
coder_agent = create_worker("Coder", CODER_PROMPT, lc_tools_without_plan)

# 3. Reviewer Agent - no submit_plan tool
reviewer_agent = create_worker("Reviewer", REVIEWER_PROMPT, lc_tools_without_plan)

# ═══════════════════════════════════════════════════════════════
# Supervisor (Orchestrator)
# ═══════════════════════════════════════════════════════════════

members = ["Planner", "Coder", "Reviewer"]
options = ["FINISH"] + members


class Router(BaseModel):
    """Worker selection router"""

    next: Literal["Planner", "Coder", "Reviewer", "FINISH"]


def supervisor_node(state: AgentState):
    """Supervisor Node: Decides the next executor based on workflow phase"""
    phase = state.get("phase", "planning")
    plan = state.get("plan")
    messages = state.get("messages", [])

    logger.info(f"Supervisor: Current phase = {phase}, messages count = {len(messages)}")

    # If phase is "done" but there are new messages, start a new workflow
    if phase == "done":
        # Check if there's a new user message (restart workflow)
        if messages and hasattr(messages[-1], "type") and messages[-1].type == "human":
            logger.info("Supervisor: New user message detected, restarting workflow")
            return {"next": "Planner", "phase": "planning", "plan": None}
        else:
            return {"next": "FINISH"}

    # Phase-based routing (deterministic, no LLM needed for basic flow)
    if phase == "planning":
        if plan is not None:
            # Plan submitted, move to coding phase
            logger.info("Supervisor: Plan submitted, moving to coding phase")
            return {"next": "Coder", "phase": "coding"}
        else:
            # Still planning
            return {"next": "Planner"}

    elif phase == "coding":
        # After Coder finishes, move to review
        logger.info("Supervisor: Coding done, moving to review phase")
        return {"next": "Reviewer", "phase": "reviewing"}

    elif phase == "reviewing":
        # After Reviewer finishes, we're done
        logger.info("Supervisor: Review done, finishing")
        return {"next": "FINISH", "phase": "done"}

    else:
        # Default: start from planning
        return {"next": "Planner", "phase": "planning"}


# ═══════════════════════════════════════════════════════════════
# Build Graph
# ═══════════════════════════════════════════════════════════════


def create_multi_agent_graph():
    workflow = StateGraph(AgentState)

    # Add Supervisor node
    workflow.add_node("Supervisor", supervisor_node)

    # ═══════════════════════════════════════════════════════════════
    # Worker Node Factory (Generator-Based for Stream Visibility)
    # ═══════════════════════════════════════════════════════════════
    # Design Philosophy (Good Taste: Eliminate Special Cases):
    #
    #   Problem: agent.invoke() is a BLACK BOX
    #     - Tool calls invisible to main stream
    #     - UI frozen during execution
    #     - Poor user experience
    #
    #   Solution: Generator nodes + agent.stream()
    #     - Each tool call -> yield update -> visible in main stream
    #     - UI updates in real-time
    #     - No special cases, clean data flow
    #
    #   How it works:
    #     Worker node is a GENERATOR function
    #     For each sub-graph update (model call, tool call, tool result):
    #       1. Extract new messages
    #       2. YIELD them to main graph
    #       3. Main graph's stream picks them up IMMEDIATELY
    #       4. UI renders them in real-time
    #
    #   Simplicity through structure, not through hacks.
    # ═══════════════════════════════════════════════════════════════

    def make_worker_node(agent_graph, name: str):
        """
        Create a generator-based worker node that streams updates

        Args:
            agent_graph: The compiled agent graph (from create_agent)
            name: Worker name for logging

        Returns:
            Generator function that yields state updates
        """

        def worker_node(state: AgentState):
            """
            Generator node: yields incremental updates from worker execution
            """
            logger.info(f"[{name}] Starting execution...")

            # For Coder: inject Plan into messages so it knows what to implement
            if name == "Coder" and state.get("plan"):
                from langchain_core.messages import SystemMessage
                plan = state["plan"]
                plan_text = f"## Plan to Implement\n\nSummary: {plan.summary}\n\nTasks:\n"
                for task in plan.tasks:
                    plan_text += f"- Task {task.id}: {task.description}\n"
                plan_text += "\nImplement these tasks using the available tools. Do NOT create a new plan."
                
                # Add plan as a system message
                plan_msg = SystemMessage(content=plan_text)
                state = {**state, "messages": list(state["messages"]) + [plan_msg]}
                logger.info(f"[{name}] Injected plan into messages")

            # Track accumulated messages for Plan extraction
            all_new_msgs = []
            num_old_msgs = len(state["messages"])

            # Stream worker agent execution
            # Each iteration yields one step: model call, tool call, or tool result
            with worker_context(name):
                for chunk in agent_graph.stream(state, stream_mode="updates"):
                    # chunk structure: {node_name: {messages: [...]}}
                    for node_name, node_output in chunk.items():
                        logger.debug(f"[{name}/{node_name}] Update received")

                        if "messages" in node_output:
                            # With stream_mode="updates", messages are already incremental updates
                            # No need to slice - just use them directly
                            new_msgs = node_output["messages"]
                            if not isinstance(new_msgs, list):
                                new_msgs = [new_msgs]

                            if new_msgs:
                                # YIELD update to main graph stream
                                # This makes the update IMMEDIATELY visible to UI
                                yield {"messages": new_msgs}

                                # Accumulate for final processing
                                all_new_msgs.extend(new_msgs)

            # Final update: Extract Plan if this is Planner
            if name == "Planner":
                for msg in all_new_msgs:
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            if tool_call["name"] == "submit_plan":
                                try:
                                    plan_data = tool_call["args"].get("plan")
                                    if plan_data:
                                        plan = Plan(**plan_data)
                                        yield {"plan": plan}
                                        logger.info(f"[{name}] Plan extracted")
                                except Exception as e:
                                    logger.error(
                                        f"[{name}] Plan extraction failed: {e}"
                                    )

            logger.info(f"[{name}] Completed with {len(all_new_msgs)} messages")

        return worker_node

    # Add worker nodes
    workflow.add_node("Planner", make_worker_node(planner_agent, "Planner"))
    workflow.add_node("Coder", make_worker_node(coder_agent, "Coder"))
    workflow.add_node("Reviewer", make_worker_node(reviewer_agent, "Reviewer"))

    # Add edges
    # Always from START to Supervisor
    workflow.add_edge(START, "Supervisor")

    # Supervisor routes based on next field
    workflow.add_conditional_edges(
        "Supervisor",
        lambda state: state["next"],
        {"Planner": "Planner", "Coder": "Coder", "Reviewer": "Reviewer", "FINISH": END},
    )

    # Workers return to Supervisor after completion
    workflow.add_edge("Planner", "Supervisor")
    workflow.add_edge("Coder", "Supervisor")
    workflow.add_edge("Reviewer", "Supervisor")

    # Compile graph
    return workflow.compile(checkpointer=MemorySaver())


# Export global Agent
agent_graph = create_multi_agent_graph()
