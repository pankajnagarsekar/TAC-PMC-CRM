import sys

from pymongo import MongoClient


def check_indexes():
    client = MongoClient("mongodb://localhost:27017")
    db = client["tac_pmc_crm"]

    collections = ["organisations", "users", "code_master", "projects"]
    for coll_name in collections:
        print(f"--- Indexes for {coll_name} ---")
        for index in db[coll_name].list_indexes():
            print(index)
    client.close()


if __name__ == "__main__":
    check_indexes()
