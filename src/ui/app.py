"""
═══════════════════════════════════════════════════════════════
TUI 应用主控制器
═══════════════════════════════════════════════════════════════
职责：
  - 管理用户输入循环
  - 调用 Agent 执行任务
  - 渲染执行结果
"""

from langchain_core.messages import HumanMessage
from rich.prompt import Prompt
from .components import (
    console,
    render_welcome,
    render_message,
    render_separator,
    show_thinking
)
from ..agent.graph import agent_graph


# ═══════════════════════════════════════════════════════════════
# TUI 应用类
# ═══════════════════════════════════════════════════════════════

class TUIApp:
    """
    TUI 应用的主控制器

    好品味体现：
      - 循环逻辑简洁,无深层嵌套
      - 状态管理交给 LangGraph,UI 只负责显示
    """

    def __init__(self):
        self.graph = agent_graph
        self.state = {
            "messages": [],
            "current_task": "",
            "is_finished": False
        }

    def run(self):
        """启动应用主循环"""
        render_welcome()

        while True:
            try:
                # 获取用户输入
                user_input = Prompt.ask("\n[bold cyan]你[/bold cyan]")

                # 退出命令
                if user_input.lower() in ["exit", "quit", "q"]:
                    console.print("\n[yellow]再见! 👋[/yellow]\n")
                    break

                # 跳过空输入
                if not user_input.strip():
                    continue

                # 处理用户请求
                self._handle_user_input(user_input)

                render_separator()

            except KeyboardInterrupt:
                console.print("\n\n[yellow]已中断[/yellow]\n")
                break
            except Exception as e:
                console.print(f"\n[red]错误: {e}[/red]\n")

    def _handle_user_input(self, user_input: str):
        """处理用户输入（内部方法）"""
        # 添加用户消息到状态
        user_message = HumanMessage(content=user_input)
        self.state["messages"].append(user_message)

        # 显示用户消息
        render_message(user_message)

        # 显示思考指示器
        progress = show_thinking()

        try:
            # 执行 Agent（流式处理）
            for event in self.graph.stream(self.state):
                # 更新状态
                for node_name, node_output in event.items():
                    if "messages" in node_output:
                        new_messages = node_output["messages"]

                        # 渲染新消息
                        for msg in new_messages:
                            # 停止思考指示器（首次输出时）
                            if progress:
                                progress.stop()
                                progress = None

                            render_message(msg)

                        # 更新本地状态
                        self.state["messages"].extend(new_messages)

        finally:
            # 确保停止进度条
            if progress:
                progress.stop()


# ═══════════════════════════════════════════════════════════════
# 应用入口
# ═══════════════════════════════════════════════════════════════

def main():
    """启动 TUI 应用"""
    app = TUIApp()
    app.run()


if __name__ == "__main__":
    main()
