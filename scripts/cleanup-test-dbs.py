import os
import pymongo

# Resolve the backend .env file to load MONGO_URL if settings config is not loaded
MONGO_URL = "mongodb+srv://tacpmc_db_user:OVCxtaNhDGMuBeq6@clustertacpmc.8cbzigp.mongodb.net/?appName=ClusterTACPMC"

# Try loading from apps/api/.env if present
env_path = os.path.join(os.path.dirname(__file__), "..", "apps", "api", ".env")
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            if line.startswith("MONGO_URL="):
                MONGO_URL = line.strip().split("=", 1)[1]
                break

try:
    print("Connecting to MongoDB Atlas to clean up test databases...")
    client = pymongo.MongoClient(MONGO_URL, tlsAllowInvalidCertificates=True)
    dbs = client.list_database_names()

    dropped_count = 0
    for db_name in dbs:
        if db_name.startswith("tac_pmc_client_") or db_name.startswith("tac_pmc_test_"):
            print(f"Dropping leftover database: {db_name}")
            try:
                client.drop_database(db_name)
                dropped_count += 1
            except Exception as drop_err:
                print(f"Warning: Failed to drop database {db_name}: {drop_err}")

    if dropped_count > 0:
        print(f"Successfully cleaned up {dropped_count} database(s)!")
    else:
        print("No leftover test databases found.")

except Exception as e:
    print(f"Error occurred during test database cleanup: {e}")
