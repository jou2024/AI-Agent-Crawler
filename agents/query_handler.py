"""
QueryHandlerAgent: parses raw user input + profile + history,
returns JSON with:
  links[{link, platform, is_confirmed}], user_info{}, feedback_info{},
  to_clarifier[], to_tool_selector[].
"""
import json
from typing import List, Dict, Any
from agents.base_agent import BaseAgent

class QueryHandlerAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_name="query_handler")

    def run(
        self,
        *,
        user_query: str,
        user_profile: Dict[str, Any],
        history_summary: str | None = None,
        retrieved_data: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        • user_profile     – latest stored profile for {{user_profile}}
        • history_summary  – one-paragraph recap of prior turns for {{history_summary}}
        • retrieved_data   – optional context passed in if upstream search has run
        """
        return self._chat(
            user_query=user_query,
            user_profile=user_profile,
            history_summary=history_summary,
            retrieved_data=retrieved_data,
            temperature=0.0,
        )

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
    # Example usage
    agent = QueryHandlerAgent()
    example_user_query= "Find all my social profiles :https://x.com/soren_iverson https://www.soreniverson.com/ https://www.youtube.com/@soren_iverson/videos"
    
    example_confirmed_links = '''
[
    {
      "link": "https://x.com/soren_iverson",
      "platform": "X",
      "search_info": "Soren Iverson",
      "is_confirmed": True,
      "add_to_db": "Waiting for confirm",
      "agent_notes": "Confirmation needed to verify the accuracy of the link."
    },
    {
      "link": "https://www.soreniverson.com/",
      "platform": "PersonalSite",
      "search_info": "Soren Iverson",
      "is_confirmed": True,
      "add_to_db": "Waiting for confirm",
      "agent_notes": "Confirmation needed to verify the accuracy of the link."
    },
    {
      "link": "https://www.youtube.com/@soren_iverson/videos",
      "platform": "YouTube",
      "search_info": "Soren Iverson",
      "is_confirmed": True,
      "add_to_db": "Waiting for confirm",
      "agent_notes": "Confirmation needed to verify the accuracy of the link."
    }
'''
    
    # response = agent.run(user_profile=example_profile,user_query=example_user_query, history_summary="")
    response = agent.run(user_profile=example_profile,user_query=example_confirmed_links, history_summary="")
    print("Response from agent:", json.dumps(response, indent=2))
    # Expected output for example_user_query:
    expected_output = {
  "links": [
    {
      "link": "https://x.com/soren_iverson",
      "platform": "X",
      "is_confirmed": False
    },
    {
      "link": "https://www.soreniverson.com/",
      "platform": "PersonalSite",
      "is_confirmed": False
    },
    {
      "link": "https://www.youtube.com/@soren_iverson/videos",
      "platform": "YouTube",
      "is_confirmed": False
    }
  ],
  "user_info": {
    "name": "Soren Iverson",
    "info": "Founder of a full-service design consultancy"
  },
  "feedback_info": {},
  "to_clarifier": [
    {
      "link": "https://x.com/soren_iverson",
      "platform": "X",
      "is_confirmed": False
    },
    {
      "link": "https://www.soreniverson.com/",
      "platform": "PersonalSite",
      "is_confirmed": False
    },
    {
      "link": "https://www.youtube.com/@soren_iverson/videos",
      "platform": "YouTube",
      "is_confirmed": False
    }
  ],
  "to_tool_selector": []
}
    
