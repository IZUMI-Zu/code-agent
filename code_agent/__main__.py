import argparse
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
    args = parse_args()
    workspace_path = Path(args.workspace).expanduser().resolve()
    from code_agent.config import settings

    settings.override_workspace(workspace_path)

    print(f"📂 Workspace set to: {workspace_path}")

    from code_agent.ui.app import main as run_app

    run_app()


if __name__ == "__main__":
    main()
