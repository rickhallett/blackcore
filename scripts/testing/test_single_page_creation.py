#!/usr/bin/env python3
"""
Test creating a single page to debug the issue.
"""

import os
from notion_client import Client

# Initialize Notion client
notion = Client(auth=os.getenv("NOTION_API_KEY"))

# Test creating a person
database_id = "21f4753d-608e-8173-b6dc-fc6302804e69"  # People & Contacts

properties = {
    "Full Name": {"title": [{"text": {"content": "Test Person Debug"}}]},
    "Role": {"select": {"name": "Ally"}},
    "Status": {"select": {"name": "Active Engagement"}},
    "Notes": {"rich_text": [{"text": {"content": "Test notes for debugging"}}]},
}

print("Creating page with properties:")
print(properties)

try:
    response = notion.pages.create(
        parent={"database_id": database_id}, properties=properties
    )
    print("\n✅ Success! Page created with ID:", response["id"])
except Exception as e:
    print("\n❌ Error:", str(e))
