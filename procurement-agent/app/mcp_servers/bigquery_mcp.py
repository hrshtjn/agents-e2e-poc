# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mcp.server.fastmcp import FastMCP
import json

mcp = FastMCP("BigQueryStub")

# Stub data
VENDORS = [
    {"vendor_id": "V001", "name": "Global Office Supplies", "rating": 4.5, "category": "Office Supplies", "preferred": True},
    {"vendor_id": "V002", "name": "TechPro Hardware", "rating": 4.8, "category": "Hardware", "preferred": True},
    {"vendor_id": "V003", "name": "Apex Catering", "rating": 4.2, "category": "Catering", "preferred": False},
    {"vendor_id": "V004", "name": "Innovate Software", "rating": 4.9, "category": "Software", "preferred": True},
    {"vendor_id": "V005", "name": "Reliable Logistics", "rating": 3.9, "category": "Logistics", "preferred": False},
]

PURCHASE_ORDERS = [
    {"po_id": "PO1001", "vendor_id": "V001", "item": "Ergonomic Chairs", "quantity": 50, "unit_price": 250.00, "status": "Delivered", "date": "2026-05-15"},
    {"po_id": "PO1002", "vendor_id": "V002", "item": "Developer Laptops", "quantity": 20, "unit_price": 1800.00, "status": "Pending", "date": "2026-06-01"},
    {"po_id": "PO1003", "vendor_id": "V004", "item": "Cloud Security Suite Licenses", "quantity": 100, "unit_price": 45.00, "status": "Approved", "date": "2026-06-10"},
]

INVENTORY = [
    {"item_id": "I101", "name": "Ergonomic Chairs", "stock": 12, "reorder_level": 15},
    {"item_id": "I102", "name": "Developer Laptops", "stock": 5, "reorder_level": 8},
    {"item_id": "I103", "name": "Standard Desks", "stock": 25, "reorder_level": 10},
]

@mcp.tool()
def query_bigquery(query: str) -> str:
    """Executes a SQL-like query against the stub BigQuery procurement tables (vendors, purchase_orders, inventory).
    
    Args:
        query: SQL query string to execute. Supported keywords in stub: vendors, purchase_orders, inventory.
    """
    query_lower = query.lower()
    if "vendors" in query_lower:
        return json.dumps(VENDORS, indent=2)
    elif "purchase_orders" in query_lower or "po" in query_lower:
        return json.dumps(PURCHASE_ORDERS, indent=2)
    elif "inventory" in query_lower:
        return json.dumps(INVENTORY, indent=2)
    else:
        return "Error: Table not found or query not recognized in stub database. Supported tables: vendors, purchase_orders, inventory."

@mcp.tool()
def list_tables() -> str:
    """Lists available tables in the BigQuery dataset."""
    return json.dumps(["vendors", "purchase_orders", "inventory"], indent=2)

@mcp.tool()
def get_table_schema(table_name: str) -> str:
    """Returns the schema of the specified table.
    
    Args:
        table_name: The name of the table ('vendors', 'purchase_orders', or 'inventory').
    """
    schemas = {
        "vendors": {
            "vendor_id": "STRING (Primary Key)",
            "name": "STRING",
            "rating": "FLOAT",
            "category": "STRING",
            "preferred": "BOOLEAN"
        },
        "purchase_orders": {
            "po_id": "STRING (Primary Key)",
            "vendor_id": "STRING (Foreign Key to vendors)",
            "item": "STRING",
            "quantity": "INTEGER",
            "unit_price": "FLOAT",
            "status": "STRING",
            "date": "STRING"
        },
        "inventory": {
            "item_id": "STRING (Primary Key)",
            "name": "STRING",
            "stock": "INTEGER",
            "reorder_level": "INTEGER"
        }
    }
    return json.dumps(schemas.get(table_name.lower(), f"Error: Table {table_name} not found."), indent=2)

if __name__ == "__main__":
    mcp.run()
