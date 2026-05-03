
import sys
import os

# Add apps/api to path
sys.path.append(os.path.join(os.getcwd(), "apps", "api"))

from app.main import app

for route in app.routes:
    if hasattr(route, "path"):
        print(f"{route.methods} {route.path}")
    elif hasattr(route, "routes"):
        for subroute in route.routes:
            print(f"{subroute.methods} {subroute.path}")
