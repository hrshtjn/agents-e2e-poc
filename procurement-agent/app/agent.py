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

import os
import sys

from dotenv import load_dotenv

# Load .env file from the same directory as this file (app/.env)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

import google.auth
from google.auth.transport.requests import Request
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.planners import PlanReActPlanner
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_toolset import StdioServerParameters
from google.adk.tools.mcp_tool.mcp_toolset import SseConnectionParams
from google.genai import types

# Model Armor safety callbacks (Step 9 — MODEL_ARMOR_SETUP.md)
from app.security.model_armor_guard import screen_input, screen_output


# Setup Google Cloud project configuration with safe fallback for local tests
try:
    _, project_id = google.auth.default()
except Exception:
    project_id = None

project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT") or "procurement-project-dummy"
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

# Resolve absolute paths to local MCP stub servers
# We use sys.executable to run the stub script within the same virtual environment
mcp_servers_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_servers")
bigquery_stub_path = os.path.join(mcp_servers_dir, "bigquery_mcp.py")
web_search_stub_path = os.path.join(mcp_servers_dir, "web_search_mcp.py")

# Configure MCP Server Toolsets
# bigquery_toolset = McpToolset(
#     connection_params=StdioServerParameters(
#         command=sys.executable,
#         args=[bigquery_stub_path],
#     ),
#     tool_name_prefix="bigquery_"
# )

# Fetch Identity Token for Service-to-Service auth to Cloud Run
cloud_run_url = "https://bq-mcp-server-905882810521.us-east1.run.app"
try:
    credentials, auth_project_id = google.auth.default()
    request = Request()
    id_token_credentials = google.auth.default_identity_token(audience=cloud_run_url, request=request)
    id_token = id_token_credentials.token
except Exception as e:
    print(f"Warning: Failed to fetch Identity Token. Proceeding without auth headers: {e}")
    id_token = None

headers = {"Authorization": f"Bearer {id_token}"} if id_token else None

bigquery_toolset = McpToolset(
    connection_params=SseConnectionParams(
        url=f"{cloud_run_url}/sse",
        headers=headers
    ),
    tool_name_prefix="bigquery_"
)

web_search_toolset = McpToolset(
    connection_params=StdioServerParameters(
        command=sys.executable,
        args=[web_search_stub_path],
    ),
    tool_name_prefix="web_search_"
)

# Instantiate the ReAct Planner
react_planner = PlanReActPlanner()

# Define the Procurement & Research Agent
root_agent = Agent(
    name="procurement_agent",
    model=Gemini(
        model="gemini-3.5-flash",  # Default model for general reasoning and tool usage
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are an autonomous Procurement & Research Agent. Your job is to assist the user with vendor lookup, purchase order tracking, stock levels, and market research.

You have access to two sets of tools:
1. BigQuery tools (prefixed with 'bigquery_'): Use these to query databases for vendors, purchase orders, and inventory information.
2. Web Search tools (prefixed with 'web_search_'): Use these to perform search queries for market research, price comparisons, and vendor reviews.

Strict Guidelines:
1. Always gather facts using your tools rather than guessing.
2. Use the BigQuery tables first when searching for internal details (preferred vendors, existing purchase orders, inventory).
3. Use Web Search tools when analyzing external details (such as market prices or vendor reputation).
4. Present your findings in a structured, professional format.
""",
    tools=[bigquery_toolset, web_search_toolset],
    # planner=react_planner,
    # Model Armor: screen every prompt before it hits Gemini, and every
    # response before it is returned to the user. Controlled via
    # MODEL_ARMOR_TEMPLATE and MODEL_ARMOR_FAIL_OPEN env vars (see app/.env).
    before_model_callback=screen_input,
    after_model_callback=screen_output,
)

# Create the ADK App
app = App(
    root_agent=root_agent,
    name="app",
)
