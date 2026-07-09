import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

def parse_date(val):
    if not val or val in ("0", "null", "undefined", "—"):
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(val, fmt)
        except:
            continue
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except:
        return None

async def inspect():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["tac_pmc_crm"]
    
    print("\n--- TIMELINE CALCULATION EMULATION ---")
    schedule = await db.project_schedules.find_one({"project_id": "69e26e2ebf1296a11a2f6942"})
    if schedule:
        tasks = schedule.get("tasks", [])
        parsed_dates = []
        for t in tasks:
            for field in ["scheduled_start", "scheduled_finish", "baseline_start", "baseline_finish", "early_start", "late_finish"]:
                d = parse_date(t.get(field))
                if d:
                    parsed_dates.append((t.get("task_id"), t.get("task_name"), field, d))
        
        print(f"Total parsed dates: {len(parsed_dates)}")
        if parsed_dates:
            min_date_item = min(parsed_dates, key=lambda x: x[3])
            max_date_item = max(parsed_dates, key=lambda x: x[3])
            print(f"Min Date: {min_date_item[3]} (Task {min_date_item[0]} - {min_date_item[1]} - {min_date_item[2]})")
            print(f"Max Date: {max_date_item[3]} (Task {max_date_item[0]} - {max_date_item[1]} - {max_date_item[2]})")
    else:
        print("Schedule not found.")

if __name__ == "__main__":
    asyncio.run(inspect())
