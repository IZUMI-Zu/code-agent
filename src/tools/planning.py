from typing import Type

from pydantic import BaseModel, Field

from ..agent.state import Plan
from .base import BaseTool


class SubmitPlanArgs(BaseModel):
    plan: Plan = Field(..., description="The structured plan to submit")


class SubmitPlanTool(BaseTool):
    """Tool for submitting the project plan"""

    def __init__(self):
        super().__init__(
            name="submit_plan",
            description="Submit the finalized project plan. Use this when you have analyzed the requirements and created a task breakdown.",
        )

    def _run(self, plan: Plan) -> str:
        # In a real scenario, this might save to a database or file
        # Here we just return a success message.
        # The actual state update will be handled by the graph node inspecting the tool call.
        return f"Plan submitted with {len(plan.tasks)} tasks."

    def get_args_schema(self) -> Type[BaseModel]:
        return SubmitPlanArgs
