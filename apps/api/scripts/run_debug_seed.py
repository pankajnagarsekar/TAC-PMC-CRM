import seed_majorda
from pymongo import MongoClient
from pymongo.errors import BulkWriteError
import os

def run():
    client = MongoClient("mongodb://localhost:27017")
    db = client["tac_pmc_crm"]
    try:
        print("Loading data...")
        data = seed_majorda.load_excel()
        print("Cleaning up...")
        seed_majorda.cleanup_db(db)
        print("Seeding...")
        seed_majorda.seed(db, data)
        print("Success!")
    except BulkWriteError as bwe:
        print("BulkWriteError details:")
        # Print first error
        print(bwe.details['writeErrors'][0])
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    run()
