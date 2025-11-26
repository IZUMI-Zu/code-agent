"""
═══════════════════════════════════════════════════════════════
Agent 状态定义 - 数据流的单一真相源
═══════════════════════════════════════════════════════════════
设计哲学：
  - 不可变思维：状态流转清晰可追溯
  - 消除特殊情况：所有消息都是统一结构
  - 简洁执念：只存必要数据,避免冗余
"""

from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


# ═══════════════════════════════════════════════════════════════
# 核心状态结构
# ═══════════════════════════════════════════════════════════════

class AgentState(TypedDict):
    """
    Agent 运行时状态

    设计要点：
      - messages: 对话历史（自动合并,消除手动拼接）
      - current_task: 当前执行任务描述
      - is_finished: 终止标志（简单布尔,无复杂枚举）
    """
    # 消息流（LangGraph 自动处理追加逻辑）
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # 当前任务上下文
    current_task: str

    # 终止标志（简单二值,避免多状态复杂度）
    is_finished: bool


# ═══════════════════════════════════════════════════════════════
# 工具调用结果（统一结构）
# ═══════════════════════════════════════════════════════════════

class ToolResult(TypedDict):
    """
    工具执行结果的统一封装

    好品味体现：
      - 成功/失败用同一结构,消除 if/else
      - output 字段统一承载结果,无需区分类型
    """
    tool_name: str      # 工具名称
    success: bool       # 执行成功标志
    output: str         # 输出内容（成功时是结果,失败时是错误信息）
    duration_ms: float  # 执行耗时（便于性能分析）
