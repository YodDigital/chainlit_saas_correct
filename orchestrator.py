from dwh_agents.dwh_code_generator_agent import create_dwh_agent
from dwh_agents.dwh_code_executor_agent import create_executor_agent
from pathlib import Path
import os
import pandas as pd


# # Config
# llm_config = {"model": "gpt-4o-mini", "api_key": os.environ["OPENAI_API_KEY"]}
# work_dir = Path("/workspace").absolute()
# csv_path = work_dir / "WA_Fn-UseC_-HR-Employee-Attrition.csv"

# # Create agents
# generator = create_dwh_agent(llm_config)
# executor = create_executor_agent(work_dir)

# # Message with task and paths


# # Start the loop
# try:
#     df = pd.read_csv(csv_path, nrows=1)
#     column_names = df.columns.tolist()
#     initial_message = f"""
# Analyze the column names extracted from a CSV file and generate a star or snowflake schema-based data warehouse.

# Your steps:
# 1. Design a schema based on thecolumn names {column_names}.
# 2. Write Python code to:
#    - Load the CSV from `{csv_path}`
#    - Transform the data to fit your schema
#    - Load the data into a relational DB (SQLite/PostgreSQL) stored in `{work_dir}/database.db`
#    - Enable OLAP operations (slicing, dicing, roll-up, drill-down)
#    - Save the generated code to `{work_dir}/generated_dwh.py`
# 3. Create a `schema_description.txt` in `{work_dir}` including:
#    - Table and column names
#    - Column roles (dimension/measure)
#    - Data types
#    - Every unique values per column
# 4. Share the code with the execution agent.
# 5. If any execution errors are returned, fix the code and resend it until it executes successfully.

# """
   
# except Exception as e:
#     column_names = []
#     print(f"Error reading CSV: {e}")

# generator.initiate_chat(
#     executor,
#     message=initial_message,
#     request_reply=False
# )


# from chat_agents.analysis_agent import create_analysis_agent
# from chat_agents.user_agent import create_user_agent

# nlp_agent = create_analysis_agent(llm_config, work_dir)
# user_agent = create_user_agent()

# chat_result = user_agent.initiate_chat(
#     nlp_agent,
#     message = "I would like to get the employee with the highest salary in april 2022",
#     request_reply = True,
#     max_turns = 3

# )

# pprint.pprint(chat_result)

from chat_agents.chat_manager import ChatManager
import chainlit as cl
import os

@cl.on_chat_start
async def start_chat():
    llm_config = {
        "model": "gpt-4o-mini",
        "api_key": os.environ["OPENAI_API_KEY"]
    }
    
    chat_manager = ChatManager(
        db_path='/workspace/database.db',
        llm_config=llm_config,
        work_dir="workspace"
    )
    
    cl.user_session.set("chat_manager", chat_manager)

@cl.on_message
async def main(message: cl.Message):
    chat_manager = cl.user_session.get("chat_manager")
    
    # Initiate the conversation
    await cl.make_async(chat_manager.user_agent.initiate_chat)(
        chat_manager.manager,
        message=message.content
    )
    
    # Find and display the final result
    for msg in reversed(chat_manager.group_chat.messages):
        if msg["name"] == "db_agent":
            await cl.Message(content=f"Result: {msg['content']}").send()
            break


# if __name__ == "__main__":
    
#     db_path = 'workspace/employee_attrition_data_warehouse.db'

#     # Initialize the chat manager
#     chat_manager = ChatManager(db_path, llm_config, work_dir)

#     # Run the conversation flow
#     result = chat_manager.handle_conversation()

#     # Display the result to the user
#     print("Database query result:", result)

# #I want the number of women who are single and work as reseach scientists