import os
import sys

# Add the current directory to sys.path
sys.path.append(os.getcwd())

try:
    from server import app  # noqa: F401

    print("App imported successfully")
except Exception as e:
    print(f"Error importing app: {e}")
    import traceback

    traceback.print_exc()
