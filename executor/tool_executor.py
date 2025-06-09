# tool_executor.py
import sys
import os
import json
import uuid
import requests
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL")
dirname = os.path.dirname(__file__)


class ToolExecutor:
    """
    Executes crawler tool calls against a backend service, managing per-user link indexing
    and persisting fetched data to disk.

    Workflow per item:
      1. Validate the tool_name and HTTP method.
      2. Ensure user folder exists and load/update link_index.json (mapping link_id ↔ link).
      3. Build the request URL: {backend_url}/{tool_name}{endpoint}.
      4. Perform HTTP GET.
      5. Save raw JSON response (or error info) to {user_folder}/{link_id}.json.
      6. Collect and return a summary record per link.
    """

    VALID_TOOLS = {
        "crawl_get_site_links": ["GET"],
        "crawl_external_content": ["GET"],
    }

    def __init__(
        self,
        user_id: str = "001",
        backend_url: str = BACKEND_URL
    ):
        self.user_id = user_id
        self.backend_url = backend_url.rstrip("/")
        self.user_folder = os.path.join(dirname,"..", "data/user_data", self.user_id)
        os.makedirs(self.user_folder, exist_ok=True)
        self.index_path = os.path.join(self.user_folder, "link_index.json")
        self._load_or_init_index()

    def _load_or_init_index(self) -> None:
        if os.path.exists(self.index_path):
            with open(self.index_path, "r", encoding="utf-8") as f:
                self.link_index: Dict[str, str] = json.load(f)
        else:
            self.link_index = {}
            with open(self.index_path, "w", encoding="utf-8") as f:
                json.dump(self.link_index, f, indent=2)

    def _get_or_create_link_id(self, link: str) -> str:
        # reuse existing ID if link is already indexed
        for lid, lnk in self.link_index.items():
            if lnk == link:
                return lid
        # else generate new
        new_id = uuid.uuid4().hex
        self.link_index[new_id] = link
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(self.link_index, f, indent=2)
        return new_id

    def execute(
        self,
        items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Process each tool-instruction item and return a list of result records.

        items: [
          {
            "link": "...",
            "reasoning": "...",
            "tool_name": "...",
            "parameters": { "endpoint": "?url=...&search=...&..." }
          },
          ...
        ]
        """
        results = []

        for item in items:
            link       = item.get("link")
            tool       = item.get("tool_name")
            endpoint   = item.get("parameters", {}).get("endpoint", "")
            record: Dict[str, Any] = {
                "link": link,
                "tool": tool,
                "link_id": None,
                "status_code": None,
                "error": None,
                "output_file": None
            }

            # 1. Validate tool and method
            if tool not in self.VALID_TOOLS:
                record["error"] = f"Invalid tool: {tool}"
                results.append(record)
                continue

            if "GET" not in self.VALID_TOOLS[tool]:
                record["error"] = f"Unsupported HTTP method for {tool}"
                results.append(record)
                continue

            # 2. Assign or create link_id
            try:
                link_id = self._get_or_create_link_id(link)
                record["link_id"] = link_id
            except Exception as e:
                record["error"] = f"Indexing error: {e}"
                results.append(record)
                continue

            # 3. Build and perform HTTP request
            url = f"{self.backend_url}/{tool}{endpoint}"
            try:
                resp = requests.get(url, timeout=30)
                record["status_code"] = resp.status_code
                data = {
                    "status_code": resp.status_code,
                    "body": resp.json() if resp.headers.get("Content-Type", "").startswith("application/json") else resp.text
                }
            except Exception as e:
                record["status_code"] = None
                data = {
                    "error": str(e)
                }
                record["error"] = f"Request failed: {e}"

            # 4. Save to disk
            out_path = os.path.join(self.user_folder, f"{link_id}.json")
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                record["output_file"] = out_path
            except Exception as e:
                record["error"] = f"Write error: {e}"

            results.append(record)

        return results


# Example usage
if __name__ == "__main__":

    example_items =[
        # {
        # "link": "https://www.soreniverson.com/",
        # "reasoning": "Personal website likely contains rich biographical and professional content; use crawl_external_content to fetch full HTML/text for detailed content extraction.",
        # "tool_name": "crawl_external_content",
        # "parameters": {
        #     "endpoint": "?url=https%3A%2F%2Fwww.soreniverson.com%2F&search=Soren%20Iverson&user_id=1"
        #     }
        # },
        # {
        # "link": "https://www.soreniverson.com/",
        # "reasoning": "Personal website main page; use crawl_get_site_links to discover all internal and external relevant links associated with full_name and alias keywords.",
        # "tool_name": "crawl_get_site_links",
        # "parameters": {
        # "endpoint": "?url=https%3A%2F%2Fwww.soreniverson.com%2F&search=www&matrix_user_id=%40ludoa%3Asuperme.etke.host"
        #     }
        # },
        # {
        #     "link": "https://www.youtube.com/",
        #     "reasoning": "Mapping the YouTube homepage for outbound links may help discover Soren Iverson's channel or related content.",
        #     "tool_name": "crawl_get_site_links",
        #     "parameters": {
        #     "endpoint": "?matrix_user_id=@ludoa:superme.etke.host&search=Soren%20Iverson&url=https://www.youtube.com/"
        #     }
        # },
    {
        "link": "https://www.youtube.com/watch?v=EjEpL6CTwLA",
        "reasoning": "YouTube video may help discover Soren Iverson's insights or related content.",
        "tool_name": "crawl_external_content",
        "parameters": {
        "endpoint": "?url=https%3A%2F%2Fwww.youtube.com%2Fwatch?v=EjEpL6CTwLA&search=Soren%20Iverson&user_id=1"
        }
    }
    ]
    # Load instructions from JSON file or stdin

    executor = ToolExecutor(user_id="001")
    summary = executor.execute(example_items)
    print(json.dumps(summary, indent=2))

    # Expected output:
    expected_print_out_output = '''
    [
  {
    "link": "https://www.youtube.com/watch?v=EjEpL6CTwLA",
    "tool": "crawl_external_content",
    "link_id": "1bc90ff4413c4a6bab8768180b084989",
    "status_code": 200,
    "error": null,
    "output_file": "/Agent_Crawler/data/user_data/001/1bc90ff4413c4a6bab8768180b084989.json"
  }
]
'''
    expected_file_saved_output = '''
{
  "status_code": 200,
  "body": {
    "content": "let's look at how to check color contrast in figma first I'll right click and open the start plugin I'll click on contrast first I'll select a layer to check against and as you can see here it fails most contrast ratios if I select the layer on the bottom you'll see that it passes if you're not passing contrast ratios Stark will suggest Alternatives that will pass and you can apply those with the premium version",
    "description": "",
    "favicon": "",
    "metadata": null,
    "published_at": "Sun, 16 Oct 2022 17:38:19 GMT",
    "title": "How to check color contrast with this #figmatutorial",
    "url": "https://www.youtube.com/watch?v=EjEpL6CTwLA"
  }
}
'''
