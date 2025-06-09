import json
from typing import Dict, Any, List

from .base_agent import BaseAgent  

class ClarifierAgent(BaseAgent):
    """
    LLM agent that receives `{"links": [...]}` from QueryHandler and returns the
    two-key JSON mandated by the clarifier system-prompt.

    Usage
    -----
    clarifier = ClarifierAgent(openai_client)
    result = clarifier.run(to_clarifier_dict)     # result is a parsed dict
    """

    def __init__(self):
        super().__init__(agent_name="clarifier")

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #
    def run(
        self,
        links_payload: Dict[str, Any],
        *,
        user_profile: Dict[str, Any] | None = None,
        history_summary: str | None = None,
    ) -> Dict[str, Any]:
        """
        Parameters
        ----------
        to_clarifier   – dict coming straight from QueryHandler, shape:
                         {"to_clarifier": [{link, platform, is_confirmed}, ...]}

        Returns
        -------
        Parsed JSON from the LLM with the schema specified in the system prompt.
        Raises ValueError if the assistant fails to emit valid JSON.
        """
        # Feed the raw dict to the model as the *entire* user message.
        user_query = json.dumps(links_payload["to_clarifier"], ensure_ascii=False, indent=2)

        # No extra retrieved context for this agent.
        return self._chat(
            user_query=user_query,
            user_profile=user_profile or {},     # optional; can be empty
            history_summary=history_summary,     # optional; usually None here
            retrieved_data=None,
            temperature=0.0,                     
            max_tokens=800,                      # plenty for <20 links
        )

if __name__ == "__main__":
    # Example usage
    example_to_clarifier = {
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
    }
    example_user_profile = {
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
    agent = ClarifierAgent()
    response = agent.run(links_payload=example_to_clarifier, user_profile=example_user_profile, history_summary="")
    print("Response from ClarifierAgent:", json.dumps(response, indent=2))
    # Expected output should match:
    expected_output = {
  "to_user": "Please review each row, toggle Is Confirmed to Yes/No, adjust Add to personal database, and edit any mistakes in link or Platform. Please press Submit when finished.",
  "clarified_links": [
    {
      "link": "https://x.com/soren_iverson",
      "platform": "X",
      "search_info": "Soren Iverson",
      "is_confirmed": False,
      "add_to_db": "Waiting for confirm",
      "agent_notes": "Confirmation needed to verify the accuracy of the link."
    },
    {
      "link": "https://www.soreniverson.com/",
      "platform": "PersonalSite",
      "search_info": "Soren Iverson",
      "is_confirmed": False,
      "add_to_db": "Waiting for confirm",
      "agent_notes": "Confirmation needed to verify the accuracy of the link."
    },
    {
      "link": "https://www.youtube.com/@soren_iverson/videos",
      "platform": "YouTube",
      "search_info": "Soren Iverson",
      "is_confirmed": False,
      "add_to_db": "Waiting for confirm",
      "agent_notes": "Confirmation needed to verify the accuracy of the link."
    }
  ]
}