"""
═══════════════════════════════════════════════════════════════
Shell 命令执行工具
═══════════════════════════════════════════════════════════════
安全设计：
  - 限制超时时间（防止僵尸进程）
  - 捕获 stderr（提供完整诊断信息）
  - 明确工作目录（避免路径混淆）
"""

import subprocess
from pathlib import Path
from typing import Any
from .base import BaseTool


# ═══════════════════════════════════════════════════════════════
# Shell 执行工具
# ═══════════════════════════════════════════════════════════════

class ShellTool(BaseTool):
    """执行 Shell 命令"""

    def __init__(self, timeout: int = 30):
        super().__init__(
            name="shell",
            description="在系统 Shell 中执行命令。返回标准输出和标准错误。"
        )
        self.timeout = timeout

    def _run(self, command: str, cwd: str = ".") -> str:
        # 验证工作目录
        work_dir = Path(cwd).resolve()
        if not work_dir.exists():
            raise FileNotFoundError(f"工作目录不存在: {cwd}")

        # 执行命令（统一处理超时和错误）
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=self.timeout
        )

        # 构造输出（成功失败都返回完整信息）
        output_lines = [
            f"命令: {command}",
            f"工作目录: {work_dir}",
            f"返回码: {result.returncode}",
            ""
        ]

        if result.stdout:
            output_lines.extend([
                "─── 标准输出 ───",
                result.stdout.strip()
            ])

        if result.stderr:
            output_lines.extend([
                "─── 标准错误 ───",
                result.stderr.strip()
            ])

        # 失败时抛出异常（让基类捕获）
        if result.returncode != 0:
            raise RuntimeError("\n".join(output_lines))

        return "\n".join(output_lines)

    def _get_parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的 Shell 命令"
                },
                "cwd": {
                    "type": "string",
                    "description": "命令执行的工作目录（默认为当前目录）",
                    "default": "."
                }
            },
            "required": ["command"]
        }
