import sys
import re

file_path = "apps/api/scripts/seed_production.py"
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

# Fix fallback for user_map['Admin'] if changed just in case
text = text.replace('user_map["Admin"]', 'user_map.get("Admin", "")')

old_step_3 = """        for code in codes:
            # Sync to financial_codes (legacy/internal)
            existing = await db.financial_codes.find_one({"code": code["code"]})
            if not existing:
                await db.financial_codes.insert_one(
                    {
                        **code,
                        "organisation_id": org_id,
                        "created_at": datetime.now(timezone.utc),
                    }
                )
            # Sync to code_master (DDD repository standard)
            existing_master = await db.code_master.find_one({"code": code["code"]})
            if not existing_master:
                await db.code_master.insert_one(
                    {
                        "code": code["code"],
                        "code_short": code["code"],
                        "description": code["description"],
                        "category": code["category"],
                        "organisation_id": org_id,
                        "is_active": True,
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    }
                )
        print(f"  Created/verified {len(codes)} financial codes in both collections")"""

new_step_3 = """        print("\\n[STEP 3.5] Creating Client & Vendor...")
        client_doc = await db.clients.find_one({"name": "Mr. Sanjay Rao"})
        if not client_doc:
            client_result = await db.clients.insert_one({
                "organisation_id": org_id,
                "name": "Mr. Sanjay Rao",
                "address": "Majorda",
                "city": "South Goa",
                "state": "Goa",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            })
            client_id = str(client_result.inserted_id)
        else:
            client_id = str(client_doc["_id"])
            
        vendor_doc = await db.vendors.find_one({"name": "Default Vendor"})
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
            vendor_id = str(vendor_doc["_id"])

        code_map = {}
        for code in codes:
            existing_master = await db.code_master.find_one({"code": code["code"]})
            if not existing_master:
                result = await db.code_master.insert_one(
                    {
                        "code": code["code"],
                        "code_short": code["code"],
                        "code_description": code["description"],
                        "category_name": code["category"],
                        "organisation_id": org_id,
                        "active_status": True,
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    }
                )
                code_map[code["code"]] = str(result.inserted_id)
            else:
                code_map[code["code"]] = str(existing_master["_id"])
                # update fields if exists
                await db.code_master.update_one({"_id": existing_master["_id"]}, {"$set": {"code_description": code["description"], "category_name": code["category"], "active_status": True}})
        print(f"  Created/verified {len(codes)} financial codes in code_master")"""

if old_step_3 in text:
    text = text.replace(old_step_3, new_step_3)
else:
    print("WARNING: Step 3 replacement failed")


old_project = """            # Ensure budget is updated
            await db.projects.update_one(
                {"_id": project["_id"]},
                {"$set": {
                    "master_original_budget": original_budget, 
                    "master_remaining_budget": remaining_budget,
                    "completion_percentage": 18,
                    "client_name": "Mr. Sanjay Rao",
                    "location": "Majorda, South Goa"
                }}
            )
        else:
            project_oid = ObjectId()
            await db.projects.insert_one(
                {
                    "_id": project_oid,
                    "project_id": str(project_oid),
                    "project_name": "Majorda Villa - Civil Works",
                    "client_name": "Mr. Sanjay Rao",
                    "status": "active",
                    "project_type": "Luxury Construction",
                    "start_date": datetime(2026, 2, 20, tzinfo=timezone.utc),
                    "end_date": datetime(2026, 12, 15, tzinfo=timezone.utc),
                    "description": "Premium villa construction project in Majorda.",
                    "location": "Majorda, South Goa",
                    "owner": "TAC-PMC",
                    "organisation_id": org_id,
                    "created_by": user_map.get("Admin", ""),
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                    "master_original_budget": original_budget,
                    "master_remaining_budget": remaining_budget,
                    "completion_percentage": 18,
                    "version": 1,
                }
            )"""

new_project = """            # Ensure budget is updated
            await db.projects.update_one(
                {"_id": project["_id"]},
                {"$set": {
                    "master_original_budget": original_budget, 
                    "master_remaining_budget": remaining_budget,
                    "completion_percentage": 18,
                    "client_id": client_id,
                    "address": "Majorda",
                    "city": "South Goa",
                    "state": "Goa"
                }}
            )
        else:
            project_oid = ObjectId()
            await db.projects.insert_one(
                {
                    "_id": project_oid,
                    "project_code": "MV-01",
                    "project_name": "Majorda Villa - Civil Works",
                    "client_id": client_id,
                    "status": "active",
                    "address": "Majorda",
                    "city": "South Goa",
                    "state": "Goa",
                    "project_retention_percentage": 0.0,
                    "project_cgst_percentage": 9.0,
                    "project_sgst_percentage": 9.0,
                    "organisation_id": org_id,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                    "master_original_budget": original_budget,
                    "master_remaining_budget": remaining_budget,
                    "completion_percentage": 18,
                    "threshold_petty": 0.0,
                    "threshold_ovh": 0.0,
                    "version": 1,
                }
            )"""

if old_project in text:
    text = text.replace(old_project, new_project)
else:
    print("WARNING: Project replacement failed")

old_fin = """        for fc in financial_categories:
            await db.financial_state.update_one(
                {"project_id": project_id, "category_id": fc["category_id"]},
                {"$set": {
                    "original_budget": fc["original"],
                    "committed_value": fc["committed"],
                    "certified_value": fc["certified"],
                    "balance_budget_remaining": fc["original"] - fc["committed"],
                    "updated_at": datetime.now(timezone.utc)
                }},
                upsert=True
            )"""

new_fin = """        for fc in financial_categories:
            code_id = code_map.get(fc["category_id"])
            if not code_id: continue
            await db.financial_state.update_one(
                {"project_id": project_id, "code_id": code_id},
                {"$set": {
                    "original_budget": fc["original"],
                    "committed_value": fc["committed"],
                    "certified_value": fc["certified"],
                    "balance_budget_remaining": fc["original"] - fc["committed"],
                    "last_updated": datetime.now(timezone.utc)
                }},
                upsert=True
            )"""

if old_fin in text:
    text = text.replace(old_fin, new_fin)
else:
    print("WARNING: Finance replacement failed")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(text)

print("Fixes applied.")
