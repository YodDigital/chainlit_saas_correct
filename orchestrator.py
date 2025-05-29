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

async def validate_auth_with_flask(auth_data):
    """Validate authentication with Flask backend"""
    try:
        flask_base_url = os.getenv('FLASK_BASE_URL')  # Get from env
        if not flask_base_url:
            print("FLASK_BASE_URL not set")
            return None

        validation_url = f"{flask_base_url}/api/validate-auth"
        
        payload = {
            'user_id': auth_data['user_id'],
            'token': auth_data['token']
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(validation_url, json=payload, timeout=10) as response:
                if response.status == 200:
                    user_data = await response.json()
                    return user_data
                else:
                    print(f"Auth validation failed: {response.status} - {await response.text()}")
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
    await cl.Message(content="Requesting cookies...", visible=False).send()
    js_injection = cl.Html(        content="""
        <script>
        (function() {
            try {
                const cookies = document.cookie.split('; ').reduce((acc, cookie) => {
                    const [key, value] = cookie.split('=').map(decodeURIComponent);
                    acc[key] = value;
                    return acc;
                }, {});

                const authDataString = "__COOKIES__" + JSON.stringify(cookies);

                const messageInput = document.querySelector('input[type="text"], textarea');
                if (messageInput) {
                    messageInput.value = authDataString;
                    messageInput.dispatchEvent(new Event('input', { bubbles: true }));
                }
            } catch (error) {
                console.error('Error reading cookies:', error);
            }        })();
        </script>
        """
    )
    await js_injection.send()

        
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
    
    chat_manager = ChatManager(
        db_path=session_data['warehouse_file_path'],  # From session
        llm_config=llm_config,
        work_dir=workspace_dir,  # User-specific workspace
        schema_path=session_data['schema_description']  # From session
    )
    
    cl.user_session.set("chat_manager", chat_manager)
    # cl.user_session.set("user_id", user_id)
    cl.user_session.set("session_data", session_data)

def get_auth_from_cookies():
    """Extract authentication parameters from browser cookies"""
    try:
        # Get cookies from the current session
        cookies = cl.user_session.get('cookies', {})

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

@cl.on_message
async def main(message: cl.Message):
    if message.content.startswith("__COOKIES__"):
        try:            
            cookies = json.loads(message.content[len("__COOKIES__"):])
            cl.user_session.set("cookies", cookies)
            print("Received cookies:", cookies)
            # Now you can call get_auth_from_cookies()
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
            # await cl.make_async(chat_manager.user_agent.initiate_chat)(
            #     chat_manager.manager,
            #     # message=message.content
            #     message=f"{message.content} - User Context: {user_context}"
            # )
            
            # Auto-generate visualization
            # raw_result = await cl.make_async(chat_manager.user_agent.initiate_chat)(
            #     chat_manager.manager,
            #     # message=message.content
            #     message=f"{message.content} - User Context: {user_context}"
            # )
            raw_result = await run_sync(chat_manager.user_agent.initiate_chat, chat_manager.manager, f"{message.content} - User Context: {user_context}")

            # Find and display the final result
            for msg in reversed(chat_manager.group_chat.messages):
                if msg["name"] == "db_agent":
                    # Send raw results first            
                    await cl.Message(content=f"Result: {msg['content']}").send()

                    # Auto-generate visualization                    
                    viz = await run_sync(generate_visualization, msg['content'])
                    
                    if isinstance(viz, str) and viz.startswith("Single result"):
                        await cl.Message(content=viz).send()
                    elif viz:  # It's a base64 image                        
                        await cl.Message(
                            content="",
                            elements=[cl.Image(name="chart", display="inline", content=viz)]
                        ).send()
                    break
        except json.JSONDecodeError as e:
                    print(f"Error decoding cookies: {e}")
    else:        
        await cl.Message(content=f"You said: {message.content}").send()


# if __name__ == "__main__":
    
#     db_path = 'workspace/employee_attrition_data_warehouse.db'

#     # Initialize the chat manager
#     chat_manager = ChatManager(db_path, llm_config, work_dir)

#     # Run the conversation flow
#     result = chat_manager.handle_conversation()

#     # Display the result to the user
#     print("Database query result:", result)

# #I want the number of women who are single and work as reseach scientists