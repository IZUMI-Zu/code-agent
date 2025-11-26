"""
═══════════════════════════════════════════════════════════════
文件操作工具集
═══════════════════════════════════════════════════════════════
实现原则：
  - 每个工具只做一件事（读/写/搜索）
  - 参数验证前置,避免深层嵌套
  - 错误信息清晰可操作
"""

from pathlib import Path
from typing import Any
from .base import BaseTool


# ═══════════════════════════════════════════════════════════════
# 文件读取工具
# ═══════════════════════════════════════════════════════════════

class ReadFileTool(BaseTool):
    """读取文件内容"""

    def __init__(self):
        super().__init__(
            name="read_file",
            description="读取指定路径的文件内容。返回文件的完整文本内容。"
        )

    def _run(self, file_path: str) -> str:
        path = Path(file_path)

        # 提前验证,避免深层嵌套
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        if not path.is_file():
            raise ValueError(f"路径不是文件: {file_path}")

        # 核心逻辑（无特殊情况）
        content = path.read_text(encoding="utf-8")
        return f"文件内容 ({len(content)} 字符):\n\n{content}"

    def _get_parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要读取的文件路径（绝对路径或相对路径）"
                }
            },
            "required": ["file_path"]
        }


# ═══════════════════════════════════════════════════════════════
# 文件写入工具
# ═══════════════════════════════════════════════════════════════

class WriteFileTool(BaseTool):
    """写入文件内容（覆盖模式）"""

    def __init__(self):
        super().__init__(
            name="write_file",
            description="将内容写入指定文件。如果文件已存在则覆盖,不存在则创建。"
        )

    def _run(self, file_path: str, content: str) -> str:
        path = Path(file_path)

        # 创建父目录（避免写入失败）
        path.parent.mkdir(parents=True, exist_ok=True)

        # 核心逻辑
        path.write_text(content, encoding="utf-8")
        return f"成功写入 {len(content)} 字符到: {file_path}"

    def _get_parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "目标文件路径"
                },
                "content": {
                    "type": "string",
                    "description": "要写入的内容"
                }
            },
            "required": ["file_path", "content"]
        }


# ═══════════════════════════════════════════════════════════════
# 文件列表工具
# ═══════════════════════════════════════════════════════════════

class ListFilesTool(BaseTool):
    """列出目录下的文件"""

    def __init__(self):
        super().__init__(
            name="list_files",
            description="列出指定目录下的所有文件和子目录。"
        )

    def _run(self, directory: str = ".") -> str:
        path = Path(directory)

        # 验证
        if not path.exists():
            raise FileNotFoundError(f"目录不存在: {directory}")

        if not path.is_dir():
            raise ValueError(f"路径不是目录: {directory}")

        # 核心逻辑（简洁遍历）
        items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))

        lines = [f"目录: {path.absolute()}\n"]
        for item in items:
            prefix = "📁" if item.is_dir() else "📄"
            lines.append(f"{prefix} {item.name}")

        return "\n".join(lines)

    def _get_parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "要列出的目录路径（默认为当前目录）",
                    "default": "."
                }
            }
        }
