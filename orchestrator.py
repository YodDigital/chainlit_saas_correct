from urllib.parse import parse_qs
import aiohttp
from dwh_agents.dwh_code_generator_agent import create_dwh_agent
from dwh_agents.dwh_code_executor_agent import create_executor_agent
from pathlib import Path
import os
import requests
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
import matplotlib.pyplot as plt
import io
import base64
from typing import Optional
import asyncio
import aiohttp  # Import aiohttp

def generate_visualization(query_result):
    """Auto-generate visualization based on query results."""
    try:
        # Check if result is tabular data (assumes it's convertible to DataFrame)
        if isinstance(query_result, str):
            # Try to parse string as table (common SQL result format)
            if "|" in query_result:  # Chainlit's default table format
                lines = [line.split("|") for line in query_result.split("\n") if line.strip()]
                if len(lines) > 2:  # Header + separator + at least one row
                    df = pd.DataFrame(lines[2:], columns=lines[0])
                    df = df.apply(lambda x: x.str.strip())
            else:
                return None  # Not visualizable data
        else:
            df = pd.DataFrame(query_result)
        
        # Clean dataframe
        df = df.dropna(how='all').reset_index(drop=True)
        
        # Single value case
        if len(df) == 1 and len(df.columns) == 1:
            return f"Single result: {df.iloc[0,0]}"
        
        # Auto-determine chart type
        if len(df.columns) == 2:
            x_col, y_col = df.columns[0], df.columns[1]
            
            # Generate plot
            plt.figure(figsize=(10, 4))
            if pd.api.types.is_numeric_dtype(df[y_col]):
                if pd.api.types.is_datetime64_any_dtype(df[x_col]):
                    plt.plot(df[x_col], df[y_col])  # Time series
                else:
                    plt.bar(df[x_col], df[y_col])  # Bar chart
            else:
                plt.pie(df[y_col].value_counts(), labels=df[x_col])  # Pie chart
            
            plt.title(f"{y_col} by {x_col}")
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Convert to base64 for Chainlit
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            plt.close()
            return base64.b64encode(buf.getvalue()).decode('utf-8')
            
    except Exception as e:
        print(f"Visualization error: {str(e)}")
        return None

# async def get_authenticated_user():
#     params = cl.user_session.get("query_params")
#     return params.get("user_id"), params.get("token"), params.get("flask_base_url"), params.get("username")


@cl.on_window_message
async def handle_url_params(message: dict):
    """Handle messages from the frontend JavaScript"""
    try:
        if message.get("type") == "url_params":
            url_params = message.get("params", {})

            # Parameter Validation (Example)
            user_id = url_params.get("user_id")
            if user_id and not isinstance(user_id, str):
                await cl.Message(
                    content="❌ Invalid URL parameters: user_id must be a string",
                    author="System",
                ).send()
                return

            # Store in user session
            cl.user_session.set("url_params", url_params)

            # Log the parameters
            print(f"URL parameters received: {url_params}")

            # Optional: Send confirmation message to chat
            await cl.Message(
                content="✅ URL parameters loaded successfully",
                author="System"
            ).send()

            # You can now access these params in other functions:
            # params = cl.user_session.get("url_params")

    except Exception as e:
        print(f"Error handling URL parameters: {e}")
        await cl.Message(
            content="❌ Error processing URL parameters",
            author="System"
        ).send()

def get_auth_from_cookies():
    """Extract authentication parameters from browser cookies"""
    try:
        # Get cookies from the current session
        # Note: This depends on how Chainlit exposes cookies - you might need to use JavaScript
        cookies = cl.context.session.get('cookies', {})
        
        auth_data = {
            'user_id': cookies.get('auth_user_id'),
            'token': cookies.get('auth_token'),
            'flask_base_url': cookies.get('flask_base_url'),
            'username': cookies.get('username'),
            'auth_timestamp': cookies.get('auth_timestamp')
        }
        
        # Validate that all required fields are present
        required_fields = ['user_id', 'token', 'flask_base_url', 'username']
        if not all(auth_data.get(field) for field in required_fields):
            return None
            
        return auth_data
    except Exception as e:
        print(f"Error reading cookies: {e}")
        return None

async def validate_auth_with_flask(auth_data):
    """Validate authentication with Flask backend"""
    try:
        flask_base_url = auth_data['flask_base_url']
        validation_url = f"{flask_base_url}api/validate-auth"
        
        payload = {
            'user_id': auth_data['user_id'],
            'token': auth_data['token']
        }
        
        response = requests.post(validation_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            user_data = response.json()
            return user_data
        else:
            print(f"Auth validation failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error validating auth: {e}")
        return None

async def fetch_user_session(user_id, token):
    if not user_id or not token:
        print("User ID or token is missing.")
        return None

    flask_base_url = os.getenv('FLASK_BASE_URL')
    if not flask_base_url:
        print("FLASK_BASE_URL environment variable not set.")
        return None

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{flask_base_url}/api/user_session/{user_id}", headers={"Authorization": f"Bearer {token}"}) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    print(f"Failed to fetch user session. Status: {resp.status}")
                    return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

@cl.on_chat_start
async def start_chat():
    """Initialize chat session with authentication"""
    
    # Get authentication data from cookies
    auth_data = get_auth_from_cookies()
    
    if not auth_data:
        await cl.Message(
            content="❌ Authentication failed. Please log in through the main application.",
            author="System"
        ).send()
        return
    
    # Validate authentication with Flask backend
    user_data = await validate_auth_with_flask(auth_data)
    
    if not user_data:
        await cl.Message(
            content="❌ Authentication validation failed. Please log in again.",
            author="System"
        ).send()
        return
    
    await load_user_data(auth_data['user_id'], auth_data['token'])
   # Store user data in session
    cl.user_session.set("user_id", auth_data['user_id'])
    cl.user_session.set("username", auth_data['username'])
    cl.user_session.set("flask_base_url", auth_data['flask_base_url'])
    cl.user_session.set("user_data", user_data)
    
        
async def load_user_data(user_id, token):

    # Fetch user session data from Flask backend
    session_data = await fetch_user_session(user_id, token)
    
    if not session_data:
        await cl.Message(content="Failed to load your data warehouse configuration").send()
        return

    llm_config = {
        "model": "gpt-4o-mini",
        "api_key": os.environ["OPENAI_API_KEY"]
    }
    
    # chat_manager = ChatManager(
    #     db_path='/workspace/database.db',
    #     llm_config=llm_config,
    #     work_dir="workspace"
    # )
    # Ensure workspace directory exists
    workspace_dir = f"workspace/user_{user_id}"
    os.makedirs(workspace_dir, exist_ok=True)
    
    chat_manager = ChatManager(
        db_path=session_data['warehouse_file_path'],  # From session
        llm_config=llm_config,
        work_dir=workspace_dir,  # User-specific workspace
        schema_path=session_data['schema_description']  # From session
    )
    
    cl.user_session.set("chat_manager", chat_manager)
    # cl.user_session.set("user_id", user_id)
    cl.user_session.set("session_data", session_data)



@cl.on_message
async def main(message: cl.Message):
    chat_manager = cl.user_session.get("chat_manager")
    if not chat_manager:
        await cl.Message(content="Session not initialized").send()
        return
        
    # Get additional context from session
    user_context = {
        "user_id": cl.user_session.get("user_id"),
        "schema_info": cl.user_session.get("session_data")['schema_description']
    }

    # Initiate the conversation
    await cl.make_async(chat_manager.user_agent.initiate_chat)(
        chat_manager.manager,
        # message=message.content
        message=f"{message.content} - User Context: {user_context}"
    )
    
    # Find and display the final result
    for msg in reversed(chat_manager.group_chat.messages):
        if msg["name"] == "db_agent":
            # Send raw results first            await cl.Message(content=f"Result: {msg['content']}").send()

            # Auto-generate visualization
            viz = generate_visualization(msg['content'])
            
            if isinstance(viz, str) and viz.startswith("Single result"):
                await cl.Message(content=viz).send()
            elif viz:  # It's a base64 image
                await cl.Message(
                    content="",
                    elements=[cl.Image(name="chart", display="inline", content=viz)]
                ).send()
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