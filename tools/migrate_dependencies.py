import os
import re

routes_dir = r"d:\_repos\TAC-PMC-CRM\apps\api\app\api\v1"

for filename in os.listdir(routes_dir):
    if not filename.endswith("_routes.py"):
        continue
    
    filepath = os.path.join(routes_dir, filename)
    with open(filepath, 'r') as f:
        content = f.read()

    # Identify imports from dependencies and deps
    dep_match = re.search(r"from app\.core\.dependencies import (.*)", content)
    deps_match = re.search(r"from app\.core\.deps import (.*)", content)
    
    if deps_match:
        deps_items = [i.strip() for i in deps_match.group(1).split(",")]
        
        if dep_match:
            dep_items = [i.strip() for i in dep_match.group(1).split(",")]
            # Merge
            all_items = sorted(list(set(dep_items + deps_items)))
            merged_import = f"from app.core.dependencies import {', '.join(all_items)}"
            
            # Replace dep_match line and remove deps_match line
            content = content.replace(dep_match.group(0), merged_import)
            content = content.replace(deps_match.group(0) + "\n", "")
            content = content.replace(deps_match.group(0), "") # Just in case no newline
        else:
            # Just rename deps to dependencies
            content = content.replace("app.core.deps", "app.core.dependencies")
            
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"MIGRATED: {filename}")
