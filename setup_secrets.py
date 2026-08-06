"""
One-time setup: creates Databricks secret scope and stores the Lakebase URL.
Run from a Databricks notebook or any environment with the Databricks CLI configured.

Usage:
    python setup_secrets.py
"""
import getpass
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import workspace

w = WorkspaceClient()

# Create scope (ignore error if it already exists)
try:
    w.secrets.create_scope(scope="database")
    print("Created secret scope 'database'.")
except Exception as e:
    print(f"Scope 'database' already exists or error: {e}")

# Store the Lakebase connection URL
lakebase_url = getpass.getpass("Paste your Lakebase connection URL: ")
w.secrets.put_secret(scope="database", key="lakebase-url", string_value=lakebase_url)
print("Stored 'database/lakebase-url'.")

# Grant read to all workspace users so the App can access it
try:
    w.secrets.put_acl(scope="database", principal="users", permission=workspace.AclPermission.READ)
    print("Granted READ to all users.")
except Exception as e:
    print(f"ACL note: {e}")

print("\nDone! You can now deploy the app.")
