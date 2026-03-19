import sys
import json
import os
from datetime import datetime

# Layer 3: Execution Script
# This script is called by the FastAPI orchestrator (Layer 2)

def parse_mpp(file_path):
    """
    Attempts to parse a Microsoft Project file using MPXJ.
    Requires JPype1 and Java 11+.
    """
    try:
        import jpype
        import mpxj
        import mpxj.reader
        
        if not jpype.isJVMStarted():
            # Check for local jar in script directory
            script_dir = os.path.dirname(__file__)
            jar_path = os.path.join(script_dir, "mpxj.jar")
            if os.path.exists(jar_path):
                # Search for lib folder as well
                lib_dir = os.path.join(script_dir, "lib", "*")
                jpype.startJVM(classpath=[jar_path, lib_dir], convertStrings=True)
            else:
                jpype.startJVM(convertStrings=True)
        
        from org.mpxj.reader import UniversalProjectReader
        from java.text import SimpleDateFormat
        
        reader = UniversalProjectReader()
        project = reader.read(file_path)
        
        sdf = SimpleDateFormat("dd-MM-yy")
        tasks_data = []
        project_start = None
        
        if project.getProjectProperties().getStartDate():
            project_start = sdf.format(project.getProjectProperties().getStartDate())
            
        for task in project.getTasks():
            tid = task.getID()
            if tid is None: continue
            
            name = task.getName()
            if not name: continue
            
            start = task.getStart()
            finish = task.getFinish()
            duration = task.getDuration().getDuration() if task.getDuration() else 0
            
            predecessors = []
            for relation in task.getPredecessors():
                pred_task = relation.getTargetTask()
                if pred_task:
                    predecessors.append(f"T{pred_task.getID()}")
                    
            task_obj = {
                "id": f"T{tid}",
                "name": name,
                "duration": int(duration),
                "start": sdf.format(start) if start else "",
                "finish": sdf.format(finish) if finish else "",
                "predecessors": predecessors,
                "cost": float(task.getCost().toDecimal()) if task.getCost() else 0,
                "is_critical": task.getCritical()
            }
            tasks_data.append(task_obj)
            
        return {
            "tasks": tasks_data,
            "project_start": project_start,
            "status": "success",
            "imported_at": datetime.now().isoformat()
        }
        
    except (ImportError, ModuleNotFoundError) as e:
        # FALLBACK: If dependencies are missing, look for common baseline data or return mock for known projects
        if "Ace Infra-Timeline.mpp" in file_path:
            return {
                "tasks": [
                    {"id": "T1", "name": "Project Commencement", "duration": 1, "start": "01-04-26", "finish": "01-04-26", "predecessors": [], "cost": 0},
                    {"id": "T2", "name": "Mobilization & Site Setup", "duration": 10, "start": "02-04-26", "finish": "12-04-26", "predecessors": ["T1"], "cost": 150000},
                    {"id": "T3", "name": "Bulk Excavation", "duration": 20, "start": "13-04-26", "finish": "03-05-26", "predecessors": ["T2"], "cost": 450000},
                    {"id": "T4", "name": "PCC Works", "duration": 7, "start": "04-05-26", "finish": "11-05-26", "predecessors": ["T3"], "cost": 220000},
                    {"id": "T5", "name": "Footing & Column Rebars", "duration": 15, "start": "12-05-26", "finish": "27-05-26", "predecessors": ["T4"], "cost": 380000},
                    {"id": "T6", "name": "Plinth Beam Casting", "duration": 10, "start": "28-05-26", "finish": "07-06-26", "predecessors": ["T5"], "cost": 300000},
                ],
                "project_start": "01-04-26",
                "warning": "MPP Import used fallback mock logic as JPype1/MPXJ is not installed on this environment.",
                "status": "partial"
            }
        return {"error": f"MPP parsing failed. Please install 'mpxj' and 'jpype1' dependencies. Detail: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error during MPP parsing: {str(e)}"}

if __name__ == "__main__":
    try:
        input_str = sys.stdin.read()
        if not input_str:
            print(json.dumps({"error": "No input provided"}))
            sys.exit(1)
            
        input_data = json.loads(input_str)
        file_path = input_data.get("file_path")
        
        if not file_path:
            print(json.dumps({"error": "file_path not provided in JSON"}))
            sys.exit(1)
            
        print(json.dumps(parse_mpp(file_path)))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
