import json
import sys
from datetime import datetime
from typing import List, Dict, Any

def generate_cash_report(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Groups costs by Month-Year based on finish dates.
    Input: List[{ id, name, finish, cost }]
    finish: "DD-MM-YY"
    """
    monthly_outflow = {}
    
    for task in tasks:
        try:
            finish_date = datetime.strptime(task["finish"], "%d-%m-%y")
            month_key = finish_date.strftime("%b %Y") # e.g., "Jan 2026"
            cost = float(task.get("cost", 0))
            
            if month_key not in monthly_outflow:
                monthly_outflow[month_key] = 0.0
            
            monthly_outflow[month_key] += cost
        except Exception:
            continue
            
    # Sort keys by date
    sorted_months = sorted(monthly_outflow.keys(), key=lambda x: datetime.strptime(x, "%b %Y"))
    
    report = [
        {"month": month, "outflow": monthly_outflow[month]}
        for month in sorted_months
    ]
    
    return {
        "monthly_outflow_forecast": report,
        "total_outflow": sum(monthly_outflow.values()),
        "generated_at": datetime.now().isoformat()
    }

if __name__ == "__main__":
    try:
        input_data = json.load(sys.stdin)
        tasks = input_data.get("tasks", [])
        report = generate_cash_report(tasks)
        print(json.dumps(report))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
