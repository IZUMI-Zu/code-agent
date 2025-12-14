"""
Agent State Definition
"""

from collections.abc import Sequence
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

# Data Models


class Task(BaseModel):
    """
    Enhanced task model with dependencies and acceptance criteria
    """

    id: int = Field(..., description="Unique task ID")
    description: str = Field(..., description="Task description")
    status: Literal["pending", "in_progress", "completed"] = "pending"

    # Enhanced fields for better task management
    depends_on: list[int] = Field(
        default_factory=list,
        description="IDs of prerequisite tasks that must complete first",
    )
    priority: int = Field(default=0, description="Task priority (higher = more important, range 1-5)")
    acceptance_criteria: str = Field(default="", description="How to verify task completion (testable condition)")
    phase: Literal["scaffold", "core", "polish"] = Field(
        default="core",
        description="Task phase: scaffold (structure), core (features), polish (refinement)",
    )


class Plan(BaseModel):
    """Project plan structure"""

    tasks: list[Task] = Field(..., description="List of tasks")
    summary: str = Field(..., description="Plan summary")


# Core State Structure


class AgentState(TypedDict):
    """
    Agent Runtime State

    Design Points:
      - messages: Conversation history (auto-merged, no manual concatenation)
      - next: The next agent to execute
      - current_task: Current task description
      - is_finished: Termination flag (simple boolean, no complex enums)
      - plan: Structured project plan (Optional)
      - phase: Current workflow phase (planning, coding, reviewing, done)

    Enhanced for Feedback Loops:
      - iteration_count: Tracks loop iterations (prevents infinite loops)
      - max_iterations: Safety limit (based on LangGraph recursion best practices)
      - review_status: Reviewer's verdict (enables conditional routing)
      - issues_found: Concrete problems to fix (guides Coder)
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
    plan: Plan | None

    # Workflow phase: planning -> coding -> reviewing -> done
    phase: Literal["planning", "coding", "reviewing", "done"]

    # Feedback Loop Control (LangGraph Best Practice)
    iteration_count: int  # Current iteration number (0-indexed)
    max_iterations: int  # Safety limit to prevent infinite loops (default: 15)

    review_status: Literal["pending", "passed", "needs_fixes"]  # Reviewer's verdict
    issues_found: list[str]  # Specific issues identified by Reviewer


# Tool Execution Result (Unified Structure)


class ToolResult(TypedDict):
    """
    Unified encapsulation of tool execution results
    """

    tool_name: str  # Tool name
    success: bool  # Execution success flag
    output: str  # Output content (result on success, error message on failure)
    duration_ms: float  # Execution duration (for performance analysis)
