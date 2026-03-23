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

        with pdfplumber.open(file_path) as pdf:
            tasks_data = []
            project_name = None
            project_start = None

            for page_num, page in enumerate(pdf.pages):
                # Extract tables from the page
                tables = page.extract_tables()

                if not tables:
                    continue

                for table_idx, table in enumerate(tables):
                    if len(table) < 2:
                        continue

                    # Find the header row (contains "ID", "Task Name", etc.)
                    header_row_idx = None
                    for i, row in enumerate(table):
                        if row and len(row) > 0:
                            # Check if this looks like a header row
                            first_cell = str(row[0]).lower() if row[0] else ""
                            if "id" in first_cell or "task" in str(row).lower():
                                header_row_idx = i
                                break

                    if header_row_idx is None:
                        continue

                    # Process data rows (skip header, title, and legend)
                    for row_idx in range(header_row_idx + 1, len(table)):
                        row = table[row_idx]
                        if not row or len(row) < 10:
                            continue

                        # Get ID column (first column)
                        task_id = str(row[0]).strip() if row[0] else ""

                        # Check if this is a valid data row (ID should be numeric or the project summary at 0)
                        if not task_id or (not task_id.isdigit() and task_id != "0"):
                            continue

                        # Skip legend and footer rows (they contain text like "Page" or "Legend")
                        if "page" in task_id.lower() or "legend" in task_id.lower():
                            continue

                        # Extract columns: ID | Task Name | BaselineDuration | BaselineStart | BaselineFinish
                        #                  | Duration | ActualStart | ActualFinish | %Comp | RemDur
                        try:
                            task_id_num = int(task_id)

                            # Task Name (column 1)
                            task_name = str(row[1]).strip() if len(row) > 1 and row[1] else "Task"

                            # Clean up task name from Gantt bleed (remove trailing Gantt bar text)
                            # Gantt bars add text like "i1n t" — remove anything after the last word
                            words = task_name.split()
                            if words:
                                # Remove trailing non-letter/digit/space content
                                task_name = " ".join(
                                    w for w in words if w and (w[0].isalpha() or w[0].isdigit())
                                ).strip()

                            # Skip ghost rows that have no useful content
                            if not task_name or task_name == "Task":
                                continue

                            # Baseline Duration (column 3, skip column 2 which is often None/"ghost")
                            baseline_duration_str = str(row[3]).strip() if len(row) > 3 and row[3] else "0"
                            baseline_duration = int(baseline_duration_str.split()[0]) if baseline_duration_str else 0

                            # Baseline Start (column 4)
                            baseline_start = str(row[4]).strip() if len(row) > 4 and row[4] else None

                            # Baseline Finish (column 5)
                            baseline_finish = str(row[5]).strip() if len(row) > 5 and row[5] else None

                            # Current Duration (column 6)
                            duration_str = str(row[6]).strip() if len(row) > 6 and row[6] else "0"
                            duration = int(duration_str.split()[0]) if duration_str else 0

                            # Actual Start (column 7)
                            actual_start = str(row[7]).strip() if len(row) > 7 and row[7] else None
                            if actual_start and actual_start.upper() == "NA":
                                actual_start = None

                            # Actual Finish (column 8)
                            actual_finish = str(row[8]).strip() if len(row) > 8 and row[8] else None
                            if actual_finish and actual_finish.upper() == "NA":
                                actual_finish = None

                            # % Complete (column 9)
                            pct_complete_str = str(row[9]).strip() if len(row) > 9 and row[9] else "0"
                            pct_complete = int(pct_complete_str.replace("%", "")) if pct_complete_str else 0

                            # Remaining Duration (column 10)
                            remaining_duration_str = str(row[10]).strip() if len(row) > 10 and row[10] else "0"
                            try:
                                remaining_duration = float(remaining_duration_str.split()[0])
                            except:
                                remaining_duration = 0

                            # Detect if this is the project summary (usually ID 0)
                            is_milestone = baseline_duration == 0

                            # Use baseline dates if available, otherwise use current dates
                            start = baseline_start if baseline_start else actual_start or ""
                            finish = baseline_finish if baseline_finish else actual_finish or ""

                            # Capture project start from the first row (project summary)
                            if task_id_num == 0 and not project_start:
                                if baseline_start:
                                    project_start = baseline_start
                                if not project_name:
                                    project_name = task_name

                            task_obj = {
                                "id": f"T{task_id_num}",
                                "name": task_name,
                                "duration": duration,
                                "start": start,
                                "finish": finish,
                                "predecessors": [],  # PDF doesn't have predecessor info
                                "cost": 0,  # PDF doesn't have cost info (only baseline PDFs have costs)
                                "percentComplete": pct_complete,
                                "actualStart": actual_start,
                                "actualFinish": actual_finish,
                                "baselineStart": baseline_start,
                                "baselineFinish": baseline_finish,
                                "remainingDuration": remaining_duration,
                                "isMilestone": is_milestone
                            }
                            tasks_data.append(task_obj)

                        except (ValueError, IndexError, TypeError) as e:
                            # Skip malformed rows
                            continue

            if not tasks_data:
                return {"error": "No task data extracted from PDF. Please ensure the PDF is a valid Microsoft Project Gantt chart export."}

            return {
                "tasks": tasks_data,
                "project_start": project_start,
                "project_name": project_name,
                "status": "success",
                "imported_at": datetime.now().isoformat(),
                "source": "PDF Gantt Chart",
                "warning": "PDF import extracts progress data. Predecessors and costs are not available in tracking PDFs. Use MSPDI XML import for the complete baseline schedule."
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
