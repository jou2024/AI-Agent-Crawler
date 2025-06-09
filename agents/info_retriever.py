import os
import json
from typing import List, Dict, Any
from openai import OpenAI

from agents.base_agent import BaseAgent, client
dirname = os.path.dirname(__file__)



class InfoRetrieverAgent(BaseAgent):
    def __init__(
        self,
        user_root: str,
        openai_client: OpenAI = client
    ):
        super().__init__(agent_name="info_retriever", openai_client=openai_client)

        self.user_root = user_root
        self.records: List[Dict[str, Any]] = []

        self.history = ""

        # 1) load the index: link_id → url
        index_path = os.path.join(self.user_root, "link_index.json")
        with open(index_path, encoding="utf-8") as f:
            index: Dict[str, str] = json.load(f)

        # 2) for each link_id, load its JSON and pull out `body`
        for link_id, url in index.items():
            file_path = os.path.join(self.user_root, f"{link_id}.json")
            if not os.path.exists(file_path):
                continue

            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                continue

            body = data.get("body", {})
            if not isinstance(body, dict):
                continue

            # Decide source
            if body.get("links") or body.get("metadata"):
                source = "crawl_get_site_links"
                self.history += f"Loaded with metadata from {body.get("metadata")} .\n"

                # — if every discovered link is already in our index, skip this record —
                links = body.get("links", [])
                if links and all(link in index.values() for link in links):
                    continue

            else:
                source = "crawl_external_content"

            # Build the record
            record: Dict[str, Any] = {
                "link_id":  link_id,
                "url":      url,
                "source":   source,
            }
            # Merge in all the body fields (links+metadata or content+…)
            record.update(body)
            self.records.append(record)


    def get_retrieved_data(self) -> List[Dict[str, Any]]:
        """
        Returns the list of loaded records, each with:
          • link_id, url, source, platform
          • plus everything inside `body`
        """
        return self.records

    def run(
        self,
        *,
        workspace_data = None, 
        retrieved_context: Dict[str, Any],
        user_profile: Dict[str, Any],
        history_summary: str | None = None
    ) -> List[Dict[str, Any]]:
        """
        Parameters
        ----------
        retrieved_context      – dict with the loaded data from self.records
        user_profile      – dict used to fill {{user_profile}} in the system prompt
        """
        if workspace_data and isinstance(workspace_data, Dict):
            workspace_data_str = json.dumps(workspace_data, ensure_ascii=False, indent=2)
            user_query = f"Note that there are some confirmed data {workspace_data_str}. Process the retreived data"
        else:
            user_query = "Process the retrieved data"

        # Send to OpenAI – we expect a pure-JSON array back
        response = self._chat(
            user_query=user_query,
            user_profile=user_profile,
            history_summary=self.history if history_summary is None else history_summary,
            retrieved_data=retrieved_context
        )

        return response


if __name__ == "__main__":

    example_profile = {
                    "id": "001",
                    "full_name": "Soren Iverson",
                    "headline": "Founder of a full-service design consultancy",
                    "location": "Los Angeles, California, United States",
                    "public_contact_info_available": True,
                    "current_position": {
                    "title": "Founder",
                    "organization": "Iverson (design consultancy)"
                    }
                    }
        
    # ——— setup a small “sample_user” folder for testing ———
    sample_user_id = "001"
    sample_root = os.path.join(dirname,"..", "data/test_user_data", sample_user_id)
    os.makedirs(sample_root, exist_ok=True)

    # link_index.json → maps two IDs to test URLs
    sample_index = {
        "test_links": "https://www.youtube.com/watch?v=EjEpL6CTwLA",
        "test_site":  "https://www.soreniverson.com/"
    }
    with open(os.path.join(sample_root, "link_index.json"), "w") as f:
        json.dump(sample_index, f, indent=2)

    # test_links.json — simulating crawl_get_site_links
    test1 = {
        "status_code": 200,
        "body": {
            "links": [
                "https://www.youtube.com/watch?v=EjEpL6CTwLA",
                "https://www.youtube.com/watch?v=NBojibnQbPo",
                "https://www.youtube.com/watch?v=RIOb2oUFZNk",
                "https://www.youtube.com/watch?v=WSHGY-TMpW0"
            ],
            "metadata": {
                "https://www.youtube.com/watch?v=EjEpL6CTwLA": {
                    "channel": "Soren Iverson",
                    "description": "",
                    "title": "How to check color contrast with this #figmatutorial"
                },
                "https://www.youtube.com/watch?v=NBojibnQbPo": {
                    "channel": "Soren Iverson",
                    "description": "",
                    "title": "How to create a type system using #materialdesign #shortvideo"
                },
                "https://www.youtube.com/watch?v=RIOb2oUFZNk": {
                    "channel": "Greg Isenberg",
                    "description": "I'm joined by Soren Iverson, Engineer at Apple . We talk about building ...",
                    "title": "He Shares The Engineer Behind Viral Products"
                }
            },
            "status": "success"
        }
    }
    with open(os.path.join(sample_root, "test_links.json"), "w") as f:
        json.dump(test1, f, indent=2)

    # test_site.json — simulating crawl_external_content
    test2 = {
        "body": {
            "content": (
                "Projects\nA few products I designed\nAbout\nWho I am\n"
                "Hi there, my name's Soren. I'm the founder of Iverson…"
            ),
            "description": "Designer based in Costa Mesa, CA",
            "error": "",
            "favicon": "https://framerusercontent.com/images/…",
            "language": "en",
            "source_url": "https://www.soreniverson.com/",
            "status_code": 200,
            "title": "Soren Iverson",
            "url": "https://www.soreniverson.com/",
            "warning": None
        }
    }
    with open(os.path.join(sample_root, "test_site.json"), "w") as f:
        json.dump(test2, f, indent=2)

    # ——— instantiate and verify that we loaded two records ———
    agent = InfoRetrieverAgent(user_root=sample_root)
    for rec in agent.get_retrieved_data():
        print("----------input record start----------")
        print(json.dumps(rec, indent=2))
        print("-----------input record end-----------")

        response = agent.run(
            retrieved_context=rec,
            user_profile=example_profile,
            history_summary=None
        )
        print("----------output record start----------")
        print(json.dumps(response, indent=2))
        print("-----------output record end-----------")
        print("\n\n")

     # Expected output be like:
    expected_output_1 = '''
{
  "thinking_process": "The source is crawl_get_site_links, so I must evaluate each child link using its metadata. Two links are from a channel named 'Soren Iverson', which matches the user's name, but the user is a design founder, not an engineer. One link is from 'Greg Isenberg' and mentions Soren Iverson as an engineer at Apple, which does not match the user's current role. All links require user confirmation.",
  "to_knowledge_base": [],
  "to_clarifier": [
    {
      "link": "https://www.youtube.com/watch?v=EjEpL6CTwLA",
      "platform": "youtube",
      "confidence": 4,
      "is_confirmed": false,
      "add_to_db": "waiting_for_confirm",
      "agent_notes": "Channel name matches user, but need user to confirm ownership of this YouTube channel."
    },
    {
      "link": "https://www.youtube.com/watch?v=NBojibnQbPo",
      "platform": "youtube",
      "confidence": 4,
      "is_confirmed": false,
      "add_to_db": "waiting_for_confirm",
      "agent_notes": "Channel name matches user, but confirmation needed to ensure this is the user's content."
    },
    {
      "link": "https://www.youtube.com/watch?v=RIOb2oUFZNk",
      "platform": "youtube",
      "confidence": 2,
      "is_confirmed": false,
      "add_to_db": "waiting_for_confirm",
      "agent_notes": "Mentions Soren Iverson as an engineer at Apple, which does not match user's current role. Needs user clarification."
    },
    {
      "link": "https://www.youtube.com/watch?v=WSHGY-TMpW0",
      "platform": "youtube",
      "confidence": 1,
      "is_confirmed": false,
      "add_to_db": "waiting_for_confirm",
      "agent_notes": "No metadata available to confirm identity. Needs user review."
    }
  ]
}'''
    expected_output_2 = '''
{
  "thinking_process": "The page title is 'Soren Iverson', matching the user's name. The About section says 'Hi there, my name's Soren. I'm the founder of Iverson\u2026', which matches the user's consultancy and founder role. The location (Costa Mesa, CA) is near Los Angeles, CA. All identity signals strongly match the user.",
  "to_knowledge_base": [
    {
      "link": "https://www.soreniverson.com/",
      "platform": "website",
      "confidence": 5,
      "is_confirmed": true,
      "add_to_db": true,
      "agent_notes": "Title, About section, and founder role all match user. Location is consistent. This is certainly the user's site."
    }
  ],
  "to_clarifier": []
}
'''
