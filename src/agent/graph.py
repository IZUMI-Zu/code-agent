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

    # Add nodes
    workflow.add_node("Supervisor", supervisor_node)

    # Wrap worker agent to adapt to graph node
    def make_node(agent, name):
        def node(state: AgentState):
            logger.info(f"Agent {name} is working...")
            # Call agent
            result = agent.invoke(state)
            # Return newly generated messages
            # result["messages"] contains full history, we need to slice to get new parts
            num_old = len(state["messages"])
            new_msgs = result["messages"][num_old:]
            logger.info(f"Agent {name} finished with {len(new_msgs)} new messages.")

            update = {"messages": new_msgs}

            # Special handling for Planner to extract Plan
            if name == "Planner":
                for msg in new_msgs:
                    if hasattr(msg, "tool_calls"):
                        for tool_call in msg.tool_calls:
                            if tool_call["name"] == "submit_plan":
                                try:
                                    plan_data = tool_call["args"].get("plan")
                                    if plan_data:
                                        # plan_data is a dict here
                                        plan = Plan(**plan_data)
                                        update["plan"] = plan
                                        logger.info("Plan updated in state.")
                                except Exception as e:
                                    logger.error(f"Failed to parse plan: {e}")

            return update

        return node

    workflow.add_node("Planner", make_node(planner_agent, "Planner"))
    workflow.add_node("Coder", make_node(coder_agent, "Coder"))
    workflow.add_node("Reviewer", make_node(reviewer_agent, "Reviewer"))

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
