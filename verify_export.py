
import os
import sys
import unittest
from fastapi.testclient import TestClient
from server import app

class TestExport(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_export_all(self):
        print("Testing Export All...")
        response = self.client.get("/api/announcements/export?q=&province=&export_type=all")
        if response.status_code == 400 and "No data" in response.json().get("error", ""):
            print("No data to export, skipping content check.")
            return
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.assertTrue(response.content.startswith(b"PK"), "Should appear to be a zip/xlsx file (start with PK)")
        print("Export All OK")

    def test_export_province(self):
        print("Testing Export by Province...")
        response = self.client.get("/api/announcements/export?q=&province=&export_type=province")
        if response.status_code == 400 and "No data" in response.json().get("error", ""):
             print("No data to export, skipping content check.")
             return

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/zip")
        self.assertTrue(response.content.startswith(b"PK"), "Should be a zip file")
        print("Export Province OK")

    def test_export_day(self):
        print("Testing Export by Day...")
        response = self.client.get("/api/announcements/export?q=&province=&export_type=day")
        if response.status_code == 400 and "No data" in response.json().get("error", ""):
            print("No data to export, skipping content check.")
            return

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/zip")
        self.assertTrue(response.content.startswith(b"PK"), "Should be a zip file")
        print("Export Day OK")

if __name__ == "__main__":
    unittest.main()
