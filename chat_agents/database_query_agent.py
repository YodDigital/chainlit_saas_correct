import sqlite3
from autogen import AssistantAgent
from .chainlit_agents import ChainlitAssistantAgent
import re


def create_database_query_agent(db_path, llm_config):
    # Create a function that will actually execute database queries
    def execute_query(query):
        try:
            connection = sqlite3.connect(db_path)
            cursor = connection.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            
            # Get column names from cursor description
            if cursor.description:
                column_names = [col[0] for col in cursor.description]
            else:
                column_names = []
                
            connection.close()
            
            # Format the results in a readable way
            if not results:
                return "Query executed successfully. No results returned."
            
            # Build a formatted table for results
            formatted_results = []
            formatted_results.append("| " + " | ".join(column_names) + " |")
            formatted_results.append("| " + " | ".join(["---" for _ in column_names]) + " |")
            
            for row in results:
                formatted_results.append("| " + " | ".join([str(item) for item in row]) + " |")
                
            return "\n".join(formatted_results)
            
        except Exception as e:
            return f"ERROR: {str(e)}"
    
    prompt = """You are a database query agent with these responsibilities:
    
    1. When you receive 'PROCEED_TO_DATABASE: [SQL_QUERY]':
       - First VALIDATE the SQL syntax and semantics
       - If valid, execute it and return the actual query results, not a placeholder
       - If invalid, return: 'ROUTE_TO_FORMULATION_AGENT: [specific_problems]' 
       Example error response:
            ROUTE_TO_FORMULATION_AGENT:
            The query failed because:
            - Table 'sales_region' does not exist. Available tables: dim_geography, fact_sales
            - Column 'region_name' not found. Available columns in dim_geography: geography_key, region_id, region_desc
            Suggested fix: Use 'fact_sales' joined with 'dim_geography' on geography_key
    
    2. For invalid queries, specify exactly what's wrong:
       - Syntax errors
       - Missing tables/columns (reference schema if needed)
       - Logical inconsistencies
       - Suggestions for correction
    
    3. Always maintain SQL best practices (parameterization, etc.)
    
    IMPORTANT: When a query is valid, DO NOT just respond with "RESULT: [query_results]". Instead, actually execute the query and show the real results from the database.
    """
    
    # Create the base agent
    base_agent = ChainlitAssistantAgent(
        name="DatabaseQueryAgent",
        system_message=prompt,
        llm_config=llm_config,
    )
    
    # Save the database path in agent's metadata
    base_agent.metadata = {"db_path": db_path}
    
    # Store the original generate_reply method
    original_generate_reply = base_agent.generate_reply
    
    # Create a wrapper method that will intercept responses and execute queries when needed
    def generate_reply_with_execution(self, messages=None, sender=None, **kwargs):
        # First get the normal response using the original method
        response = original_generate_reply(messages=messages, sender=sender, **kwargs)
        
        # Check if the response contains "PROCEED_TO_DATABASE:"
        if "PROCEED_TO_DATABASE:" in response:
            try:
                # Extract the SQL query using regex
                match = re.search(r'PROCEED_TO_DATABASE:\s*(.*?)\s*(?:$|REQUEST_REVISION:)', response, re.DOTALL)
                if match:
                    sql_query = match.group(1).strip()
                    
                    # Remove any markdown code formatting if present
                    sql_query = re.sub(r'```sql|```', '', sql_query).strip()
                    
                    # Execute the query
                    query_result = query_database(sql_query, self.metadata['db_path'])
                    
                    # Format the response with the actual results
                    result_response = f"""I've executed your SQL query:

```sql
{sql_query}
```

Here are the results:

{query_result}
"""
                    return result_response
            except Exception as e:
                return f"I encountered an error while trying to execute the query: {str(e)}"
        
        # For errors or non-query responses, return the original response
        return response
    
    # Replace the original generate_reply method with our new one
    base_agent.generate_reply = generate_reply_with_execution.__get__(base_agent)
    
    return base_agent


def query_database(db_path, sql_query):
    """
    Direct function to query the database without going through the agent.
    Useful for debugging or direct queries.
    """
    try:
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()
        cursor.execute(sql_query)
        result = cursor.fetchall()
        
        # Get column names
        if cursor.description:
            column_names = [col[0] for col in cursor.description]
        else:
            column_names = []
            
        connection.close()
        return {"columns": column_names, "data": result}
    except Exception as e:
        return {"error": str(e)}