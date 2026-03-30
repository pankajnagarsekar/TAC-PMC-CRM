from pymongo import MongoClient


def hard_reset():
    client = MongoClient("mongodb://localhost:27017")
    db = client["tac_pmc_crm"]

    collections = [
        "organisations",
        "users",
        "code_master",
        "projects",
        "clients",
        "vendors",
        "work_orders",
        "payment_certificates",
        "global_settings",
        "notifications",
        "project_category_budgets",
        "financial_state",
        "fund_allocations",
        "cash_transactions",
        "vendor_ledger",
        "site_overheads",
        "dprs",
        "attendance",
        "workers_daily_logs",
        "voice_logs",
        "audit_logs",
        "sequences",
        "user_project_map",
    ]

    print("--- HARD RESET ---")
    for coll in collections:
        res = db[coll].delete_many({})
        print(f"Deleted {res.deleted_count} from {coll}")

    print("Reset complete.")
    client.close()


if __name__ == "__main__":
    hard_reset()
