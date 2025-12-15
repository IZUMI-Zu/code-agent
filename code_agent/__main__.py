import argparse
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="TUI Code Agent")
    parser.add_argument(
        "--workspace",
        "-w",
        type=str,
        default=None,  # None = use .env config or current directory
        help="Path to the workspace directory (default: from .env WORKSPACE_ROOT, or current directory)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    from code_agent.config import settings

    if args.workspace is not None:
        # User explicitly specified -w, override .env config
        workspace_path = Path(args.workspace).expanduser().resolve()
        settings.override_workspace(workspace_path)
        print(f"📂 Workspace: {settings.workspace_root} (from -w)")
    else:
        # Use .env config (Pydantic auto-loads WORKSPACE_ROOT)
        # Ensure relative paths from .env are resolved to absolute
        if not settings.workspace_root.is_absolute():
            settings.workspace_root = settings.workspace_root.resolve()
        print(f"📂 Workspace: {settings.workspace_root}")

    from code_agent.ui.app import main as run_app

    run_app()


if __name__ == "__main__":
    main()
