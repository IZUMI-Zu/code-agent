"""
═══════════════════════════════════════════════════════════════
Agent State Definition - Single Source of Truth for Data Flow
═══════════════════════════════════════════════════════════════
Design Philosophy:
  - Immutability: Clear and traceable state transitions
  - No Special Cases: All messages follow a unified structure
  - Simplicity: Store only necessary data, avoid redundancy
"""

from typing import Annotated, List, Literal, Optional, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

# ═══════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════


class Task(BaseModel):
    """Single task in the plan"""

    id: int = Field(..., description="Unique task ID")
    description: str = Field(..., description="Task description")
    status: Literal["pending", "in_progress", "completed"] = "pending"


class Plan(BaseModel):
    """Project plan structure"""

    tasks: List[Task] = Field(..., description="List of tasks")
    summary: str = Field(..., description="Plan summary")


# ═══════════════════════════════════════════════════════════════
# Core State Structure
# ═══════════════════════════════════════════════════════════════


class AgentState(TypedDict):
    """
    Agent Runtime State

    Design Points:
      - messages: Conversation history (auto-merged, no manual concatenation)
      - next: The next agent to execute
      - current_task: Current task description
      - is_finished: Termination flag (simple boolean, no complex enums)
      - plan: Structured project plan (Optional)
    """

    # Message stream (LangGraph handles appending logic automatically)
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # The next agent to execute
    next: str

    # Current task context
    current_task: str

    # Termination flag (simple binary, avoiding multi-state complexity)
    is_finished: bool

    # Structured Plan
    plan: Optional[Plan]


# ═══════════════════════════════════════════════════════════════
# Tool Execution Result (Unified Structure)
# ═══════════════════════════════════════════════════════════════


class ToolResult(TypedDict):
    """
    Unified encapsulation of tool execution results

    Good Taste:
      - Success/Failure use the same structure, eliminating if/else
      - output field unifies results, no need to distinguish types
    """

    tool_name: str  # Tool name
    success: bool  # Execution success flag
    output: str  # Output content (result on success, error message on failure)
    duration_ms: float  # Execution duration (for performance analysis)
