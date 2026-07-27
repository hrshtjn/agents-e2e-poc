# procurement-agent

Simple ReAct agent
Agent generated with `agents-cli` version `0.3.0`

## Project Structure

```
procurement-agent/
├── app/         # Core agent code
│   ├── agent.py               # Main agent logic
│   ├── agent_runtime_app.py    # Agent Runtime application logic
│   └── app_utils/             # App utilities and helpers
├── tests/                     # Unit, integration, and load tests
├── GEMINI.md                  # AI-assisted development guide
└── pyproject.toml             # Project dependencies
```

> 💡 **Tip:** Use [Gemini CLI](https://github.com/google-gemini/gemini-cli) for AI-assisted development - project context is pre-configured in `GEMINI.md`.

## Requirements

Before you begin, ensure you have:
- **uv**: Python package manager (used for all dependency management in this project) - [Install](https://docs.astral.sh/uv/getting-started/installation/) ([add packages](https://docs.astral.sh/uv/concepts/dependencies/) with `uv add <package>`)
- **agents-cli**: Agents CLI - Install with `uv tool install google-agents-cli`
- **Google Cloud SDK**: For GCP services - [Install](https://cloud.google.com/sdk/docs/install)


## Quick Start

Install `agents-cli` and its skills if not already installed:

```bash
uvx google-agents-cli setup
```

Install required packages:

```bash
agents-cli install
```

Test the agent with a local web server:

```bash
agents-cli playground
```

You can also use features from the [ADK](https://adk.dev/) CLI with `uv run adk`.

## Commands

| Command              | Description                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------- |
| `agents-cli install` | Install dependencies using uv                                                         |
| `agents-cli playground` | Launch local development environment                                                  |
| `agents-cli lint`    | Run code quality checks                                                               |
| `agents-cli eval`    | Evaluate agent behavior (generate, grade, analyze, and more — see `agents-cli eval --help`) |
| `uv run pytest tests/unit tests/integration` | Run unit and integration tests                                                        |
| `agents-cli deploy`  | Deploy agent to Agent Runtime                                                                |
| `agents-cli publish gemini-enterprise` | Register deployed agent to Gemini Enterprise                    |

## 🛠️ Project Management

| Command | What It Does |
|---------|--------------|
| `agents-cli scaffold enhance` | Add CI/CD pipelines and Terraform infrastructure |
| `agents-cli infra cicd` | One-command setup of entire CI/CD pipeline + infrastructure |
| `agents-cli scaffold upgrade` | Auto-upgrade to latest version while preserving customizations |

---

## Development

Edit your agent logic in `app/agent.py` and test with `agents-cli playground` - it auto-reloads on save.

## Deployment

```bash
gcloud config set project <your-project-id>
agents-cli deploy
```

To add CI/CD and Terraform, run `agents-cli scaffold enhance`.
To set up your production infrastructure, run `agents-cli infra cicd`.

## Observability

Built-in telemetry exports to Cloud Trace, BigQuery, and Cloud Logging.


The MCP Inspector is a web-based UI that lets you connect to your MCP servers and interactively call tools, inspect schemas, and see responses.

  ### Run it against your stub servers
    cd procurement-agent

    # For the BigQuery stub
    npx -y @modelcontextprotocol/inspector uv run python app/mcp_servers/bigquery_mcp.py
    
    # For the Web Search stub
    npx -y @modelcontextprotocol/inspector uv run python app/mcp_servers/web_search_mcp.py

## Test Prompts for Your Procurement Agent

  ### 🔍 Vendor Lookup (BigQuery)

  1.  "List all preferred vendors"  — Tests if the agent queries the vendors table and filters by  preferred: true .
  2.  "Who is our hardware vendor and what's their rating?"  — Tests category-based lookup (should find TechPro Hardware, 4.8).
  3.  "Do we have a preferred catering vendor?"  — Tests handling of  preferred: false  (Apex Catering is not preferred).

  ### 📦 Purchase Order Tracking (BigQuery)

  4.  "What is the status of PO1002?"  — Tests PO lookup (should return "Pending" for Developer Laptops).
  5.  "Show me all pending purchase orders"  — Tests filtering POs by status.
  6.  "How much are we spending on the cloud security suite licenses order?"  — Tests if the agent calculates total (100 × $45 = $4,500 for PO1003).

  ### 📊 Inventory / Stock Levels (BigQuery)

  7.  "Which items are below their reorder level?"  — Tests inventory analysis (Ergonomic Chairs: 12 < 15, Developer Laptops: 5 < 8).
  8.  "How many developer laptops do we have in stock?"  — Simple stock check (should return 5).

  ### 🌐 Market Research (Web Search)

  9.  "What's the current market price for ergonomic chairs?"  — Tests web search for pricing ($199–$1,400 range from stubs).
  10.  "Compare the best developer laptops for our team"  — Tests web search for laptop comparisons.
  11.  "What do reviews say about TechPro Hardware?"  — Tests vendor reputation lookup via web search (4.8/5 TrustPilot).

  ### 🔀 Multi-Tool / Cross-Capability (BigQuery + Web Search)

  12.  "We need to reorder ergonomic chairs. Check our current stock, find the existing PO, and research current market prices"  — Tests the agent chaining all
  three: inventory → PO → web search.
  13.  "Compare our PO price for developer laptops against current market rates"  — Tests if it pulls PO unit price ($1,800) and cross-references with web search
  results.
  14.  "We're evaluating Innovate Software for license renewal. Pull their vendor rating from our records and check their current pricing online"  — Tests BigQuery
  vendor lookup + web search pricing.

  ### ⚠️ Edge Cases & Robustness

  15.  "What tables are available in the database?"  — Tests the  list_tables  tool.
  16.  "Show me the schema for the purchase_orders table"  — Tests the  get_table_schema  tool.
  17.  "Find me a vendor for janitorial services"  — Tests graceful handling when no matching vendor/category exists in the stub data.
  18.  "Hello"  — Tests basic greeting without triggering unnecessary tool calls.
  ──────
  The multi-tool prompts (12–14) are the most valuable for testing the ReAct planner's reasoning chain. The edge cases (15–18) help verify robustness. I'd recommend
  starting with a simple single-tool prompt (like #2 or #8) and then graduating to multi-tool ones.