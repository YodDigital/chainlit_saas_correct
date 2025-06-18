import sqlite3
from autogen import AssistantAgent
from .chainlit_agents import ChainlitAssistantAgent
import re
import urllib.request
import tempfile


# def load_actual_schema(db_path):
#     """Dynamically loads the REAL schema from the database, including columns for each table"""
#     conn = sqlite3.connect(db_path)
#     schema = {"tables": {}, "columns": {}}

#     # Get all tables
#     tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()

#     for table in tables:
#         table_name = table[0]
#         cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
#         column_names = [col[1] for col in cols]  # col[1] = column name
#         schema["tables"][table_name] = column_names
#         for col in column_names:
#             schema["columns"][col] = table_name  # map column to table (last wins)

#     conn.close()
#     return schema


def execute_query(query, db_path):
    try:
       
        # Execute query
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()
        cursor.execute(query)
        results = cursor.fetchall()

        # Get column names
        column_names = [col[0] for col in cursor.description] if cursor.description else []
        connection.close()

        if not results:
            return "Query executed successfully. No results returned."

        formatted_results = ["| " + " | ".join(column_names) + " |",
                             "| " + " | ".join(["---"] * len(column_names)) + " |"]
        for row in results:
            formatted_results.append("| " + " | ".join(map(str, row)) + " |")

        return "\n".join(formatted_results)

    except Exception as e:
         return f"ROUTE_TO_FORMULATION_AGENT:\nThe query failed because:\n- {str(e)}"

def create_database_query_agent(db_url, llm_config):
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        urllib.request.urlretrieve(db_url, tmp_file.name)
        db_path = tmp_file.name

    # real_schema = load_actual_schema(db_path)

    prompt = f"""
You are the Database Query Agent.

Your only task is to execute SQL queries on the database.

When you receive:
    PROCEED_TO_DATABASE: [SQL_QUERY]

Do the following:

1. Directly execute the SQL query on the database — no validation or analysis.

2. If the query executes successfully:
    - Return the actual query result (not a placeholder).
    - Format as: RESULT: [query_result]

3. If execution fails due to any reason (e.g., syntax error, missing column/table, logic issues):
    - DO NOT attempt to fix it.
    - DO NOT generate a new query.
    - Instead, return:
        ROUTE_TO_FORMULATION_AGENT:
        The query failed because:
        - [List clear reasons based on the error]
        - [If possible, include hints from the database error to guide correction]

IMPORTANT:
- Do not guess or modify queries.
- Only act based on the query received.
- If the failure reason includes a hallucinated column/table, specify it clearly in the error.
- When a query is valid, DO NOT just respond with "RESULT: [query_results]". Instead, actually execute the query and show the real results from the database.
    """

    def execute_with_schema(query):
        return execute_query(query, db_path)

    base_agent = ChainlitAssistantAgent(
        name="DatabaseQueryAgent",
        system_message=prompt,
        llm_config=llm_config,
    )

    base_agent.metadata = {"db_path": db_path}
    original_generate_reply = base_agent.generate_reply

    def generate_reply_with_execution(self, messages=None, sender=None, **kwargs):
        response = original_generate_reply(messages=messages, sender=sender, **kwargs)

        if "PROCEED_TO_DATABASE:" in response:
            try:
                match = re.search(r'PROCEED_TO_DATABASE:\s*(.*?)\s*(?:$|REQUEST_REVISION:)', response, re.DOTALL)
                if match:
                    sql_query = match.group(1).strip()
                    sql_query = re.sub(r'```sql|```', '', sql_query).strip()
                    query_result = execute_with_schema(sql_query)
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

        return response

    base_agent.generate_reply = generate_reply_with_execution.__get__(base_agent)
    return base_agent


def query_database(db_path, sql_query):
    try:
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()
        cursor.execute(sql_query)
        result = cursor.fetchall()

        if cursor.description:
            column_names = [col[0] for col in cursor.description]
        else:
            column_names = []

        connection.close()
        return {"columns": column_names, "data": result}
    except Exception as e:
        return {"error": str(e)}
