"""
BaseAgent: provides a common OpenAI‐wrapper that loads system/user prompts
and enforces JSON‐only output. Each derived Agent inherits from this class.
"""

import os
import json
import textwrap
import re
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("Missing OPENAI_API_KEY in environment")

dirname = os.path.dirname(__file__)
# Instantiate the new client
client = OpenAI(api_key=api_key)
_PLACEHOLDER_RE = re.compile(r"\{\{(\w+?)\}\}")   # {{word}}

def render_prompt(template: str, mapping: dict[str, str]) -> str:
    """
    Replace only {{placeholder}} tokens.  All other braces stay intact.
    Unrecognised placeholders are left as-is.
    """
    def _sub(match):
        key = match.group(1)
        return mapping.get(key, match.group(0))   # keep original if missing
    return _PLACEHOLDER_RE.sub(_sub, template)

class BaseAgent:
    """
    Parent class for all LLM agents (query_handler, clarifier, tool_selector, info_extractor …).

    A single ChatCompletion call is built from up to four logical parts:
      1. system prompt  (self.system_prompt rendered with user_profile & history_summary)
      2. conversation history summary (already inside the system prompt to save tokens)
      3. retrieved context (optional)
      4. latest user query
    """
    def __init__(self, agent_name: str, openai_client:  OpenAI = client):
        self.agent_name = agent_name
        self.openai = openai_client

        # load prompt templates
        base_dir = "prompts"
        with open(os.path.join(dirname, "..", base_dir, f"{agent_name}_sys.txt"), encoding="utf-8") as f:
            self._sys_template = f.read().strip()

    # --------------------------------------------------------------------- #
    # Core helper that every concrete agent calls.
    # --------------------------------------------------------------------- #
    def _chat(
        self,
        user_query: str,
        *,
        user_profile: Dict[str, Any] | None = None,
        history_summary: str | None = None,
        retrieved_data: str | Dict[str, Any] | List[Any] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1500,
    ) -> Dict[str, Any]:
        """
        Build and send a ChatCompletion request. Returns the *parsed JSON* that
        the assistant outputs (raise if parsing fails).

        Arguments
        ---------
        user_query        – The user’s latest natural-language request.
        user_profile      – Dict inserted into {{user_profile}}.
        history_summary   – One-paragraph assistant summary of prior turns.
        retrieved_data    – Extra context (string or JSON-able). Put in its own
                            system-level message with name='retrieved_context'.
        """
        # ---- 1) render system prompt template ---- #
        rendered_sys = render_prompt(
            self._sys_template,
            {
                "user_profile": json.dumps(user_profile or {}, ensure_ascii=False),
                "history_summary": history_summary or ""
            }
        )

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": rendered_sys}
        ]

        # ---- 2) optional retrieved context ---- #
        if retrieved_data:
            # stringify in a predictable way to avoid parsing errors downstream
            retrieved_str = (
                retrieved_data
                if isinstance(retrieved_data, str)
                else json.dumps(retrieved_data, ensure_ascii=False, indent=2)
            )
            messages.append({
                "role": "system",
                "name": "retrieved_context",
                "content": retrieved_str
            })

        # ---- 3) latest user query ---- #
        messages.append({"role": "user", "content": user_query})

        # ---- 4) send request ---- #
        resp = self.openai.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

        assistant_msg = resp.choices[0].message.content

        try:
            return json.loads(assistant_msg)
        except json.JSONDecodeError:
            # helpful debug printout
            snippet = textwrap.shorten(assistant_msg, width=300, placeholder=" …")
            raise ValueError(
                f"[{self.agent_name}] assistant returned non-JSON:\n{snippet}"
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
    agent = BaseAgent("query_handler")
    user_query="Find all my social profiles :https://x.com/soren_iverson https://www.soreniverson.com/ https://www.youtube.com/@soren_iverson/videos"
    response = agent._chat(user_profile=example_profile, user_query=user_query, history_summary="")
    print("Response from agent:", json.dumps(response, indent=2))


    # Expected output:
    output = {
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