import json
import sys
import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import landscape, A3
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# Layer 3: Execution Script
# Generates a high-fidelity Gantt chart PDF using ReportLab

def parse_date_str(date_str):
    """Parse DD-MM-YY format to date object"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%d-%m-%y").date()
    except:
        return None


def generate_gantt_pdf(tasks, project_name="Project Schedule", output_path=".tmp/gantt_export.pdf"):
    """
    Generates a Microsoft Project-style Gantt chart PDF using ReportLab.
    """
    try:
        # Page setup: Landscape A3
        page_width, page_height = landscape(A3)  # ~420mm x ~297mm

        # Margins and layout
        margin_left = 0.5 * inch
        margin_right = 0.5 * inch
        margin_top = 0.5 * inch
        margin_bottom = 1.0 * inch

        # Fixed left panel width for data grid
        left_panel_width = 3.5 * inch
        right_panel_width = page_width - margin_left - margin_right - left_panel_width - 0.25 * inch

        # Create PDF
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        c = canvas.Canvas(output_path, pagesize=landscape(A3))

        # Calculate timeline range from tasks
        all_dates = []
        for task in tasks:
            start = parse_date_str(task.get("start", ""))
            finish = parse_date_str(task.get("finish", ""))
            if start:
                all_dates.append(start)
            if finish:
                all_dates.append(finish)

        if not all_dates:
            # No valid dates - create minimal PDF
            c.drawString(margin_left, page_height - margin_top, "No schedule data to export")
            c.save()
            return {"status": "error", "message": "No valid task dates found"}

        min_date = min(all_dates)
        max_date = max(all_dates)
        total_days = (max_date - min_date).days + 1

        # --- PAGE HEADER ---
        header_y = page_height - 0.4 * inch
        c.setFillColor(colors.HexColor("#1F3864"))  # Dark navy
        c.rect(margin_left, header_y - 0.35 * inch, page_width - margin_left - margin_right, 0.35 * inch, fill=1, stroke=0)
        c.setFillColor(colors.whitesmoke)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin_left + 0.1 * inch, header_y - 0.25 * inch, project_name)

        # --- COLUMN HEADERS ---
        header_row_y = page_height - 0.8 * inch

        # Define columns
        columns = [
            {"name": "ID", "width": 0.3 * inch},
            {"name": "Task Name", "width": left_panel_width - 0.3 * inch - 0.1 * inch},
            {"name": "Base Dur.", "width": 0.8 * inch},
            {"name": "Base Start", "width": 0.75 * inch},
            {"name": "Base Finish", "width": 0.75 * inch},
            {"name": "Duration", "width": 0.7 * inch},
            {"name": "Act. Start", "width": 0.75 * inch},
            {"name": "Act. Finish", "width": 0.75 * inch},
            {"name": "% Comp.", "width": 0.5 * inch},
            {"name": "Rem. Dur.", "width": 0.7 * inch},
        ]

        # Draw left panel header background
        c.setFillColor(colors.HexColor("#f0f0f0"))
        c.rect(margin_left, header_row_y - 0.25 * inch, left_panel_width, 0.25 * inch, fill=1, stroke=0)

        # Draw column headers
        col_x = margin_left
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 7)
        for col in columns:
            c.drawCentredString(col_x + col["width"] / 2, header_row_y - 0.15 * inch, col["name"])
            c.setStrokeColor(colors.HexColor("#cccccc"))
            c.line(col_x, header_row_y, col_x, header_row_y - 0.25 * inch)
            col_x += col["width"]

        # Draw right panel header (timeline)
        c.setFillColor(colors.HexColor("#f0f0f0"))
        c.rect(margin_left + left_panel_width + 0.25 * inch, header_row_y - 0.25 * inch,
               right_panel_width, 0.25 * inch, fill=1, stroke=0)

        # Draw week headers in right panel
        right_panel_x = margin_left + left_panel_width + 0.25 * inch
        week_width = right_panel_width / max(1, (total_days // 7 + 1))
        current_date = min_date
        c.setFont("Helvetica", 6)
        c.setFillColor(colors.black)
        while current_date <= max_date:
            week_label = current_date.strftime("%d %b '%y")
            x_pos = right_panel_x + ((current_date - min_date).days * right_panel_width / total_days)
            c.drawString(x_pos + 2, header_row_y - 0.15 * inch, week_label)
            current_date += timedelta(days=7)

        # --- TASK ROWS ---
        row_height = 0.2 * inch
        row_y = header_row_y - 0.35 * inch
        c.setFont("Helvetica", 7)

        for idx, task in enumerate(tasks):
            # Alternate row background
            if idx % 2 == 0:
                c.setFillColor(colors.HexColor("#ffffff"))
            else:
                c.setFillColor(colors.HexColor("#f8f8f8"))

            c.rect(margin_left, row_y - row_height, left_panel_width + 0.25 * inch + right_panel_width,
                   row_height, fill=1, stroke=0)

            # Draw left panel data
            col_x = margin_left
            c.setFillColor(colors.black)

            # ID
            c.drawCentredString(col_x + columns[0]["width"] / 2, row_y - row_height / 2 - 0.05 * inch, str(task.get("id", "")))
            col_x += columns[0]["width"]

            # Task Name (bold for summary rows)
            task_name = str(task.get("name", ""))
            if task.get("isMilestone"):
                c.setFont("Helvetica-Bold", 7)
            c.drawString(col_x + 0.05 * inch, row_y - row_height / 2 - 0.05 * inch, task_name[:40])
            c.setFont("Helvetica", 7)
            col_x += columns[1]["width"]

            # Baseline Duration
            base_dur = task.get("duration", 0)
            c.drawCentredString(col_x + columns[2]["width"] / 2, row_y - row_height / 2 - 0.05 * inch,
                               f"{base_dur}d")
            col_x += columns[2]["width"]

            # Baseline Start
            base_start = task.get("start", "")
            c.drawCentredString(col_x + columns[3]["width"] / 2, row_y - row_height / 2 - 0.05 * inch,
                               base_start)
            col_x += columns[3]["width"]

            # Baseline Finish
            base_finish = task.get("finish", "")
            c.drawCentredString(col_x + columns[4]["width"] / 2, row_y - row_height / 2 - 0.05 * inch,
                               base_finish)
            col_x += columns[4]["width"]

            # Duration
            dur = task.get("duration", 0)
            c.drawCentredString(col_x + columns[5]["width"] / 2, row_y - row_height / 2 - 0.05 * inch,
                               f"{dur}d")
            col_x += columns[5]["width"]

            # Actual Start
            act_start = task.get("actualStart", "NA")
            c.drawCentredString(col_x + columns[6]["width"] / 2, row_y - row_height / 2 - 0.05 * inch,
                               act_start or "NA")
            col_x += columns[6]["width"]

            # Actual Finish
            act_finish = task.get("actualFinish", "NA")
            c.drawCentredString(col_x + columns[7]["width"] / 2, row_y - row_height / 2 - 0.05 * inch,
                               act_finish or "NA")
            col_x += columns[7]["width"]

            # % Complete
            pct = task.get("percentComplete", 0)
            c.drawCentredString(col_x + columns[8]["width"] / 2, row_y - row_height / 2 - 0.05 * inch,
                               f"{pct}%")
            col_x += columns[8]["width"]

            # Remaining Duration
            rem_dur = task.get("remainingDuration", 0)
            c.drawCentredString(col_x + columns[9]["width"] / 2, row_y - row_height / 2 - 0.05 * inch,
                               f"{rem_dur}")

            # Draw Gantt bar
            start_date = parse_date_str(task.get("start", ""))
            finish_date = parse_date_str(task.get("finish", ""))

            if start_date and finish_date:
                bar_x = right_panel_x + ((start_date - min_date).days * right_panel_width / total_days)
                bar_width = ((finish_date - start_date).days + 1) * right_panel_width / total_days
                bar_width = max(bar_width, 2)  # Minimum bar width

                # Choose bar color based on critical flag
                if task.get("is_critical"):
                    bar_color = colors.HexColor("#CC0000")  # Red for critical
                    progress_color = colors.HexColor("#990000")
                else:
                    bar_color = colors.HexColor("#4472C4")  # Blue for regular
                    progress_color = colors.HexColor("#2E5BA3")

                bar_height = 0.08 * inch

                # Draw baseline bar (light gray) if applicable
                if task.get("baselineStart") and task.get("baselineFinish"):
                    baseline_start = parse_date_str(task.get("baselineStart"))
                    baseline_finish = parse_date_str(task.get("baselineFinish"))
                    if baseline_start and baseline_finish:
                        baseline_x = right_panel_x + ((baseline_start - min_date).days * right_panel_width / total_days)
                        baseline_width = ((baseline_finish - baseline_start).days + 1) * right_panel_width / total_days
                        c.setFillColor(colors.HexColor("#888888"))
                        c.rect(baseline_x, row_y - row_height / 2 - 0.02 * inch, baseline_width, 0.02 * inch,
                              fill=1, stroke=0)

                # Draw progress fill
                pct = task.get("percentComplete", 0)
                if pct > 0:
                    progress_width = bar_width * (pct / 100.0)
                    c.setFillColor(progress_color)
                    c.roundRect(bar_x, row_y - row_height / 2 - bar_height / 2, progress_width, bar_height,
                               radius=1, fill=1, stroke=0)

                # Draw main task bar
                c.setFillColor(bar_color)
                c.roundRect(bar_x, row_y - row_height / 2 - bar_height / 2, bar_width, bar_height,
                           radius=2, fill=1, stroke=0)

                # Draw % label on bar
                if bar_width > 0.3 * inch:
                    c.setFont("Helvetica", 5)
                    c.setFillColor(colors.whitesmoke)
                    c.drawCentredString(bar_x + bar_width / 2, row_y - row_height / 2 - 0.01 * inch,
                                      f"{pct}%")

            row_y -= row_height

        # --- PAGE FOOTER (Legend) ---
        footer_y = 0.4 * inch
        c.setFont("Helvetica", 6)
        c.drawString(margin_left, footer_y, "Legend: ■ Critical Task  ■ Regular Task  ◆ Milestone  ▬ Baseline  | Progress Fill")
        c.drawString(page_width - margin_right - 1 * inch, footer_y, f"Page 1 | Generated {datetime.now().strftime('%Y-%m-%d')}")

        c.save()

        return {
            "status": "success",
            "pdf_path": output_path,
            "tasks_exported": len(tasks),
            "date_range": f"{min_date.strftime('%d-%m-%y')} to {max_date.strftime('%d-%m-%y')}"
        }

    except Exception as e:
        return {"error": f"Failed to generate PDF: {str(e)}"}


if __name__ == "__main__":
    try:
        input_data = json.load(sys.stdin)
        project_id = input_data.get("project_id", "project")
        tasks = input_data.get("tasks", [])
        project_name = input_data.get("project_name", f"Project {project_id}")
        output_path = input_data.get("output_path", f".tmp/gantt_export_{project_id}.pdf")

        result = generate_gantt_pdf(tasks, project_name, output_path)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
