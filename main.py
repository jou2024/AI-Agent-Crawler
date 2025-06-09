#!/usr/bin/env python3
"""
main.py: Entry point for the Intelligent Agent Crawler CLI application.
"""
import os
import sys
import json
from dotenv import load_dotenv
from agents.query_handler import QueryHandlerAgent
from agents.clarifier import ClarifierAgent
from agents.tool_selector import ToolSelectorAgent
from agents.info_retriever import InfoRetrieverAgent
from executor.tool_executor import ToolExecutor

from utils.workspace_ui import WorkspaceDashboard

dirname = os.path.dirname(__file__)
profiles_data_path = os.path.join(dirname, "data/profiles")
all_user_data_path = os.path.join(dirname, "data/user_data")

def print_welcome():
    print("Welcome to the Intelligent Agent Crawler CLI.")
    print("This system helps you discover and extract your public-facing content.")
    print("At any point, type 'END' to exit the application.\n")

def load_user_profile(user_id: str):
    profile_file = f"id_{user_id}.json"
    profile_path = os.path.join(profiles_data_path, profile_file)
    if not os.path.isfile(profile_path):
        print(f"Error: User profile file {profile_path} not found.", file=sys.stderr)
        sys.exit(1)
    with open(profile_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_feedback(feedback: dict, path: str = "feedback_info.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(feedback, f, indent=2, ensure_ascii=False)

def append_knowledge(knowledge: any, path: str = "knowledge_base.json"):
    # Load existing or initialize
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = []
    else:
        data = []
    data.append(knowledge)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def update_workspace_links(workspace_links: dict, items: list, dashboard: WorkspaceDashboard = None):
    """
    Merge or add each link_item into workspace_links by URL;
    ensure an 'add_to_db' flag exists.
    """
    for link_item in items:
        url = link_item.get("link")
        if not url:
            continue
        if url not in workspace_links:
            workspace_links[url] = link_item.copy()
            workspace_links[url].setdefault("add_to_db", False)
        else:
            workspace_links[url].update(link_item)
    if dashboard:
        # Update the dashboard UI with the latest workspace links
        dashboard.update(workspace_links, [])
    return workspace_links


def print_workspace_status(workspace_links: dict):
    items = list(workspace_links.values())
    print("\n" + "=" * 60)
    print("Workspace Links Status:")
    print(json.dumps(items, indent=2))
    total = len(items)
    confirmed = sum(1 for v in items if v.get("is_confirmed") is True)
    added = sum(1 for v in items if v.get("add_to_db") is True)
    print("-" * 60 + "\n")
    print(f"Total links: {total}, Confirmed: {confirmed}, Added to DB: {added}\n")
    print("=" * 60 + "\n")


def main():
    # testing setting
    USER_ID = "001"

    load_dotenv()
    print_welcome()

    # Load user profile
    user_id = USER_ID
    user_profile = load_user_profile(user_id)
    
    user_data_path = os.path.join(all_user_data_path, user_id)
    knowledge_base_path = os.path.join(user_data_path, "knowledge_base.json")

    qh_agent = QueryHandlerAgent()
    clarifier_agent = ClarifierAgent()
    tool_selector_agent = ToolSelectorAgent()

    dashboard = WorkspaceDashboard(ui_dir='ui', port=8000)
    

    # Tool executor for backend calls
    executor = ToolExecutor(user_id=user_id)

    workspace_links: dict = {}

    # Main interaction loop

    ir_output = None
    while True:
        if workspace_links and all(v.get("add_to_db") is True for v in workspace_links.values()):
            print("+" * 60)
            user_input = input("All links are added. Type 'END' to exit or press Enter to continue: ").strip()
        else:
            user_input = input("\nYour query> ").strip()
        
        if user_input.upper() == "END":
            print("Goodbye!")
            break

        # 1. Primary query handling
        qh_output = qh_agent.run(
            user_query=user_input,
            user_profile=user_profile
        )
        
        # Merge any new 'links' from QH
        if qh_output.get("links"):
            workspace_links = update_workspace_links(workspace_links, qh_output["links"], dashboard)
            print_workspace_status(workspace_links)
            # If all links are flagged added, offer to exit
            # test_add_to_db = workspace_links.values()
            # for test in test_add_to_db:
            #         test_instance = test.get("add_to_db")

            if workspace_links and all(v.get("add_to_db") is True for v in workspace_links.values()):
                choice = input("All links are added. Type 'END' to exit or press Enter to continue: ").strip()
                if choice.upper() == "END":
                    print("Goodbye!")
                    break

        # 2. Clarification step
        if qh_output.get("to_clarifier"):
            clar_in = {"to_clarifier": qh_output["to_clarifier"]}
            clar_output = clarifier_agent.run(
                links_payload=clar_in,
                user_profile=user_profile
            )
            if clar_output.get("clarified_links"):
                clarified_links = clar_output["clarified_links"]
                workspace_links = update_workspace_links(workspace_links, clarified_links, dashboard)
                
            print("Clarifier action required:")
            if clar_output.get("to_user") and dashboard:
                dashboard.update(workspace_links, clar_output["to_user"])
                
            print(json.dumps(clar_output, indent=2))
            print_workspace_status(workspace_links)
            continue

        # 3. Tool selection and execution
        if qh_output.get("to_tool_selector"):
            ts_input = {"to_tool_selector": qh_output["to_tool_selector"]}
            ts_output = tool_selector_agent.run(
                to_tool_selector=ts_input,
                user_profile=user_profile
            )
            print("Tool Selector output:")
            ts_output_results = ts_output.get("results", [])
            print(json.dumps(ts_output, indent=2))

            exec_results = executor.execute(ts_output_results)
            print("Tool Executor results:")
            print(json.dumps(exec_results, indent=2))


        # 4. Retrieve external/context data
        info_retriever_agent = InfoRetrieverAgent(user_root=user_data_path)
        for rec in info_retriever_agent.get_retrieved_data():
            ir_output = info_retriever_agent.run(
                workspace_data=workspace_links,
                retrieved_context=rec,
                user_profile=user_profile
            )
            print("Info Retriever output:")
            print(json.dumps(ir_output, indent=2))

            if ir_output.get("to_knowledge_base"):
                knowledge_to_add = ir_output["to_knowledge_base"]
                workspace_links = update_workspace_links(workspace_links, knowledge_to_add, dashboard)
                append_knowledge(knowledge_to_add, knowledge_base_path)
                print("Knowledge base updated.")
                print(knowledge_to_add)
            if ir_output.get("to_clarifier"):
                clar_output = clarifier_agent.run(
                    links_payload={"to_clarifier": ir_output["to_clarifier"]},
                    user_profile=user_profile
                )
                if clar_output.get("clarified_links"):
                    clarified_links = clar_output["clarified_links"]
                    workspace_links = update_workspace_links(workspace_links, clarified_links, dashboard)
                    print_workspace_status(workspace_links)
                print("Clarifier output:")
                print(json.dumps(clar_output, indent=2))
                continue


        # 5. Direct important info to user
        if ir_output.get("to_user"):
            print(ir_output["to_user"])
            if dashboard:
                dashboard.update(workspace_links, ir_output["to_user"])
        if qh_output.get("to_user"):
            print(qh_output["to_user"])
            if dashboard:
                dashboard.update(workspace_links, qh_output["to_user"])
        # 6. Save feedback info if present
        if qh_output.get("feedback_info"):
            save_feedback(qh_output["feedback_info"])
            print("Feedback info saved to feedback_info.json.")

if __name__ == "__main__":
    main()
