import subprocess
import sys

def run_pytest():
    cmd = [
        "python", "-m", "pytest", 
        "apps/api/tests/modules/tasks/test_api.py", 
        "-k", "test_create_task", 
        "-vv", 
        "--log-cli-level=DEBUG"
    ]
    process = subprocess.Popen(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    while True:
        line = process.stdout.readline()
        if not line:
            break
        if "SYSTEM_FAULT" in line or "Error" in line or "Traceback" in line:
             print(line.strip())
        # To avoid too much output, we can filter or just print everything if it's small
        # Since we use -k test_create_task, it should be small.
        print(line.strip())

    process.wait()

if __name__ == "__main__":
    run_pytest()
