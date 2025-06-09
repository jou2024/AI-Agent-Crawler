# src/agents/tool_selector_agent.py
import json
from typing import List, Dict, Any
from agents.base_agent import BaseAgent   

class ToolSelectorAgent(BaseAgent):
    """
    Decides which crawler API to call for every confirmed link.

    Usage
    -----
    agent = ToolSelectorAgent()
    result = agent.run(
        to_tool_selector=payload["to_tool_selector"],
        user_profile=profile_dict,
        default_matrix_user_id="@ludoa:superme.etke.host",
        default_user_id=1
    )
    print(result)   # JSON array ready for the executor
    """

    def __init__(self):
        super().__init__(agent_name="tool_selector")

    # ------------------------------------------------------------------ #
    # public entry-point
    # ------------------------------------------------------------------ #
    def run(
        self,
        *,
        to_tool_selector: List[Dict[str, Any]],
        user_profile: Dict[str, Any],
        default_matrix_user_id: str = "@ludoa:superme.etke.host",
        default_user_id: int = 1,
        history_summary: str | None = None
    ) -> List[Dict[str, Any]]:
        """
        Parameters
        ----------
        to_tool_selector  – list from upstream JSON
        user_profile      – dict used to fill {{user_profile}} in the system prompt
        """

        # The LLM sees `user_query` only; provide the payload verbatim.
        user_query = json.dumps(
            { "to_tool_selector": to_tool_selector },
            ensure_ascii=False
        )

        # Stuff we need for placeholders inside the system prompt
        retrieved_context = {
            "default_matrix_user_id": default_matrix_user_id,
            "default_user_id": default_user_id
        }

        # Send to OpenAI – we expect a pure-JSON array back
        response = self._chat(
            user_query=user_query,
            user_profile=user_profile,
            history_summary=history_summary,
            retrieved_data=retrieved_context
        )

        return response


if __name__ == "__main__":
    example_input_to_tool_selector  = [
    # {
    #   "link": "https://x.com/soren_iverson",
    #   "platform": "X",
    #   "search_info": "Soren Iverson",
    #   "is_confirmed": True,
    #   "add_to_db": "Waiting for confirm",
    #   "agent_notes": "Confirmation needed to verify the accuracy of the link."
    # },
    # {
    #   "link": "https://www.soreniverson.com/",
    #   "platform": "PersonalSite",
    #   "search_info": "Soren Iverson",
    #   "is_confirmed": True,
    #   "add_to_db": "Waiting for confirm",
    #   "agent_notes": "Confirmation needed to verify the accuracy of the link."
    # },
    # {
    #   "link": "https://www.youtube.com/@soren_iverson/videos",
    #   "platform": "YouTube",
    #   "search_info": "Soren Iverson",
    #   "is_confirmed": True,
    #   "add_to_db": "Waiting for confirm",
    #   "agent_notes": "Confirmation needed to verify the accuracy of the link."
    # },
    {
      "link": "https://www.youtube.com/",
      "platform": "YouTube",
      "search_info": "Soren Iverson",
      "is_confirmed": True,
      "add_to_db": "Waiting for confirm",
      "agent_notes": "Confirmation needed to verify the accuracy of the link."
    },
    {
      "link": "https://www.youtube.com/",
      "platform": "YouTube",
      "search_info": "Soren Iverson",
      "is_confirmed": True,
      "add_to_db": "Waiting for confirm",
      "agent_notes": "Confirmation needed to verify the accuracy of the link."
    }
  ]

    
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


    agent = ToolSelectorAgent()
    response = agent.run(to_tool_selector=example_input_to_tool_selector, 
                         user_profile=example_user_profile)
    print("Response from ClarifierAgent:", json.dumps(response, indent=2))
    