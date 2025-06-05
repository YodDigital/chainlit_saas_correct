import json
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
import aiohttp
import aiofiles
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor()  # Create a ThreadPoolExecutor instance


def generate_visualization(query_result):
    """Auto-generate visualization based on query results."""
    try:
        if query_result is None:
            return None

        # Check if result is tabular data (assumes it's convertible to DataFrame)
        if isinstance(query_result, str):
            # Try to parse string as table (common SQL result format)
            if "|" in query_result:  # Chainlit's default table format
                lines = [line.split("|") for line in query_result.split("\n") if line.strip()]
                if len(lines) > 2:  # Header + separator + at least one row
                    try:
                        df = pd.DataFrame([lines[i] for i in range(2, len(lines))], columns=lines[0])                        
                        df = df.apply(lambda x: x.str.strip())
                    except Exception as e:
                        print(f"Error creating DataFrame: {e}")
                        return None
                else:
                    return None  # Not visualizable data
            else:
                return None  # Not visualizable data
        else:
            try:
                df = pd.DataFrame(query_result)
            except Exception as e:
                print(f"Error creating DataFrame: {e}")
                return None
        
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
            
        else:
            print("Dataframe has more than 2 columns, cannot visualize")
            return None

    except Exception as e:
        print(f"Visualization error: {str(e)}")
        return None

def run_sync(func, *args, **kwargs):
    """Run a synchronous function in the event loop."""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(executor, lambda: func(*args, **kwargs))

async def fetch_user_session(user_id, token):
    if not user_id or not token:
        await cl.Message(content="User ID or token is missing.").send()
        return None

    flask_base_url = os.getenv('FLASK_BASE_URL')
    if not flask_base_url:
        await cl.Message(content="FLASK_BASE_URL environment variable not set.").send()
        return None

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{flask_base_url}/api/user_session/{user_id}") as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    await cl.Message(content=f"Failed to fetch user session. Status: {resp.status}").send()
                    return None
    except Exception as e:
        await cl.Message(content=f"An error occurred: {e}").send()
        return None
def parse_cookie_string(cookie_string):
    """Parse cookie string into a dictionary"""
    try:
        cookies = {}
        # Handle different cookie formats
        if cookie_string.startswith('{') and cookie_string.endswith('}'):
            # JSON format: {"auth_user_id": "123", "auth_token": "abc"}
            cookies = json.loads(cookie_string)
        else:
            # String format: "auth_user_id=123; auth_token=abc; username=john"
            for cookie in cookie_string.split(';'):
                if '=' in cookie:
                    key, value = cookie.strip().split('=', 1)
                    cookies[key.strip()] = value.strip()
        
        return cookies
    except Exception as e:
        print(f"Error parsing cookie string: {e}")
        return {}

def get_auth_from_cookies(cookies_dict):
    """Extract authentication parameters from cookies dictionary"""
    try:
        auth_data = {
            'user_id': cookies_dict.get('auth_user_id'),
            'token': cookies_dict.get('auth_token'),
            'flask_base_url': cookies_dict.get('flask_base_url'),
            'username': cookies_dict.get('username'),
            'auth_timestamp': cookies_dict.get('auth_timestamp')
        }

        # Validate that all required fields are present
        required_fields = ['user_id', 'token', 'flask_base_url', 'username']
        missing_fields = [field for field in required_fields if not auth_data.get(field)]
        
        if missing_fields:
            print(f"Missing required fields: {missing_fields}")
            return None

        return auth_data
    except Exception as e:
        print(f"Error extracting auth from cookies: {e}")
        return None

async def load_schema_from_url(schema_url, local_path):
    """Download schema file from URL to local path"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(schema_url) as response:
                if response.status == 200:
                    content = await response.text()
                    # Save to local file
                    async with aiofiles.open(local_path, 'w', encoding='utf-8') as f:
                        await f.write(content)
                    return local_path
                else:
                    print(f"Failed to download schema: {response.status}")
                    return None
    except Exception as e:
        print(f"Error downloading schema: {e}")
        return None

async def load_user_data(user_id, token):

    # Fetch user session data from Flask backend
    session_data = await fetch_user_session(user_id, token)
    
    if not session_data:
        await cl.Message(content="Failed to load your data warehouse configuration").send()
        return

    llm_config = {
        "model": "gpt-4o-mini",
        "api_key": os.getenv("OPENAI_API_KEY")
    }
    
    # chat_manager = ChatManager(
    #     db_path='/workspace/database.db',
    #     llm_config=llm_config,
    #     work_dir="workspace"
    # )
    # Ensure workspace directory exists
    workspace_dir = f"workspace/user_{user_id}"
    os.makedirs(workspace_dir, exist_ok=True)
    
    os.environ["AUTOGEN_USE_DOCKER"] = "False"

    # cl.user_session.set("user_id", user_id)
    cl.user_session.set("session_data", session_data)

    local_schema_path = os.path.join(workspace_dir, 'schema.txt')
    schema_path = await load_schema_from_url(cl.user_session.get("session_data", {}).get('schema_description', ''), local_schema_path)

    chat_manager = ChatManager(
        db_path=cl.user_session.get("session_data", {}).get('warehouse_file_path', '').rstrip("'%7D"),  # From session
        llm_config=llm_config,
        work_dir=workspace_dir,  # User-specific workspace
        schema_path=schema_path  # From session
    )
    
    cl.user_session.set("chat_manager", chat_manager)
    # # cl.user_session.set("user_id", user_id)
    # cl.user_session.set("session_data", session_data)

@cl.on_chat_start
async def start():
    """Initialize chat and prompt for authentication"""
    # Check if user is already authenticated
    if cl.user_session.get("authenticated"):
        await cl.Message(
            content=f"✅ Welcome back, {cl.user_session.get('username')}! You can now ask questions about your data warehouse.",
            author="System"
        ).send()
        return
    
    # Prompt for cookie authentication
    await cl.Message(
        content="""🔐 **Authentication Required**
        
Please provide your authentication cookies in one of these formats:

**Format 1 (JSON):**
```
{"auth_user_id": "123", "auth_token": "your-token", "flask_base_url": "https://your-app.com", "username": "your-username"}
```

**Format 2 (Cookie String):**
```
auth_user_id=123; auth_token=your-token; flask_base_url=https://your-app.com; username=your-username
```

Please paste your authentication cookies below:""",
        author="System"
    ).send()
    
    # Set flag to indicate we're waiting for authentication
    cl.user_session.set("awaiting_auth", True)

@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages"""
    
    # Check if we're waiting for authentication
    if cl.user_session.get("awaiting_auth"):
        await handle_authentication(message.content)
        return
    
    # Check if user is authenticated
    if not cl.user_session.get("authenticated"):
        await cl.Message(
            content="❌ Please authenticate first by providing your cookies.",
            author="System"
        ).send()
        return
    
    # Handle normal chat messages
    await handle_chat_message(message.content)

async def handle_authentication(cookie_input):
    """Handle the authentication process"""
    try:
        # Parse the cookie input
        cookies_dict = parse_cookie_string(cookie_input.strip())
        
        if not cookies_dict:
            await cl.Message(
                content="❌ Invalid cookie format. Please check your input and try again.",
                author="System"
            ).send()
            return
        
        # Extract authentication data
        auth_data = get_auth_from_cookies(cookies_dict)
        
        if not auth_data:
            await cl.Message(
                content="❌ Missing required authentication fields. Please ensure you have: auth_user_id, auth_token, flask_base_url, username",
                author="System"
            ).send()
            return
        
        await cl.Message(content="🔄 Validating authentication...", author="System").send()
        
        # Validate authentication with Flask backend
        await load_user_data(auth_data['user_id'], auth_data['token'])
                
        # Store authentication info in session
        cl.user_session.set("authenticated", True)
        cl.user_session.set("awaiting_auth", False)
        cl.user_session.set("user_id", auth_data['user_id'])
        cl.user_session.set("username", auth_data['username'])
        cl.user_session.set("flask_base_url", auth_data['flask_base_url'])
        
        await cl.Message(
            content=f"✅ **Authentication Successful!**\n\nWelcome, {auth_data['username']}! Your data warehouse is now loaded and ready.\n\n💬 You can now ask questions about your data. Try something like:\n- 'Show me the top 10 customers by revenue'\n- 'What was the total sales last month?'\n- 'How many employees are in each department?'",
            author="System"
        ).send()
        
    except Exception as e:
        print(f"Authentication error: {e}")
        await cl.Message(
            content=f"❌ Authentication error: {str(e)}",
            author="System"
        ).send()

async def handle_chat_message(user_message):
    """Handle normal chat messages after authentication"""
    try:
        chat_manager = cl.user_session.get("chat_manager")
        if not chat_manager:
            await cl.Message(content="❌ Session not initialized. Please restart and authenticate again.", author="System").send()
            return
        
        # Get user context
        user_context = {
            "user_id": cl.user_session.get("user_id"),
            "schema_info": cl.user_session.get("session_data", {}).get('schema_description', ''),
            "warehouse_info": cl.user_session.get("session_data", {}).get('warehouse_file_path', '')
        }
        
        await cl.Message(content="🔄 Processing your query...", author="System").send()
        
        # Process the message with the chat manager
        await cl.make_async(chat_manager.user_agent.initiate_chat)(
        chat_manager.manager,
        # message=message.content
        message=f"{user_message} - User Context: {user_context}"
    )

        # Find and display the final result
        result_found = False
        for msg in reversed(chat_manager.group_chat.messages):
            if msg["name"] == "db_agent":
                # Send raw results first
                await cl.Message(content=f"📊 **Result:**\n{msg['content']}", author="Database").send()

                # Auto-generate visualization
                viz = await run_sync(generate_visualization, msg['content'])
                
                if isinstance(viz, str) and viz.startswith("Single result"):
                    await cl.Message(content=f"📈 {viz}", author="Visualization").send()
                elif viz:  # It's a base64 image
                    await cl.Message(
                        content="📊 **Chart:**",
                        elements=[cl.Image(name="chart", display="inline", content=viz)],
                        author="Visualization"
                    ).send()
                
                result_found = True
                break
        
        if not result_found:
            await cl.Message(content="⚠️ No database results found. Please try rephrasing your question.", author="System").send()
            
    except Exception as e:
        print(f"Chat message error: {e}")
        await cl.Message(
            content=f"❌ Error processing your message: {str(e)}",
            author="System"
        ).send()

# if __name__ == "__main__":
    
#     db_path = 'workspace/employee_attrition_data_warehouse.db'

#     # Initialize the chat manager
#     chat_manager = ChatManager(db_path, llm_config, work_dir)

#     # Run the conversation flow
#     result = chat_manager.handle_conversation()

#     # Display the result to the user
#     print("Database query result:", result)

# #I want the number of women who are single and work as reseach scientists
#i want the highest monthly income per jobrole for employees having worked for over 10 years in the company

# {
# "auth_token":"1-RDfTlwN3HNOXtzK3zj4eMg",  "auth_user_id":"1", "flask_base_url":"https://skaibknd-production.up.railway.app/", "username":"raphy_01", "auth_timestamp":"1749117523"
# }