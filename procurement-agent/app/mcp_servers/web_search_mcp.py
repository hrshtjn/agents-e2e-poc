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

mcp = FastMCP("WebSearchStub")

# Stub web search results for procurement/market research
MOCK_SEARCH_RESULTS = {
    "ergonomic chairs price": [
        {"title": "Office Depot: Ergonomic Chairs & Seating", "snippet": "Find top-quality ergonomic chairs starting from $199. Fully adjustable lumbar support, 4D armrests, and premium mesh fabric.", "url": "https://www.officedepot.mock/ergonomic-chairs"},
        {"title": "Steelcase Office Chairs Review 2026", "snippet": "The Steelcase Gesture and Leap remain the gold standard for ergonomics. Prices range from $800 to $1,400 with a 12-year warranty.", "url": "https://www.officechairreviews.mock/steelcase-gesture"}
    ],
    "developer laptops comparison": [
        {"title": "TechRadar: Best Laptops for Developers 2026", "snippet": "Compare performance, battery life, and keyboard quality. MacBook Pro 16 M3 Max and Lenovo ThinkPad P1 Gen 6 top the developer choices.", "url": "https://www.techradar.mock/best-developer-laptops"},
        {"title": "Dell XPS 15 vs ThinkPad X1 Carbon for Coding", "snippet": "X1 Carbon wins on portability and keyboard comfort. Dell XPS 15 is better for GPU-intensive development tasks.", "url": "https://www.devcommunity.mock/laptops-comparison"}
    ],
    "vendor rating techpro hardware": [
        {"title": "TrustPilot: TechPro Hardware reviews", "snippet": "TechPro Hardware has a 4.8/5 rating. Customers praise fast delivery, responsive customer support, and excellent bulk business pricing.", "url": "https://www.trustpilot.mock/techpro-hardware"}
    ],
    "innovate software license pricing": [
        {"title": "Innovate Software Enterprise Pricing Table", "snippet": "Innovate Software Cloud Security Suite licenses start at $50/user/month. Bulk discounts available for orders over 50 licenses ($45/user/month).", "url": "https://www.innovatesoftware.mock/pricing"}
    ]
}

@mcp.tool()
def search(query: str) -> str:
    """Performs a web search to gather market research, price comparisons, or vendor ratings.
    
    Args:
        query: The search query string.
    """
    query_lower = query.lower()
    for key, results in MOCK_SEARCH_RESULTS.items():
        if all(word in query_lower for word in key.split()):
            return json.dumps(results, indent=2)
            
    # Default fallback search response
    fallback = [
        {
            "title": f"Search Results for '{query}'",
            "snippet": f"Here are the mock web search results for the query '{query}'. No exact match was found in the database, but this stub verifies the tool execution and MCP server integration.",
            "url": f"https://www.stubsearch.mock/search?q={query}"
        }
    ]
    return json.dumps(fallback, indent=2)

@mcp.tool()
def fetch_url(url: str) -> str:
    """Fetches the text content of a web page for detailed reading.
    
    Args:
        url: The absolute URL of the web page to fetch.
    """
    return f"Mock page content for {url}: This is the stubbed web page content. It contains detailed information and specs retrieved from the mock site."

if __name__ == "__main__":
    mcp.run()
