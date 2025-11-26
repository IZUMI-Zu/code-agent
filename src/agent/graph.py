"""
═══════════════════════════════════════════════════════════════
Agent 核心 - Code Agent
═══════════════════════════════════════════════════════════════
设计哲学：
  "做一件事,做到极致"
  - 不要多个变体,只要一个能干活的 Agent
  - 不要过度配置,合理的默认值就够了
"""

from langchain_anthropic import ChatAnthropic
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from ..tools.registry import get_registry


# ═══════════════════════════════════════════════════════════════
# 创建 Code Agent
# ═══════════════════════════════════════════════════════════════


def create_code_agent():
    """
    创建 Code Agent

    简洁执念:
      - Claude 3.5 Sonnet
      - 所有工具
      - 持久化(多轮对话)
      - 无中间件(保持简单)

    用法:
        agent = create_code_agent()
        result = agent.invoke(
            {"messages": [HumanMessage("读取 main.py")]},
            {"configurable": {"thread_id": "session_1"}}
        )
    """
    # 初始化模型
    model = ChatAnthropic(
        model_name="claude-3-5-sonnet-20241022", temperature=0, timeout=60, stop=None
    )

    # 获取所有工具
    registry = get_registry()
    tools = [tool.to_langchain_tool() for tool in registry.get_all_tools()]

    # 创建 Agent
    agent = create_agent(model=model, tools=tools, checkpointer=MemorySaver())

    return agent


# ═══════════════════════════════════════════════════════════════
# 导出全局 Agent
# ═══════════════════════════════════════════════════════════════

agent_graph = create_code_agent()
