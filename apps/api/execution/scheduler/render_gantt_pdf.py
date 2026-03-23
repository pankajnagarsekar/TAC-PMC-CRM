import json
import sys
import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# Layer 3: Execution Script
# Generates a professional Gantt chart PDF using ReportLab

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
    Generates a clean, professional Gantt chart PDF using ReportLab.
    Simplified 2-column layout: Data Grid (left) + Gantt Timeline (right)
    """
    try:
        # Page setup: A4 Landscape (simpler, more compatible)
        page_width, page_height = landscape(A4)  # ~297mm x ~210mm

        # Margins
        margin_left = 0.4 * inch
        margin_right = 0.4 * inch
        margin_top = 0.5 * inch
        margin_bottom = 0.6 * inch

        # Layout: Two clear sections
        data_col_width = 3.2 * inch  # Left panel: ID, Task Name, Start, Finish
        gantt_col_width = page_width - margin_left - margin_right - data_col_width - 0.2 * inch

        # Create PDF
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        c = canvas.Canvas(output_path, pagesize=landscape(A4))

        # Calculate timeline range
        all_dates = []
        for task in tasks:
            start = parse_date_str(task.get("start", ""))
            finish = parse_date_str(task.get("finish", ""))
            if start:
                all_dates.append(start)
            if finish:
                all_dates.append(finish)

        if not all_dates:
            c.drawString(margin_left, page_height - margin_top, "No schedule data to export")
            c.save()
            return {"status": "error", "message": "No valid task dates found"}

        min_date = min(all_dates)
        max_date = max(all_dates)
        total_days = (max_date - min_date).days + 1

        # --- PROJECT TITLE ---
        title_y = page_height - 0.35 * inch
        c.setFillColor(colors.HexColor("#1F3A5F"))  # Dark blue
        c.rect(margin_left, title_y - 0.3 * inch, page_width - margin_left - margin_right,
               0.3 * inch, fill=1, stroke=0)
        c.setFillColor(colors.whitesmoke)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(margin_left + 0.1 * inch, title_y - 0.2 * inch, project_name)

        # --- DATA GRID HEADER (Left Panel) ---
        header_y = page_height - 0.75 * inch

        # Header background
        c.setFillColor(colors.HexColor("#2E5090"))  # Professional blue
        c.rect(margin_left, header_y - 0.3 * inch, data_col_width, 0.3 * inch, fill=1, stroke=0)

        # Header text
        c.setFillColor(colors.whitesmoke)
        c.setFont("Helvetica-Bold", 8)

        # Column headers in left panel
        headers_left = ["ID", "Task Name", "Start", "Finish"]
        header_widths = [0.28 * inch, 1.7 * inch, 0.65 * inch, 0.65 * inch]

        h_x = margin_left
        for header, w in zip(headers_left, header_widths):
            c.drawCentredString(h_x + w / 2, header_y - 0.18 * inch, header)
            h_x += w

        # --- GANTT TIMELINE HEADER (Right Panel) ---
        gantt_x = margin_left + data_col_width + 0.2 * inch

        c.setFillColor(colors.HexColor("#2E5090"))
        c.rect(gantt_x, header_y - 0.3 * inch, gantt_col_width, 0.3 * inch, fill=1, stroke=0)

        # Timeline labels
        c.setFillColor(colors.whitesmoke)
        c.setFont("Helvetica", 7)

        current_date = min_date
        while current_date <= max_date:
            x_pos = gantt_x + ((current_date - min_date).days * gantt_col_width / total_days)
            label = current_date.strftime("%d %b")
            c.drawString(x_pos + 2, header_y - 0.18 * inch, label)
            current_date += timedelta(days=14)

        # --- TASK ROWS ---
        row_y = header_y - 0.4 * inch
        row_height = 0.24 * inch

        for idx, task in enumerate(tasks):
            # Alternate row colors
            if idx % 2 == 0:
                c.setFillColor(colors.HexColor("#ffffff"))
            else:
                c.setFillColor(colors.HexColor("#f5f7fa"))

            # Full row background
            c.rect(margin_left, row_y - row_height,
                   page_width - margin_left - margin_right, row_height, fill=1, stroke=0)

            # Row border
            c.setStrokeColor(colors.HexColor("#d0d5e0"))
            c.setLineWidth(0.5)
            c.line(margin_left, row_y - row_height,
                   margin_left + page_width - margin_left - margin_right, row_y - row_height)

            # --- LEFT PANEL: DATA GRID ---
            c.setFillColor(colors.HexColor("#1a1a1a"))
            c.setFont("Helvetica", 7.5)

            d_x = margin_left

            # ID
            task_id = str(task.get("id", ""))[:6]
            c.drawCentredString(d_x + header_widths[0] / 2, row_y - row_height / 2 - 0.03 * inch, task_id)
            d_x += header_widths[0]

            # Task Name
            task_name = str(task.get("name", ""))
            if len(task_name) > 35:
                task_name = task_name[:32] + "..."

            if task.get("isMilestone"):
                c.setFont("Helvetica-Bold", 7.5)
            c.drawString(d_x + 0.05 * inch, row_y - row_height / 2 - 0.03 * inch, task_name)
            c.setFont("Helvetica", 7.5)
            d_x += header_widths[1]

            # Start Date
            start_date = task.get("start", "-")
            c.drawCentredString(d_x + header_widths[2] / 2, row_y - row_height / 2 - 0.03 * inch, start_date)
            d_x += header_widths[2]

            # Finish Date
            finish_date = task.get("finish", "-")
            c.drawCentredString(d_x + header_widths[3] / 2, row_y - row_height / 2 - 0.03 * inch, finish_date)

            # --- RIGHT PANEL: GANTT BARS ---
            start_obj = parse_date_str(task.get("start", ""))
            finish_obj = parse_date_str(task.get("finish", ""))

            if start_obj and finish_obj:
                # Bar positioning
                bar_start_x = gantt_x + ((start_obj - min_date).days * gantt_col_width / total_days)
                bar_width = ((finish_obj - start_obj).days + 1) * gantt_col_width / total_days
                bar_width = max(bar_width, 2)

                # Determine bar color and style
                if task.get("isMilestone"):
                    bar_color = colors.HexColor("#F4A620")  # Gold
                elif task.get("is_critical"):
                    bar_color = colors.HexColor("#D63031")  # Red
                else:
                    bar_color = colors.HexColor("#4472C4")  # Blue

                bar_height = 0.1 * inch
                bar_y_pos = row_y - row_height / 2

                # Draw progress if exists
                pct = task.get("percentComplete", 0)
                if pct > 0:
                    progress_color = colors.HexColor("#52A552")
                    progress_width = bar_width * (pct / 100.0)
                    c.setFillColor(progress_color)
                    c.roundRect(bar_start_x, bar_y_pos - bar_height / 2, progress_width, bar_height,
                               radius=2, fill=1, stroke=0)

                # Draw main bar
                c.setFillColor(bar_color)
                c.roundRect(bar_start_x, bar_y_pos - bar_height / 2, bar_width, bar_height,
                           radius=2, fill=1, stroke=0)

                # Bar border
                c.setStrokeColor(colors.HexColor("#333333"))
                c.setLineWidth(0.5)
                c.roundRect(bar_start_x, bar_y_pos - bar_height / 2, bar_width, bar_height,
                           radius=2, fill=0, stroke=1)

            row_y -= row_height

        # --- FOOTER ---
        footer_y = 0.3 * inch
        c.setFont("Helvetica", 6)
        c.setFillColor(colors.HexColor("#666666"))

        # Legend
        c.drawString(margin_left, footer_y, "Legend:")

        legend_items = [
            ("Critical", colors.HexColor("#D63031")),
            ("Regular", colors.HexColor("#4472C4")),
            ("Milestone", colors.HexColor("#F4A620")),
            ("Progress", colors.HexColor("#52A552")),
        ]

        leg_x = margin_left + 0.6 * inch
        for label, color in legend_items:
            c.setFillColor(color)
            c.rect(leg_x, footer_y - 0.08 * inch, 0.08 * inch, 0.08 * inch, fill=1, stroke=0)
            leg_x += 0.12 * inch

            c.setFillColor(colors.HexColor("#666666"))
            c.drawString(leg_x, footer_y, label)
            leg_x += 0.9 * inch

        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        c.drawString(page_width - margin_right - 2.5 * inch, footer_y, f"Generated: {timestamp}")

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
