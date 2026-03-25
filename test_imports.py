import sys
import os

# Add apps/api to path
sys.path.append(os.path.join(os.getcwd(), "apps", "api"))

try:
    from execution.scheduler.api.routes.scheduler import router
    print("SUCCESS: Imported scheduler router")
except Exception as e:
    print(f"FAILURE: {e}")
    import traceback
    traceback.print_exc()
