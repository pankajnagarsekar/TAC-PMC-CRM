import json
import sys
import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# Layer 3: Execution Script
# Generates professional MS Project-style Gantt chart PDF using ReportLab

def parse_date_str(date_str):
    """Parse DD-MM-YY format to date object"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%d-%m-%y").date()
    except:
        return None


def get_quarter_label(date_obj):
    """Get quarter label like 'Qtr 1, 2026'"""
    quarter = (date_obj.month - 1) // 3 + 1
    return f"Qtr {quarter}, {date_obj.year}"


def generate_gantt_pdf(tasks, project_name="Project Schedule", output_path=".tmp/gantt_export.pdf"):
    """
    Generates a professional MS Project-style Gantt chart PDF.
    Features quarterly grouping and comprehensive data columns.
    """
    try:
        # Page setup: Landscape A4
        page_width, page_height = landscape(A4)

        # Margins
        margin_left = 0.3 * inch
        margin_right = 0.3 * inch
        margin_top = 0.4 * inch
        margin_bottom = 0.5 * inch

        # Two-panel layout
        data_col_width = 3.8 * inch  # Left: ID, Task Mode, Name, Duration, Start, Finish, Pred, Cost
        gantt_col_width = page_width - margin_left - margin_right - data_col_width - 0.15 * inch

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
        title_y = page_height - 0.3 * inch
        c.setFillColor(colors.HexColor("#1F3A5F"))
        c.rect(margin_left, title_y - 0.25 * inch, page_width - margin_left - margin_right,
               0.25 * inch, fill=1, stroke=0)
        c.setFillColor(colors.whitesmoke)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin_left + 0.1 * inch, title_y - 0.16 * inch, f"Project: {project_name}")

        # --- DATA GRID HEADER ---
        header_y = page_height - 0.6 * inch

        # Header background
        c.setFillColor(colors.HexColor("#2E5090"))
        c.rect(margin_left, header_y - 0.28 * inch, data_col_width, 0.28 * inch, fill=1, stroke=0)

        # Column headers
        c.setFillColor(colors.whitesmoke)
        c.setFont("Helvetica-Bold", 6.5)

        headers = [
            ("ID", 0.25 * inch),
            ("Task Mode", 0.35 * inch),
            ("Task Name", 1.45 * inch),
            ("Duration", 0.65 * inch),
            ("Start", 0.5 * inch),
            ("Finish", 0.5 * inch),
        ]

        h_x = margin_left
        for header, width in headers:
            c.drawCentredString(h_x + width / 2, header_y - 0.15 * inch, header)
            h_x += width

        # --- QUARTERLY TIMELINE HEADER ---
        gantt_x = margin_left + data_col_width + 0.15 * inch

        c.setFillColor(colors.HexColor("#2E5090"))
        c.rect(gantt_x, header_y - 0.28 * inch, gantt_col_width, 0.28 * inch, fill=1, stroke=0)

        # Quarterly sections
        current_quarter_start = None
        quarter_sections = []

        current_date = min_date
        while current_date <= max_date:
            quarter_label = get_quarter_label(current_date)
            if not current_quarter_start or quarter_label != get_quarter_label(current_quarter_start):
                if current_quarter_start:
                    quarter_end = current_date - timedelta(days=1)
                    quarter_sections.append((
                        get_quarter_label(current_quarter_start),
                        current_quarter_start,
                        quarter_end
                    ))
                current_quarter_start = current_date
                # Move to next quarter
                quarter_num = (current_date.month - 1) // 3 + 1
                if quarter_num == 4:
                    current_date = datetime(current_date.year + 1, 1, 1).date()
                else:
                    current_date = datetime(current_date.year, (quarter_num) * 3 + 1, 1).date()
            else:
                current_date += timedelta(days=1)

        if current_quarter_start:
            quarter_sections.append((
                get_quarter_label(current_quarter_start),
                current_quarter_start,
                max_date
            ))

        # Draw quarter labels
        c.setFillColor(colors.whitesmoke)
        c.setFont("Helvetica-Bold", 7)

        for quarter_label, q_start, q_end in quarter_sections:
            q_start_x = gantt_x + ((q_start - min_date).days * gantt_col_width / total_days)
            q_end_x = gantt_x + ((q_end - min_date).days * gantt_col_width / total_days)
            q_width = q_end_x - q_start_x

            if q_width > 0.3 * inch:  # Only draw if there's space
                c.drawCentredString(q_start_x + q_width / 2, header_y - 0.15 * inch, quarter_label)

        # --- MONTH SUBHEADER (below quarters) ---
        subheader_y = header_y - 0.32 * inch
        c.setFillColor(colors.HexColor("#f0f0f0"))
        c.rect(gantt_x, subheader_y - 0.15 * inch, gantt_col_width, 0.15 * inch, fill=1, stroke=0)

        c.setFillColor(colors.HexColor("#333333"))
        c.setFont("Helvetica", 6)

        current_date = min_date
        last_month = None
        while current_date <= max_date:
            month_label = current_date.strftime("%b")
            if current_date.month != last_month:
                x_pos = gantt_x + ((current_date - min_date).days * gantt_col_width / total_days)
                c.drawString(x_pos + 2, subheader_y - 0.08 * inch, month_label)
                last_month = current_date.month
            current_date += timedelta(days=1)

        # --- TASK ROWS ---
        row_y = subheader_y - 0.25 * inch
        row_height = 0.18 * inch

        for idx, task in enumerate(tasks):
            # Alternate row colors
            if idx % 2 == 0:
                c.setFillColor(colors.HexColor("#ffffff"))
            else:
                c.setFillColor(colors.HexColor("#f8f8f8"))

            # Full row background
            c.rect(margin_left, row_y - row_height,
                   page_width - margin_left - margin_right, row_height, fill=1, stroke=0)

            # Row separator line
            c.setStrokeColor(colors.HexColor("#e0e0e0"))
            c.setLineWidth(0.5)
            c.line(margin_left, row_y - row_height,
                   margin_left + page_width - margin_left - margin_right, row_y - row_height)

            # --- LEFT PANEL: DATA ---
            c.setFillColor(colors.HexColor("#1a1a1a"))
            c.setFont("Helvetica", 6.5)

            col_x = margin_left

            # ID
            task_id = str(task.get("id", ""))[:4]
            c.drawCentredString(col_x + 0.125 * inch, row_y - row_height / 2 - 0.02 * inch, task_id)
            col_x += 0.25 * inch

            # Task Mode (icon placeholder)
            c.drawString(col_x + 0.05 * inch, row_y - row_height / 2 - 0.02 * inch, "■")
            col_x += 0.35 * inch

            # Task Name
            task_name = str(task.get("name", ""))
            if len(task_name) > 45:
                task_name = task_name[:42] + "..."

            if task.get("isMilestone"):
                c.setFont("Helvetica-Bold", 6.5)
            c.drawString(col_x + 0.05 * inch, row_y - row_height / 2 - 0.02 * inch, task_name)
            c.setFont("Helvetica", 6.5)
            col_x += 1.45 * inch

            # Duration
            dur = task.get("duration", 0)
            c.drawCentredString(col_x + 0.325 * inch, row_y - row_height / 2 - 0.02 * inch,
                               f"{dur}d" if dur else "-")
            col_x += 0.65 * inch

            # Start Date
            start_date = task.get("start", "-")
            c.drawCentredString(col_x + 0.25 * inch, row_y - row_height / 2 - 0.02 * inch, start_date)
            col_x += 0.5 * inch

            # Finish Date
            finish_date = task.get("finish", "-")
            c.drawCentredString(col_x + 0.25 * inch, row_y - row_height / 2 - 0.02 * inch, finish_date)

            # --- RIGHT PANEL: GANTT BARS ---
            start_obj = parse_date_str(task.get("start", ""))
            finish_obj = parse_date_str(task.get("finish", ""))

            if start_obj and finish_obj:
                bar_start_x = gantt_x + ((start_obj - min_date).days * gantt_col_width / total_days)
                bar_width = ((finish_obj - start_obj).days + 1) * gantt_col_width / total_days
                bar_width = max(bar_width, 2)

                # Color coding
                if task.get("isMilestone"):
                    # Milestone diamond
                    bar_color = colors.HexColor("#F4A620")
                    bar_y_pos = row_y - row_height / 2
                    diamond_size = 0.06 * inch
                    c.setFillColor(bar_color)
                    # Draw diamond
                    c.circle(bar_start_x + diamond_size / 2, bar_y_pos, diamond_size / 2, fill=1, stroke=0)
                else:
                    # Regular bar
                    if task.get("is_critical"):
                        bar_color = colors.HexColor("#D63031")  # Red
                    else:
                        bar_color = colors.HexColor("#4472C4")  # Blue

                    bar_height = 0.09 * inch
                    bar_y_pos = row_y - row_height / 2

                    # Progress fill
                    pct = task.get("percentComplete", 0)
                    if pct > 0:
                        progress_color = colors.HexColor("#70AD47")
                        progress_width = bar_width * (pct / 100.0)
                        c.setFillColor(progress_color)
                        c.rect(bar_start_x, bar_y_pos - bar_height / 2, progress_width, bar_height,
                              fill=1, stroke=0)

                    # Main bar
                    c.setFillColor(bar_color)
                    c.roundRect(bar_start_x, bar_y_pos - bar_height / 2, bar_width, bar_height,
                               radius=1.5, fill=1, stroke=0)

                    # Bar border
                    c.setStrokeColor(colors.HexColor("#333333"))
                    c.setLineWidth(0.5)
                    c.roundRect(bar_start_x, bar_y_pos - bar_height / 2, bar_width, bar_height,
                               radius=1.5, fill=0, stroke=1)

            row_y -= row_height

            # Page break if needed
            if row_y < 1.0 * inch:
                break

        # --- FOOTER ---
        footer_y = 0.25 * inch
        c.setFont("Helvetica", 6)
        c.setFillColor(colors.HexColor("#666666"))
        c.drawString(margin_left, footer_y, f"Date: {datetime.now().strftime('%d-%m-%y')}")

        # Legend
        legend_items = [
            ("Task", colors.HexColor("#4472C4")),
            ("Critical", colors.HexColor("#D63031")),
            ("Milestone", colors.HexColor("#F4A620")),
            ("Progress", colors.HexColor("#70AD47")),
        ]

        leg_x = page_width / 2
        for label, color in legend_items:
            c.setFillColor(color)
            c.rect(leg_x, footer_y - 0.06 * inch, 0.07 * inch, 0.07 * inch, fill=1, stroke=0)
            leg_x += 0.1 * inch

            c.setFillColor(colors.HexColor("#666666"))
            c.setFont("Helvetica", 5.5)
            c.drawString(leg_x, footer_y, label)
            leg_x += 0.75 * inch

        c.drawString(page_width - margin_right - 1.5 * inch, footer_y, "Page 1")

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
