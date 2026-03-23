import sys
import json
import os
from datetime import datetime

# Layer 3: Execution Script
# Parses Microsoft Project Gantt chart PDFs (tracking/progress reports)

def parse_tracking_pdf(file_path):
    """
    Parses a Microsoft Project Gantt chart PDF export (e.g., CIV_Rajesh_Tracking_14032026.pdf).
    Extracts the structured data grid from the left side of the PDF.
    """
    try:
        import pdfplumber

        def find_column_indices(header_row):
            """Helper to map keywords to column indices based on header text"""
            indices = {
                "id": None,
                "name": None,
                "duration": None,
                "start": None,
                "finish": None,
                "predecessors": None,
                "cost": None,
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": None,
                "remaining_duration": None,
                "baseline_duration": None,
                "baseline_start": None,
                "baseline_finish": None
            }
            
            if not header_row:
                return indices
                
            for i, cell in enumerate(header_row):
                if not cell:
                    continue
                cell_text = str(cell).lower().replace('\n', ' ')
                
                if "id" == cell_text.strip():
                    indices["id"] = i
                elif "task name" in cell_text or "name" == cell_text.strip():
                    indices["name"] = i
                elif "baseline" in cell_text and "duration" in cell_text:
                    indices["baseline_duration"] = i
                elif "baseline" in cell_text and "start" in cell_text:
                    indices["baseline_start"] = i
                elif "baseline" in cell_text and "finish" in cell_text:
                    indices["baseline_finish"] = i
                elif "actual" in cell_text and "start" in cell_text:
                    indices["actual_start"] = i
                elif "actual" in cell_text and "finish" in cell_text:
                    indices["actual_finish"] = i
                elif "duration" in cell_text and "baseline" not in cell_text:
                    indices["duration"] = i
                elif "start" in cell_text and "baseline" not in cell_text and "actual" not in cell_text:
                    indices["start"] = i
                elif "finish" in cell_text and "baseline" not in cell_text and "actual" not in cell_text:
                    indices["finish"] = i
                elif "predecessor" in cell_text:
                    indices["predecessors"] = i
                elif "cost" in cell_text:
                    indices["cost"] = i
                elif "% comp" in cell_text or "complete" in cell_text:
                    indices["percent_complete"] = i
                elif "rem" in cell_text and "dur" in cell_text:
                    indices["remaining_duration"] = i
                    
            return indices

        with pdfplumber.open(file_path) as pdf:
            tasks_data = []
            project_name = None
            project_start = None
            debug_info = {
                "total_pages": len(pdf.pages),
                "tables_per_page": [],
                "headers_found": []
            }

            for page_num, page in enumerate(pdf.pages):
                # Extract tables from the page
                tables = page.extract_tables()
                debug_info["tables_per_page"].append(len(tables) if tables else 0)

                if not tables:
                    continue

                for table_idx, table in enumerate(tables):
                    if len(table) < 2:
                        continue

                    # Find the header row (contains "ID", "Task Name", etc.)
                    header_row_idx = None
                    col_map = None
                    for i, row in enumerate(table):
                        if row and len(row) > 0:
                            # Check if this looks like a header row
                            row_str = str(row).lower()
                            if "id" in row_str and ("task" in row_str or "name" in row_str):
                                header_row_idx = i
                                col_map = find_column_indices(row)
                                debug_info["headers_found"].append({
                                    "page": page_num,
                                    "table": table_idx,
                                    "row": i,
                                    "columns": len(row),
                                    "map": {k: v for k, v in col_map.items() if v is not None}
                                })
                                break

                    if header_row_idx is None or col_map is None:
                        continue

                    # Process data rows
                    for row_idx in range(header_row_idx + 1, len(table)):
                        row = table[row_idx]
                        if not row or len(row) < 5: # Relaxed column count
                            continue

                        # Get ID column
                        idx_id = col_map["id"]
                        if idx_id is None: continue
                        task_id = str(row[idx_id]).strip() if len(row) > idx_id and row[idx_id] else ""

                        # Check if this is a valid data row
                        if not task_id or (not task_id.isdigit() and task_id != "0"):
                            continue

                        # Skip footer rows
                        if "page" in task_id.lower() or "legend" in task_id.lower():
                            continue

                        try:
                            task_id_num = int(task_id)

                            # Extract data using the column map
                            def get_cell(key, default=""):
                                idx = col_map[key]
                                if idx is not None and len(row) > idx and row[idx] is not None:
                                    return str(row[idx]).strip()
                                return default

                            task_name = get_cell("name", "Task")
                            
                            # Clean up task name
                            # Preserve symbols but remove trailing Gantt bleed if any
                            task_name = task_name.strip()
                            # If there's high-ASCII or weird bleed characters at the end, 
                            # we could try to trim them, but simple strip is safer for now.

                            if not task_name or task_name == "Task":
                                continue

                            # Duration
                            idx_dur = col_map["duration"]
                            duration = 0
                            if idx_dur is not None:
                                duration_str = get_cell("duration", "0")
                                try:
                                    duration = int(duration_str.split()[0])
                                except:
                                    duration = 0

                            # Baseline Duration
                            idx_bdur = col_map["baseline_duration"]
                            baseline_duration = 0
                            if idx_bdur is not None:
                                bduration_str = get_cell("baseline_duration", "0")
                                try:
                                    baseline_duration = int(bduration_str.split()[0])
                                except:
                                    baseline_duration = 0

                            # Dates
                            start = get_cell("start")
                            finish = get_cell("finish")
                            baseline_start = get_cell("baseline_start")
                            baseline_finish = get_cell("baseline_finish")
                            actual_start = get_cell("actual_start")
                            actual_finish = get_cell("actual_finish")

                            if actual_start and actual_start.upper() == "NA": actual_start = None
                            if actual_finish and actual_finish.upper() == "NA": actual_finish = None

                            # Cost
                            cost_str = get_cell("cost", "0")
                            cost = 0
                            if cost_str:
                                # Clean up currency symbols and commas
                                clean_cost = cost_str.replace('₹', '').replace(',', '').replace('$', '').strip()
                                try:
                                    cost = float(clean_cost)
                                except:
                                    cost = 0

                            # Predecessors
                            predecessors_str = get_cell("predecessors", "")
                            predecessors = []
                            if predecessors_str:
                                # Simple split by comma or semi-colon
                                parts = predecessors_str.replace(';', ',').split(',')
                                for p in parts:
                                    p_clean = p.strip()
                                    if p_clean:
                                        # Handle lead/lag like "5FS+2 days" - just take the ID
                                        import re
                                        match = re.match(r'^(\d+)', p_clean)
                                        if match:
                                            predecessors.append(f"T{match.group(1)}")

                            # % Complete
                            pct_str = get_cell("percent_complete", "0")
                            pct_complete = 0
                            if pct_str:
                                try:
                                    pct_complete = int(pct_str.replace("%", ""))
                                except:
                                    if pct_str.isdigit():
                                        pct_complete = int(pct_str)

                            # Remaining Duration
                            rem_dur_str = get_cell("remaining_duration", "0")
                            try:
                                remaining_duration = float(rem_dur_str.split()[0])
                            except:
                                remaining_duration = 0

                            is_milestone = duration == 0 or baseline_duration == 0

                            # Fallbacks for start/finish
                            final_start = start or baseline_start or actual_start or ""
                            final_finish = finish or baseline_finish or actual_finish or ""

                            # Capture project start
                            if (task_id_num == 0 or not project_start) and final_start:
                                if not project_start or task_id_num == 0:
                                    project_start = final_start
                                if not project_name or task_id_num == 0:
                                    project_name = task_name

                            task_obj = {
                                "id": f"T{task_id_num}",
                                "name": task_name,
                                "duration": duration,
                                "start": final_start,
                                "finish": final_finish,
                                "predecessors": predecessors,
                                "cost": cost,
                                "percentComplete": pct_complete,
                                "actualStart": actual_start,
                                "actualFinish": actual_finish,
                                "baselineStart": baseline_start,
                                "baselineFinish": baseline_finish,
                                "remainingDuration": remaining_duration,
                                "isMilestone": is_milestone
                            }
                            tasks_data.append(task_obj)

                        except (ValueError, IndexError, TypeError):
                            continue

            if not tasks_data:
                return {
                    "error": "No task data extracted from PDF. Please ensure the PDF is a valid Microsoft Project Gantt chart export.",
                    "debug": debug_info
                }

            return {
                "tasks": tasks_data,
                "project_start": project_start,
                "project_name": project_name,
                "status": "success",
                "imported_at": datetime.now().isoformat(),
                "source": "PDF Gantt Chart"
            }

    except ImportError:
        return {
            "error": "pdfplumber is not installed. Please install it via: pip install pdfplumber"
        }
    except Exception as e:
        return {"error": f"Failed to parse PDF: {str(e)}"}


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

        result = parse_tracking_pdf(file_path)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
