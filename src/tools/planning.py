from typing import Type

from pydantic import BaseModel, Field

from ..agent.state import Plan
from .base import BaseTool


# ═══════════════════════════════════════════════════════════════
# Custom Exception for Plan Submission
# ═══════════════════════════════════════════════════════════════
# This exception is used to signal that the plan has been submitted
# and the agent should stop immediately. The worker node catches this
# exception and extracts the plan from it.
#
# Why use an exception instead of Command?
# - Command only updates state, doesn't stop the agent loop
# - Exception immediately terminates the tool-calling loop
# - Worker node can catch it and handle gracefully
# ═══════════════════════════════════════════════════════════════


class PlanSubmittedException(Exception):
    """Raised when a plan is submitted to signal immediate termination"""

    def __init__(self, plan: Plan):
        self.plan = plan
        super().__init__(f"Plan submitted with {len(plan.tasks)} tasks")


class SubmitPlanArgs(BaseModel):
    plan: Plan = Field(..., description="The structured plan to submit")


class SubmitPlanTool(BaseTool):
    """Tool for submitting the project plan

    Uses a custom exception to immediately terminate the agent loop.
    This is more reliable than prompt-based "STOP NOW" instructions.

    The exception is caught by the worker node, which extracts the plan
    and returns it to the supervisor for routing to the Coder.
    """

    def __init__(self):
        super().__init__(
            name="submit_plan",
            description="Submit the finalized project plan. Use this when you have analyzed the requirements and created a task breakdown. After calling this tool, the Coder agent will automatically take over - you do NOT need to do anything else.",
        )

    def _run(self, plan: Plan) -> str:
        """
        Submit plan by raising PlanSubmittedException.

        This immediately terminates the agent loop. The worker node
        catches this exception and extracts the plan for state update.
        """
        # Raise exception to immediately stop the agent loop
        # The worker node will catch this and handle it gracefully
        raise PlanSubmittedException(plan)

    def get_args_schema(self) -> Type[BaseModel]:
        return SubmitPlanArgs
