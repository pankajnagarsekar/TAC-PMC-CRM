import json
import sys
import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# Layer 3: Execution Script
# Professional MS Project-style Gantt chart PDF

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
    Generates professional MS Project-style Gantt chart PDF with proper bars and colors.
    """
    try:
        # Page setup
        page_width, page_height = landscape(A4)

        # Margins
        margin_left = 0.3 * inch
        margin_right = 0.3 * inch
        margin_top = 0.35 * inch
        margin_bottom = 0.5 * inch

        # Layout dimensions
        data_col_width = 3.8 * inch
        gantt_col_width = page_width - margin_left - margin_right - data_col_width - 0.15 * inch

        # Create PDF
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        c = canvas.Canvas(output_path, pagesize=landscape(A4))

        # Calculate timeline
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
        title_y = page_height - 0.28 * inch
        c.setFillColor(colors.HexColor("#1F3A5F"))
        c.rect(margin_left, title_y - 0.22 * inch, page_width - margin_left - margin_right,
               0.22 * inch, fill=1, stroke=0)
        c.setFillColor(colors.whitesmoke)
        c.setFont("Helvetica-Bold", 11)
        # Use proper project name (not ID)
        display_name = project_name if project_name and len(project_name) > 20 else f"Project: {project_name}"
        c.drawString(margin_left + 0.1 * inch, title_y - 0.14 * inch, display_name)

        # --- DATA GRID HEADER ---
        header_y = page_height - 0.55 * inch

        # Header background
        c.setFillColor(colors.HexColor("#2E5090"))
        c.rect(margin_left, header_y - 0.2 * inch, data_col_width, 0.2 * inch, fill=1, stroke=0)

        # Data column headers
        c.setFillColor(colors.whitesmoke)
        c.setFont("Helvetica-Bold", 6.5)

        col_positions = []
        col_x = margin_left
        headers = [
            ("ID", 0.25 * inch),
            ("Task Mode", 0.35 * inch),
            ("Task Name", 1.45 * inch),
            ("Duration", 0.65 * inch),
            ("Start", 0.5 * inch),
            ("Finish", 0.5 * inch),
        ]

        for header, width in headers:
            col_positions.append((header, width, col_x))
            c.drawCentredString(col_x + width / 2, header_y - 0.11 * inch, header)
            col_x += width

        # --- GANTT TIMELINE HEADER ---
        gantt_x = margin_left + data_col_width + 0.15 * inch

        # Build quarter sections
        quarters = []
        current_date = min_date
        while current_date <= max_date:
            q_num = (current_date.month - 1) // 3 + 1
            q_year = current_date.year

            # Define quarter boundaries
            if q_num == 1:
                q_start = datetime(q_year, 1, 1).date()
                q_end = datetime(q_year, 3, 31).date()
            elif q_num == 2:
                q_start = datetime(q_year, 4, 1).date()
                q_end = datetime(q_year, 6, 30).date()
            elif q_num == 3:
                q_start = datetime(q_year, 7, 1).date()
                q_end = datetime(q_year, 9, 30).date()
            else:
                q_start = datetime(q_year, 10, 1).date()
                q_end = datetime(q_year, 12, 31).date()

            # Clamp to timeline
            q_start = max(q_start, min_date)
            q_end = min(q_end, max_date)

            if q_start <= max_date and q_end >= min_date:
                label = f"Qtr {q_num}, {q_year}"
                if not quarters or quarters[-1][0] != label:
                    quarters.append((label, q_start, q_end))

            # Move to next quarter
            if q_num == 4:
                current_date = datetime(q_year + 1, 1, 1).date()
            else:
                current_date = datetime(q_year, (q_num * 3) + 1, 1).date()

        # Draw quarterly header
        c.setFillColor(colors.HexColor("#2E5090"))
        c.rect(gantt_x, header_y - 0.1 * inch, gantt_col_width, 0.1 * inch, fill=1, stroke=0)

        c.setFillColor(colors.whitesmoke)
        c.setFont("Helvetica-Bold", 7)

        for q_label, q_start, q_end in quarters:
            q_start_px = gantt_x + ((q_start - min_date).days * gantt_col_width / total_days)
            q_end_px = gantt_x + ((q_end - min_date).days * gantt_col_width / total_days)
            q_width = q_end_px - q_start_px

            if q_width > 0.3 * inch:
                c.drawCentredString(q_start_px + q_width / 2, header_y - 0.055 * inch, q_label)

            # Quarter divider
            c.setStrokeColor(colors.whitesmoke)
            c.setLineWidth(0.5)
            c.line(q_end_px, header_y, q_end_px, header_y - 0.2 * inch)

        # Draw month subheader
        c.setFillColor(colors.HexColor("#3A6BA0"))
        c.rect(gantt_x, header_y - 0.2 * inch, gantt_col_width, 0.1 * inch, fill=1, stroke=0)

        c.setFillColor(colors.whitesmoke)
        c.setFont("Helvetica", 6)

        current_date = min_date
        last_month = None
        while current_date <= max_date:
            if current_date.month != last_month:
                month_label = current_date.strftime("%b")
                month_x = gantt_x + ((current_date - min_date).days * gantt_col_width / total_days)
                c.drawString(month_x + 2, header_y - 0.16 * inch, month_label)
                last_month = current_date.month

            current_date += timedelta(days=1)

        # --- TASK ROWS ---
        row_y = header_y - 0.3 * inch
        row_height = 0.16 * inch

        for idx, task in enumerate(tasks):
            # Alternate row colors
            if idx % 2 == 0:
                c.setFillColor(colors.HexColor("#ffffff"))
            else:
                c.setFillColor(colors.HexColor("#f8f8f8"))

            # Full row background
            c.rect(margin_left, row_y - row_height,
                   page_width - margin_left - margin_right, row_height, fill=1, stroke=0)

            # Row border
            c.setStrokeColor(colors.HexColor("#d0d5e0"))
            c.setLineWidth(0.5)
            c.line(margin_left, row_y - row_height,
                   margin_left + page_width - margin_left - margin_right, row_y - row_height)

            # --- LEFT PANEL: DATA ---
            c.setFillColor(colors.HexColor("#1a1a1a"))
            c.setFont("Helvetica", 6)

            col_x = margin_left

            # ID
            task_id = str(task.get("id", ""))[:4]
            c.drawCentredString(col_x + 0.125 * inch, row_y - row_height / 2 - 0.02 * inch, task_id)
            col_x += 0.25 * inch

            # Task Mode icon
            c.drawString(col_x + 0.1 * inch, row_y - row_height / 2 - 0.02 * inch, "■")
            col_x += 0.35 * inch

            # Task Name
            task_name = str(task.get("name", ""))
            if len(task_name) > 45:
                task_name = task_name[:42] + "..."

            if task.get("isMilestone"):
                c.setFont("Helvetica-Bold", 6)
            c.drawString(col_x + 0.05 * inch, row_y - row_height / 2 - 0.02 * inch, task_name)
            c.setFont("Helvetica", 6)
            col_x += 1.45 * inch

            # Duration
            dur = task.get("duration", 0)
            dur_text = f"{dur}d" if dur else "-"
            c.drawCentredString(col_x + 0.325 * inch, row_y - row_height / 2 - 0.02 * inch, dur_text)
            col_x += 0.65 * inch

            # Start
            start_date = task.get("start", "-")
            c.drawCentredString(col_x + 0.25 * inch, row_y - row_height / 2 - 0.02 * inch, start_date)
            col_x += 0.5 * inch

            # Finish
            finish_date = task.get("finish", "-")
            c.drawCentredString(col_x + 0.25 * inch, row_y - row_height / 2 - 0.02 * inch, finish_date)

            # --- RIGHT PANEL: GANTT BARS ---
            start_obj = parse_date_str(task.get("start", ""))
            finish_obj = parse_date_str(task.get("finish", ""))

            if start_obj and finish_obj and start_obj <= max_date and finish_obj >= min_date:
                # Clamp to timeline
                bar_start = max(start_obj, min_date)
                bar_end = min(finish_obj, max_date)

                # Calculate position and width
                bar_x = gantt_x + ((bar_start - min_date).days * gantt_col_width / total_days)
                bar_width = ((bar_end - bar_start).days + 1) * gantt_col_width / total_days
                bar_width = max(bar_width, 4)  # Minimum width

                bar_height = 0.08 * inch
                bar_y_center = row_y - row_height / 2

                # Determine bar properties
                is_milestone = task.get("isMilestone", False)
                is_critical = task.get("is_critical", False)

                if is_milestone:
                    # Milestone: small diamond at finish date
                    marker_x = gantt_x + ((finish_obj - min_date).days * gantt_col_width / total_days)
                    marker_size = 0.08 * inch
                    c.setFillColor(colors.HexColor("#F4A620"))  # Gold
                    c.rect(marker_x - marker_size / 2, bar_y_center - marker_size / 2,
                          marker_size, marker_size, fill=1, stroke=0)
                else:
                    # Regular task bar
                    bar_color = colors.HexColor("#D63031") if is_critical else colors.HexColor("#4472C4")

                    # Progress fill
                    pct = task.get("percentComplete", 0)
                    if pct > 0:
                        progress_color = colors.HexColor("#70AD47")
                        progress_width = bar_width * (pct / 100.0)
                        c.setFillColor(progress_color)
                        c.roundRect(bar_x, bar_y_center - bar_height / 2, progress_width, bar_height,
                                   radius=2, fill=1, stroke=0)

                    # Main bar
                    c.setFillColor(bar_color)
                    c.roundRect(bar_x, bar_y_center - bar_height / 2, bar_width, bar_height,
                               radius=2, fill=1, stroke=0)

                    # Bar border
                    c.setStrokeColor(colors.HexColor("#333333"))
                    c.setLineWidth(0.5)
                    c.roundRect(bar_x, bar_y_center - bar_height / 2, bar_width, bar_height,
                               radius=2, fill=0, stroke=1)

            row_y -= row_height

        # --- FOOTER ---
        footer_y = 0.25 * inch
        c.setFont("Helvetica", 6)
        c.setFillColor(colors.HexColor("#666666"))

        c.drawString(margin_left, footer_y, f"Date: {datetime.now().strftime('%d-%m-%y')}")

        # Legend
        legend_x = page_width / 2 - 1.5 * inch
        legend_items = [
            ("Task", colors.HexColor("#4472C4")),
            ("Critical", colors.HexColor("#D63031")),
            ("Milestone", colors.HexColor("#F4A620")),
            ("Progress", colors.HexColor("#70AD47")),
        ]

        for label, color in legend_items:
            c.setFillColor(color)
            c.rect(legend_x, footer_y - 0.07 * inch, 0.06 * inch, 0.06 * inch, fill=1)
            legend_x += 0.08 * inch

            c.setFillColor(colors.HexColor("#666666"))
            c.setFont("Helvetica", 5)
            c.drawString(legend_x, footer_y, label)
            legend_x += 0.8 * inch

        c.drawString(page_width - margin_right - 1.2 * inch, footer_y, "Page 1")

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
