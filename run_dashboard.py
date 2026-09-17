from pathlib import Path
import os
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
APP_FILE = PROJECT_ROOT / "app.py"


def main() -> None:
    if not VENV_PYTHON.exists():
        print(
            "Virtual environment not found. Run the first-time setup commands "
            "in README.md before starting the dashboard.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    command = [
        str(VENV_PYTHON),
        "-m",
        "streamlit",
        "run",
        str(APP_FILE),
    ]
    environment = os.environ.copy()
    environment["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

    try:
        raise SystemExit(
            subprocess.call(command, cwd=PROJECT_ROOT, env=environment)
        )
    except KeyboardInterrupt:
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
