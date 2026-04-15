import asyncio
import httpx
import json

async def debug_test():
    # This is dummy since I don't have the test project setup here easily
    # I'll just run pytest and try to capture output better
    pass

if __name__ == "__main__":
    # Just run pytest and print to stdout
    import subprocess
    result = subprocess.run(
        ["python", "-m", "pytest", "apps/api/tests/modules/site_operations/test_track_b_completion.py::test_dpr_image_deletion", "-s", "-vv"],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    print("STDOUT:")
    print(result.stdout)
    print("STDERR:")
    print(result.stderr)
