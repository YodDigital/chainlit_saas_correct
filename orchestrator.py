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
import json

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


# JavaScript code to read localStorage (this would be injected into the Chainlit page)
LOCALSTORAGE_READER_JS = """
function getChainlitAuthData() {
    try {
        const authData = {
            user_id: localStorage.getItem('chainlit_user_id'),
            auth_token: localStorage.getItem('chainlit_auth_token'),
            flask_base_url: localStorage.getItem('chainlit_flask_base_url'),
            username: localStorage.getItem('chainlit_username'),
            auth_timestamp: localStorage.getItem('chainlit_auth_timestamp'),
            warehouse_file_path: localStorage.getItem('chainlit_warehouse_file_path'),
            schema_description: localStorage.getItem('chainlit_schema_description'),
            auth_expiry: localStorage.getItem('chainlit_auth_expiry')
        };
        
        // Check if essential fields exist
        const requiredFields = ['user_id', 'auth_token', 'flask_base_url', 'username'];
        const hasAllFields = requiredFields.every(field => authData[field]);
        
        if (!hasAllFields) {
            console.log('Missing required auth fields in localStorage');
            return null;
        }
        
        // Check expiry
        if (authData.auth_expiry) {
            const expiryTime = parseInt(authData.auth_expiry);
            if (Date.now() > expiryTime) {
                console.log('Auth data has expired');
                // Clear expired data
                clearChainlitAuthData();
                return null;
            }
        }
        
        return authData;
        
    } catch (error) {
        console.error('Error reading localStorage auth data:', error);
        return null;
    }
}

function clearChainlitAuthData() {
    const keysToRemove = [
        'chainlit_user_id',
        'chainlit_auth_token',
        'chainlit_flask_base_url',
        'chainlit_username',
        'chainlit_auth_timestamp',
        'chainlit_warehouse_file_path',
        'chainlit_schema_description',
        'chainlit_auth_expiry'
    ];
    
    keysToRemove.forEach(key => {
        localStorage.removeItem(key);
    });
}

// Make auth data available globally
window.chainlitAuthData = getChainlitAuthData();
"""

def get_auth_from_frontend():
    """
    Get authentication data from the frontend localStorage
    This is a placeholder - you'll need to implement the actual method
    to get data from the frontend based on Chainlit's capabilities
    """
    # In a real implementation, you would need to:
    # 1. Inject the JavaScript code above into the page
    # 2. Execute it to get the auth data
    # 3. Return the result
    
    # For now, this is a conceptual placeholder
    # You might need to use Chainlit's JavaScript execution capabilities
    # or have the frontend send this data via a message
    
    return None


async def validate_auth_with_flask(auth_data):
    """Validate authentication with Flask backend using localStorage data"""
    try:
        flask_base_url = auth_data['flask_base_url']
        validation_url = f"{flask_base_url}api/validate-localstorage-auth"
        
        # Send all auth data for validation
        response = requests.post(validation_url, json=auth_data, timeout=10)
        
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
    """Initialize chat session with localStorage authentication"""
    
    # First, try to get auth data from localStorage
    # NOTE: You'll need to implement the actual localStorage reading method
    # This might involve sending a message to the frontend or using Chainlit's JS capabilities
    
    await cl.Message(
        content="🔄 Checking authentication...",
        author="System"
    ).send()
    
    # Try to get auth data (this is where you'd implement localStorage reading)
    auth_data = await get_localStorage_auth_data()
    
    if not auth_data:
        await cl.Message(
            content="❌ Authentication failed. Please log in through the main application first.",
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
    
    # Store user data in session
    cl.user_session.set("user_id", auth_data['user_id'])
    cl.user_session.set("username", auth_data['username'])
    cl.user_session.set("flask_base_url", auth_data['flask_base_url'])
    cl.user_session.set("warehouse_file_path", auth_data.get('warehouse_file_path'))
    cl.user_session.set("schema_description", auth_data.get('schema_description'))
    cl.user_session.set("user_data", user_data)
    
    # Send welcome message
    welcome_msg = f"👋 Welcome back, {auth_data['username']}! \n\nI'm ready to help you analyze your data warehouse. What would you like to explore?"

    await cl.Message(
        content=welcome_msg,
        author="Assistant"
    ).send()
    

async def get_localStorage_auth_data():
    """
    Implementation that asks the frontend to auto-send localStorage data
    via a specially formatted message
    """
    
    # Send JavaScript that auto-executes and sends auth data
    js_injection = cl.Html(
        content="""
        <script>
        (function() {
            try {
                const authData = {
                    user_id: localStorage.getItem('chainlit_user_id'),
                    auth_token: localStorage.getItem('chainlit_auth_token'),
                    flask_base_url: localStorage.getItem('chainlit_flask_base_url'),
                    username: localStorage.getItem('chainlit_username'),
                    auth_timestamp: localStorage.getItem('chainlit_auth_timestamp'),
                    warehouse_file_path: localStorage.getItem('chainlit_warehouse_file_path'),
                    schema_description: localStorage.getItem('chainlit_schema_description'),
                    auth_expiry: localStorage.getItem('chainlit_auth_expiry')
                };
                
                // Check if we have the required data
                if (authData.user_id && authData.auth_token) {
                    // Check expiry
                    if (authData.auth_expiry && Date.now() > parseInt(authData.auth_expiry)) {
                        console.log('Auth expired, clearing data');
                        Object.keys(authData).forEach(key => {
                            localStorage.removeItem('chainlit_' + key);
                        });
                        return;
                    }
                    
                    // Send auth data as a hidden message
                    const event = new CustomEvent('chainlit-auth-data', {
                        detail: authData
                    });
                    window.dispatchEvent(event);
                    
                    // Alternative: Try to send via input if available
                    const messageInput = document.querySelector('input[type="text"], textarea');
                    if (messageInput) {
                        // Temporarily store auth data for retrieval
                        window._chainlitAuthData = authData;
                    }
                }
            } catch (error) {
                console.error('Error reading localStorage:', error);
            }
        })();
        </script>
        <div style="display: none;">Authentication check in progress...</div>
        """,
        display="inline"
    )
    
    await js_injection.send()
    
    # Wait a moment for the JavaScript to execute
    await asyncio.sleep(2)
    
    # Check if auth data was stored globally (this might not work in Chainlit's sandbox)
    # This is a placeholder - actual implementation depends on Chainlit's JS capabilities
    return None

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