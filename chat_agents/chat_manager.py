from autogen import GroupChat, GroupChatManager
from chat_agents.analysis_agent import create_analysis_agent
from chat_agents.database_query_agent import create_database_query_agent, query_database
from chat_agents.request_formulation_agent import create_formulation_agent
from chat_agents.user_agent import create_user_agent

class ChatManager:
    def __init__(self, db_path, llm_config, work_dir, schema_path):
        self.db_path = db_path
        self.llm_config = llm_config
        self.work_dir = work_dir
        self.schema_path = schema_path

        # Initialize agents with clear system messages
        self.user_agent = create_user_agent()
        self.analysis_agent = create_analysis_agent(llm_config, work_dir)
        self.formulation_agent = create_formulation_agent(llm_config, work_dir, schema_path)
        self.db_agent = create_database_query_agent(db_path, llm_config)

        # Set up GroupChat (automatic mode)
        self.group_chat = GroupChat(
            agents=[
                self.user_agent,
                self.analysis_agent,
                self.formulation_agent,
                self.db_agent,
            ],
            messages=[],
            # max_round=20,
            # No speaker_selection_method → defaults to automatic
        )

        # Initialize manager with LLM config
        self.manager = GroupChatManager(
            groupchat=self.group_chat,
            llm_config=llm_config,
        )

    # def handle_conversation(self):
    #     """Runs the conversation automatically."""
    #     # Start chat with the user agent
    #     self.manager.initiate_chat(
    #         self.user_agent,
    #         message="Please enter your request:",
    #     )

    #     # Extract the final result (e.g., database response)
    #     for msg in reversed(self.group_chat.messages):
    #         if msg["role"] == "db_agent" and "result" in msg["content"]:
    #             return msg["content"]
        
    #     return "No result found."