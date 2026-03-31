import sys
import re

file_path = "apps/api/scripts/seed_production.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Vendor insertions
vendor_block = """        vendor_doc = await db.vendors.find_one({"name": "Default Vendor"})
        if not vendor_doc:
            vendor_result = await db.vendors.insert_one({
                "organisation_id": org_id,
                "name": "Default Vendor",
                "active_status": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            })
            vendor_id = str(vendor_result.inserted_id)
        else:
            vendor_id = str(vendor_doc["_id"])"""

new_vendor_block = """        vendors_to_create = ["Default Vendor", "SS Construction", "Suraj Electrician", "Rajesh Construction", "CDSP Global"]
        vendor_map = {}
        for v_name in vendors_to_create:
            v_doc = await db.vendors.find_one({"name": v_name})
            if not v_doc:
                result = await db.vendors.insert_one({
                    "organisation_id": org_id,
                    "name": v_name,
                    "active_status": True,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                })
                vendor_map[v_name] = str(result.inserted_id)
            else:
                vendor_map[v_name] = str(v_doc["_id"])
        vendor_id = vendor_map["Default Vendor"]"""

content = content.replace(vendor_block, new_vendor_block)

# 2. Master Budget Replace
old_budget_section = """        # Consistent realistic budget values from MIS
        original_budget = 12000000 # ~12M Cr
        remaining_budget = 7500000 # After ~4.5M expenditure"""

new_budget_section = """        # Consistent realistic budget values from MIS
        original_budget = 70000000 # 70M Cr
        remaining_budget = 68465000 # Adjusted"""

content = content.replace(old_budget_section, new_budget_section)

# 3. Financial Categories
old_fin_cats = """        financial_categories = [
            {"category_id": "CIV", "original": 10072425, "committed": 10072425, "certified": 4500000},
            {"category_id": "PLB", "original": 350000, "committed": 0, "certified": 0},
            {"category_id": "ELC", "original": 500000, "committed": 13530, "certified": 0},
            {"category_id": "PRF", "original": 200000, "committed": 14000, "certified": 14000},
            {"category_id": "PTC", "original": 100000, "committed": 25000, "certified": 25000},
        ]"""

new_fin_cats = """        financial_categories = [
            {"category_id": "CIV", "original": 15000000, "committed": 10072425, "certified": 1535000},
            {"category_id": "PLB", "original": 5000000, "committed": 0, "certified": 0},
            {"category_id": "ELC", "original": 5000000, "committed": 13530, "certified": 0},
            {"category_id": "PRF", "original": 5000000, "committed": 14000, "certified": 14000},
            {"category_id": "PTC", "original": 85000, "committed": 81300, "certified": 81300},
        ]"""

content = content.replace(old_fin_cats, new_fin_cats)


# 4. WOs and PCs and extra tables
injection_block = """        print(f"  Projected financial states for {len(financial_categories)} categories")

        print("\\n[STEP 7] Seeding Missing WOs, PCs and Site Tasks...")
        await db.work_orders.delete_many({"project_id": project_id})
        await db.payment_certificates.delete_many({"project_id": project_id})
        
        await db.work_orders.insert_many([
            {
                "wo_ref": "TAC_WO_25_003",
                "organisation_id": org_id,
                "project_id": project_id,
                "category_id": code_map.get("ELC"),
                "vendor_id": vendor_map.get("Suraj Electrician"),
                "subtotal": 13530,
                "grand_total": 13530,
                "status": "Completed"
            },
            {
                "wo_ref": "TAC_WO_25_004",
                "organisation_id": org_id,
                "project_id": project_id,
                "category_id": code_map.get("PRF"),
                "vendor_id": vendor_map.get("CDSP Global"),
                "subtotal": 14000,
                "grand_total": 14000,
                "status": "Completed"
            }
        ])
        
        await db.payment_certificates.insert_many([
            {
                "pc_ref": "TAC_PC_25_001",
                "organisation_id": org_id,
                "project_id": project_id,
                "category_id": code_map.get("CIV"),
                "vendor_id": vendor_map.get("SS Construction"),
                "subtotal": 1000000,
                "grand_total": 1000000,
                "status": "Approved"
            },
            {
                "pc_ref": "TAC_PC_25_002",
                "organisation_id": org_id,
                "project_id": project_id,
                "category_id": code_map.get("CIV"),
                "vendor_id": vendor_map.get("Rajesh Construction"),
                "subtotal": 535000,
                "grand_total": 535000,
                "status": "Approved"
            }
        ])
        
        print("  Created missing entities.")"""

content = content.replace("""        print(f"  Projected financial states for {len(financial_categories)} categories")""", injection_block)


with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Second seed fixes applied.")
