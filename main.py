"""
═══════════════════════════════════════════════════════════════
TUI Code Agent - 入口点
═══════════════════════════════════════════════════════════════
"""

import argparse
import os
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="TUI Code Agent")
    parser.add_argument(
        "--workspace",
        "-w",
        type=str,
        default=".",
        help="Path to the workspace directory (default: current directory)",
    )
    return parser.parse_args()


def main():
    """启动 TUI Code Agent"""
    args = parse_args()

    # Set workspace path in environment variable
    # This must be done BEFORE importing src.config (which is imported by src.ui.app)
    workspace_path = Path(args.workspace).resolve()
    os.environ["WORKSPACE_ROOT"] = str(workspace_path)

    print(f"📂 Workspace set to: {workspace_path}")

    # Import app after setting environment variables
    from src.ui.app import main as run_app

    run_app()


if __name__ == "__main__":
    main()
