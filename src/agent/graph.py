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

# 1. Planner Agent
planner_agent = create_worker("Planner", PLANNER_PROMPT, lc_tools)

# 2. Coder Agent
coder_agent = create_worker("Coder", CODER_PROMPT, lc_tools)

# 3. Reviewer Agent
reviewer_agent = create_worker("Reviewer", REVIEWER_PROMPT, lc_tools)

# ═══════════════════════════════════════════════════════════════
# Supervisor (Orchestrator)
# ═══════════════════════════════════════════════════════════════

members = ["Planner", "Coder", "Reviewer"]
options = ["FINISH"] + members


class Router(BaseModel):
    """Worker selection router"""

    next: Literal["Planner", "Coder", "Reviewer", "FINISH"]


def supervisor_node(state: AgentState):
    """Supervisor Node: Decides the next executor"""
    messages = state["messages"]

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SUPERVISOR_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="messages"),
            (
                "system",
                "Given the conversation above, who should act next?"
                " Or should we FINISH? Select one of: {options}",
            ),
        ]
    ).partial(options=str(options), members=", ".join(members))

    model = get_model()
    # Use with_structured_output to enforce structured output
    chain = prompt | model.with_structured_output(Router)

    logger.info("Supervisor is deciding the next step...")
    result = cast(Router, chain.invoke({"messages": messages}))
    logger.info(f"Supervisor decided: {result.next}")

    return {"next": result.next}


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
                            # Extract only NEW messages from this update
                            full_msgs = node_output["messages"]
                            new_msgs = full_msgs[num_old_msgs:]

                            if new_msgs:
                                # YIELD update to main graph stream
                                # This makes the update IMMEDIATELY visible to UI
                                yield {"messages": new_msgs}

                                # Accumulate for final processing
                                all_new_msgs.extend(new_msgs)
                                num_old_msgs = len(full_msgs)

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
