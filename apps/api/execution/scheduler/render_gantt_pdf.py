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
    Generates a professional, multi-page Gantt chart PDF using ReportLab.
    Improved layout with better readability and spacing.
    """
    try:
        # Page setup: Landscape A3
        page_width, page_height = landscape(A3)  # ~420mm x ~297mm

        # Margins and layout (increased margins for better spacing)
        margin_left = 0.5 * inch
        margin_right = 0.5 * inch
        margin_top = 0.6 * inch
        margin_bottom = 0.8 * inch

        # Improved layout: larger left panel for data, better proportions
        left_panel_width = 4.5 * inch  # Increased from 3.5 to accommodate task names
        right_panel_width = page_width - margin_left - margin_right - left_panel_width - 0.3 * inch

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
        header_row_y = page_height - 0.9 * inch

        # Define columns (reduced to essentials for clarity)
        columns = [
            {"name": "ID", "width": 0.35 * inch},
            {"name": "Task Name", "width": left_panel_width - 0.35 * inch - 0.65 * inch},
            {"name": "Start", "width": 0.65 * inch},
            {"name": "Finish", "width": 0.65 * inch},
            {"name": "Days", "width": 0.5 * inch},
            {"name": "%", "width": 0.4 * inch},
        ]

        # Draw left panel header background (darker for better contrast)
        c.setFillColor(colors.HexColor("#2C5AA0"))  # Professional blue
        c.rect(margin_left, header_row_y - 0.35 * inch, left_panel_width, 0.35 * inch, fill=1, stroke=0)

        # Draw column headers with better styling
        col_x = margin_left
        c.setFillColor(colors.whitesmoke)
        c.setFont("Helvetica-Bold", 9)
        for col in columns:
            c.drawCentredString(col_x + col["width"] / 2, header_row_y - 0.2 * inch, col["name"])
            # Draw column divider lines
            c.setStrokeColor(colors.HexColor("#ffffff"))
            c.setLineWidth(1)
            c.line(col_x + col["width"], header_row_y, col_x + col["width"], header_row_y - 0.35 * inch)
            col_x += col["width"]

        # Draw right panel header (timeline) - matching colors
        c.setFillColor(colors.HexColor("#2C5AA0"))
        c.rect(margin_left + left_panel_width + 0.3 * inch, header_row_y - 0.35 * inch,
               right_panel_width, 0.35 * inch, fill=1, stroke=0)

        # Draw week headers in right panel with proper spacing
        right_panel_x = margin_left + left_panel_width + 0.3 * inch
        current_date = min_date
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.whitesmoke)

        # Draw timeline labels at 14-day intervals for clarity
        while current_date <= max_date:
            x_pos = right_panel_x + ((current_date - min_date).days * right_panel_width / total_days)
            week_label = current_date.strftime("%d %b")
            # Only draw if there's space
            if x_pos + 0.3 * inch <= right_panel_x + right_panel_width:
                c.drawString(x_pos + 5, header_row_y - 0.2 * inch, week_label)
            current_date += timedelta(days=14)

        # --- TASK ROWS (with improved spacing) ---
        row_height = 0.28 * inch  # Increased from 0.2 for better readability
        row_y = header_row_y - 0.5 * inch
        c.setFont("Helvetica", 8)

        for idx, task in enumerate(tasks):
            # Alternate row background for better readability
            if idx % 2 == 0:
                c.setFillColor(colors.HexColor("#ffffff"))
            else:
                c.setFillColor(colors.HexColor("#f5f7fa"))  # Light blue-gray

            # Draw full row background
            c.rect(margin_left, row_y - row_height, left_panel_width + 0.3 * inch + right_panel_width,
                   row_height, fill=1, stroke=0)

            # Draw row borders for separation
            c.setStrokeColor(colors.HexColor("#e0e0e0"))
            c.setLineWidth(0.5)
            c.line(margin_left, row_y - row_height, margin_left + left_panel_width + 0.3 * inch + right_panel_width, row_y - row_height)

            # Draw left panel data with improved spacing
            col_x = margin_left
            c.setFillColor(colors.HexColor("#1a1a1a"))  # Darker text for contrast
            c.setFont("Helvetica", 8)

            # Column 1: ID
            task_id = str(task.get("id", ""))[:8]
            c.drawCentredString(col_x + columns[0]["width"] / 2, row_y - row_height / 2 - 0.05 * inch, task_id)
            col_x += columns[0]["width"]

            # Column 2: Task Name (truncate with ellipsis if needed)
            task_name = str(task.get("name", ""))
            if task.get("isMilestone"):
                c.setFont("Helvetica-Bold", 8)
            else:
                c.setFont("Helvetica", 8)

            # Truncate task name to fit width
            max_name_chars = 45
            if len(task_name) > max_name_chars:
                task_name = task_name[:max_name_chars-2] + "..."

            c.drawString(col_x + 0.08 * inch, row_y - row_height / 2 - 0.05 * inch, task_name)
            c.setFont("Helvetica", 8)
            col_x += columns[1]["width"]

            # Column 3: Start Date
            start_date = task.get("start", "")
            c.drawCentredString(col_x + columns[2]["width"] / 2, row_y - row_height / 2 - 0.05 * inch,
                               start_date or "-")
            col_x += columns[2]["width"]

            # Column 4: Finish Date
            finish_date = task.get("finish", "")
            c.drawCentredString(col_x + columns[3]["width"] / 2, row_y - row_height / 2 - 0.05 * inch,
                               finish_date or "-")
            col_x += columns[3]["width"]

            # Column 5: Duration in Days
            dur = task.get("duration", 0)
            c.drawCentredString(col_x + columns[4]["width"] / 2, row_y - row_height / 2 - 0.05 * inch,
                               f"{dur}d" if dur else "-")
            col_x += columns[4]["width"]

            # Column 6: % Complete
            pct = task.get("percentComplete", 0)
            c.drawCentredString(col_x + columns[5]["width"] / 2, row_y - row_height / 2 - 0.05 * inch,
                               f"{pct}%")

            # Draw Gantt bar in right panel
            start_date = parse_date_str(task.get("start", ""))
            finish_date = parse_date_str(task.get("finish", ""))

            if start_date and finish_date:
                bar_x = right_panel_x + ((start_date - min_date).days * right_panel_width / total_days)
                bar_width = ((finish_date - start_date).days + 1) * right_panel_width / total_days
                bar_width = max(bar_width, 3)  # Minimum bar width for visibility

                # Determine bar color
                if task.get("isMilestone"):
                    bar_color = colors.HexColor("#FFB81C")  # Gold for milestones
                elif task.get("is_critical"):
                    bar_color = colors.HexColor("#E31937")  # Crimson for critical
                else:
                    bar_color = colors.HexColor("#4472C4")  # Professional blue

                bar_height = 0.12 * inch  # Larger bars for better visibility

                # Draw progress fill first (underneath)
                pct = task.get("percentComplete", 0)
                if pct > 0:
                    progress_color = colors.HexColor("#70AD47")  # Green for progress
                    progress_width = bar_width * (pct / 100.0)
                    c.setFillColor(progress_color)
                    c.roundRect(bar_x, row_y - row_height / 2 - bar_height / 2, progress_width, bar_height,
                               radius=2, fill=1, stroke=0)

                # Draw main task bar with subtle shadow
                c.setFillColor(bar_color)
                c.roundRect(bar_x, row_y - row_height / 2 - bar_height / 2, bar_width, bar_height,
                           radius=2, fill=1, stroke=0)

                # Add border to bar
                c.setStrokeColor(colors.HexColor("#333333"))
                c.setLineWidth(0.5)
                c.roundRect(bar_x, row_y - row_height / 2 - bar_height / 2, bar_width, bar_height,
                           radius=2, fill=0, stroke=1)

            row_y -= row_height

        # --- PAGE FOOTER ---
        footer_y = 0.35 * inch
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#666666"))

        # Legend
        legend_x = margin_left
        c.drawString(legend_x, footer_y, "Legend:")
        legend_x += 0.5 * inch

        # Critical task box
        c.setFillColor(colors.HexColor("#E31937"))
        c.rect(legend_x, footer_y - 0.03 * inch, 0.08 * inch, 0.08 * inch, fill=1, stroke=0)
        legend_x += 0.12 * inch
        c.setFillColor(colors.HexColor("#666666"))
        c.drawString(legend_x, footer_y, "Critical")
        legend_x += 0.8 * inch

        # Regular task box
        c.setFillColor(colors.HexColor("#4472C4"))
        c.rect(legend_x, footer_y - 0.03 * inch, 0.08 * inch, 0.08 * inch, fill=1, stroke=0)
        legend_x += 0.12 * inch
        c.setFillColor(colors.HexColor("#666666"))
        c.drawString(legend_x, footer_y, "Regular")
        legend_x += 0.8 * inch

        # Milestone box
        c.setFillColor(colors.HexColor("#FFB81C"))
        c.rect(legend_x, footer_y - 0.03 * inch, 0.08 * inch, 0.08 * inch, fill=1, stroke=0)
        legend_x += 0.12 * inch
        c.setFillColor(colors.HexColor("#666666"))
        c.drawString(legend_x, footer_y, "Milestone")
        legend_x += 0.9 * inch

        # Progress box
        c.setFillColor(colors.HexColor("#70AD47"))
        c.rect(legend_x, footer_y - 0.03 * inch, 0.08 * inch, 0.08 * inch, fill=1, stroke=0)
        legend_x += 0.12 * inch
        c.setFillColor(colors.HexColor("#666666"))
        c.drawString(legend_x, footer_y, "Progress")

        # Page info on right
        c.drawString(page_width - margin_right - 2.2 * inch, footer_y, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

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
