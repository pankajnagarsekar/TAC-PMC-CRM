import unittest
from datetime import datetime, date, timedelta
import sys
import os

# Add the parent directory to sys.path to import the script to be tested
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from calculate_critical_path import calculate_critical_path

class TestCriticalPath(unittest.TestCase):
    def test_basic_critical_path(self):
        # T1 (5) -> T2 (3) -> T4 (2)
        # T1 (5) -> T3 (4) -> T4 (2)
        # Critical Path: T1 -> T3 -> T4 (11 days)
        tasks = [
            {"id": "T1", "name": "Task 1", "duration": 5, "predecessors": []},
            {"id": "T2", "name": "Task 2", "duration": 3, "predecessors": ["T1"]},
            {"id": "T3", "name": "Task 3", "duration": 4, "predecessors": ["T1"]},
            {"id": "T4", "name": "Task 4", "duration": 2, "predecessors": ["T2", "T3"]}
        ]
        
        # Start date: 01-01-2026 (Thursday)
        # 6-day week (Mon-Sat are work days, Sun is holiday)
        start_date = "01-01-26"
        
        result = calculate_critical_path(tasks, start_date)
        
        # Check finish dates
        # T1: Start Thu 01-01, Finish Tue 06-01 (Thu, Fri, Sat, Mon, Tue = 5 days)
        # T3: Start Wed 07-01, Finish Sat 10-01 (Wed, Thu, Fri, Sat = 4 days)
        # T4: Start Mon 12-01, Finish Tue 13-01 (Mon, Tue = 2 days)
        
        # Verify Critical Path
        critical_ids = [t["id"] for t in result if t.get("is_critical")]
        self.assertIn("T1", critical_ids)
        self.assertIn("T3", critical_ids)
        self.assertIn("T4", critical_ids)
        self.assertNotIn("T2", critical_ids)
        
        # Verify total project duration
        # Finish of T4 should be 13-01-26
        t4 = next(t for t in result if t["id"] == "T4")
        self.assertEqual(t4["finish"], "13-01-26")

if __name__ == "__main__":
    unittest.main()
