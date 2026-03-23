import sys
import json
import os
from datetime import datetime
import xml.etree.ElementTree as ET

# Layer 3: Execution Script
# This script is called by the FastAPI orchestrator (Layer 2)

def parse_mspdi_xml(file_path):
    """
    Parses a Microsoft Project Data Interchange (MSPDI) XML file.
    MSPDI is the standard XML export format from Microsoft Project.
    Requires: File → Save As → XML Format in Microsoft Project
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        # MSPDI namespace
        ns = {
            'p': 'http://schemas.microsoft.com/office/project/2003/api/pe'
        }

        # Try to find elements with or without namespace
        def find_text(element, path, default=""):
            """Safely find text in XML element with namespace handling"""
            # First try with namespace
            result = element.find(f'p:{path}', ns)
            if result is None:
                result = element.find(path)
            return result.text if result is not None else default

        # Get project start date
        project_start = None
        project_elem = root.find('.//p:Project', ns) or root.find('.//Project')
        if project_elem is not None:
            start_date = find_text(project_elem, 'StartDate')
            if start_date:
                # Parse ISO date and format as DD-MM-YY
                try:
                    from datetime import datetime as dt
                    parsed_date = dt.fromisoformat(start_date.split('T')[0])
                    project_start = parsed_date.strftime("%d-%m-%y")
                except:
                    project_start = None

        tasks_data = []

        # Parse all tasks
        tasks_elem = root.findall('.//p:Tasks/p:Task', ns)
        if not tasks_elem:
            tasks_elem = root.findall('.//Tasks/Task')

        for task_elem in tasks_elem:
            # Skip if task has no ID or is a template
            uid = find_text(task_elem, 'UID', "")
            if not uid:
                continue

            task_id = find_text(task_elem, 'ID', "0")
            name = find_text(task_elem, 'Name', "")

            if not name:
                continue

            # Duration (in minutes in MSPDI, convert to days)
            duration_str = find_text(task_elem, 'Duration', "0")
            try:
                # Duration is in minutes, divide by 480 (8 hours * 60 min)
                duration_minutes = int(duration_str.replace('pt', '').replace('m', '')) if duration_str else 0
                duration = max(0, duration_minutes // 480)
            except:
                duration = 0

            # Start date
            start_str = find_text(task_elem, 'Start', "")
            start = ""
            if start_str:
                try:
                    from datetime import datetime as dt
                    parsed_start = dt.fromisoformat(start_str.split('T')[0])
                    start = parsed_start.strftime("%d-%m-%y")
                except:
                    pass

            # Finish date
            finish_str = find_text(task_elem, 'Finish', "")
            finish = ""
            if finish_str:
                try:
                    from datetime import datetime as dt
                    parsed_finish = dt.fromisoformat(finish_str.split('T')[0])
                    finish = parsed_finish.strftime("%d-%m-%y")
                except:
                    pass

            # Cost
            cost_str = find_text(task_elem, 'Cost', "0")
            try:
                cost = float(cost_str.replace('$', '').replace(',', '')) if cost_str else 0
            except:
                cost = 0

            # Percent Complete
            pct_complete_str = find_text(task_elem, 'PercentComplete', "0")
            try:
                pct_complete = int(pct_complete_str) if pct_complete_str else 0
            except:
                pct_complete = 0

            # Predecessors (PredecessorLink elements)
            predecessors = []
            pred_links = task_elem.findall('.//p:PredecessorLink', ns) or task_elem.findall('.//PredecessorLink')
            for pred_link in pred_links:
                pred_uid = find_text(pred_link, 'PredecessorUID', "")
                # In a full implementation, map UID to task ID
                # For now, add as reference
                if pred_uid:
                    predecessors.append(f"T{pred_uid}")

            # Critical path flag (if available)
            is_critical = False
            try:
                critical_str = find_text(task_elem, 'Critical', "false")
                is_critical = critical_str.lower() == 'true'
            except:
                pass

            # Is milestone (0 duration or Milestone field)
            is_milestone = duration == 0

            # Actual Start/Finish (if available)
            actual_start_str = find_text(task_elem, 'ActualStart', "")
            actual_start = None
            if actual_start_str:
                try:
                    from datetime import datetime as dt
                    parsed_actual_start = dt.fromisoformat(actual_start_str.split('T')[0])
                    actual_start = parsed_actual_start.strftime("%d-%m-%y")
                except:
                    pass

            actual_finish_str = find_text(task_elem, 'ActualFinish', "")
            actual_finish = None
            if actual_finish_str:
                try:
                    from datetime import datetime as dt
                    parsed_actual_finish = dt.fromisoformat(actual_finish_str.split('T')[0])
                    actual_finish = parsed_actual_finish.strftime("%d-%m-%y")
                except:
                    pass

            # Baseline Start/Finish (if available)
            baseline_start_str = find_text(task_elem, 'BaselineStart', "")
            baseline_start = None
            if baseline_start_str:
                try:
                    from datetime import datetime as dt
                    parsed_baseline_start = dt.fromisoformat(baseline_start_str.split('T')[0])
                    baseline_start = parsed_baseline_start.strftime("%d-%m-%y")
                except:
                    pass

            baseline_finish_str = find_text(task_elem, 'BaselineFinish', "")
            baseline_finish = None
            if baseline_finish_str:
                try:
                    from datetime import datetime as dt
                    parsed_baseline_finish = dt.fromisoformat(baseline_finish_str.split('T')[0])
                    baseline_finish = parsed_baseline_finish.strftime("%d-%m-%y")
                except:
                    pass

            task_obj = {
                "id": f"T{task_id}",
                "name": name,
                "duration": duration,
                "start": start,
                "finish": finish,
                "predecessors": predecessors,
                "cost": cost,
                "percentComplete": pct_complete,
                "is_critical": is_critical,
                "isMilestone": is_milestone,
                "actualStart": actual_start,
                "actualFinish": actual_finish,
                "baselineStart": baseline_start,
                "baselineFinish": baseline_finish
            }
            tasks_data.append(task_obj)

        return {
            "tasks": tasks_data,
            "project_start": project_start,
            "status": "success",
            "imported_at": datetime.now().isoformat(),
            "source": "MSPDI XML"
        }

    except ET.ParseError as e:
        return {"error": f"Failed to parse XML file: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error during XML parsing: {str(e)}"}


def parse_mpp(file_path):
    """
    Attempts to parse a Microsoft Project binary file (.mpp).
    This requires JPype1 and MPXJ Java library.

    NOTE: Since Python 3.14 is not yet supported by JPype1,
    we recommend exporting from Microsoft Project as XML instead.
    """
    try:
        import jpype
        import mpxj.reader

        if not jpype.isJVMStarted():
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
            if tid is None:
                continue

            name = task.getName()
            if not name:
                continue

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
                "is_critical": task.getCritical(),
                "isMilestone": duration == 0
            }
            tasks_data.append(task_obj)

        return {
            "tasks": tasks_data,
            "project_start": project_start,
            "status": "success",
            "imported_at": datetime.now().isoformat(),
            "source": "MPP Binary (MPXJ)"
        }

    except (ImportError, ModuleNotFoundError):
        return {
            "error": (
                "MPP binary parsing requires JPype1 and Java 11+. "
                "Since Python 3.14 is not yet supported by JPype1, "
                "please export from Microsoft Project as XML instead: "
                "File → Save As → XML Format. "
                "XML files can be imported without any additional dependencies."
            ),
            "status": "unsupported"
        }
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

        # Detect file type by extension
        if file_path.lower().endswith('.xml'):
            result = parse_mspdi_xml(file_path)
        elif file_path.lower().endswith('.mpp'):
            result = parse_mpp(file_path)
        else:
            result = {"error": "Unsupported file type. Please use .xml or .mpp"}

        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
