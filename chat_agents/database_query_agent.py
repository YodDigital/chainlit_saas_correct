import sqlite3
from autogen import AssistantAgent
from .chainlit_agents import ChainlitAssistantAgent
import re
import urllib.request
import tempfile


def load_actual_schema(db_path):
    """Dynamically loads the REAL schema from the database, including columns for each table"""
    conn = sqlite3.connect(db_path)
    schema = {"tables": {}, "columns": {}}

    # Get all tables
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()

    for table in tables:
        table_name = table[0]
        cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        column_names = [col[1] for col in cols]  # col[1] = column name
        schema["tables"][table_name] = column_names
        for col in column_names:
            schema["columns"][col] = table_name  # map column to table (last wins)

    conn.close()
    return schema


def execute_query(query, schema, db_path):
    try:
        # Extract referenced tables
        tables_in_query = set(re.findall(r'\bFROM\s+(\w+)|\bJOIN\s+(\w+)', query, re.IGNORECASE))
        tables_in_query = {t for pair in tables_in_query for t in pair if t}

        # Validate tables
        for table in tables_in_query:
            if table not in schema["tables"]:
                return f"ERROR: Table '{table}' doesn't exist. Available tables: {list(schema['tables'].keys())}"

        # Validate columns
        columns_in_query = re.findall(r'SELECT\s+(.*?)\s+FROM|WHERE\s+(.*?)\s*(?:AND|OR|GROUP BY|ORDER BY|LIMIT|;|$)', query, re.IGNORECASE)
        flat_cols = [col for pair in columns_in_query for col in pair if col]
        all_cols = set()
        for col_block in flat_cols:
            col_candidates = re.split(r'[ ,]+', col_block.strip())
            all_cols.update([col.strip() for col in col_candidates if col.strip()])

        missing_cols = [col for col in all_cols if '.' not in col and col not in schema['columns']]
        if missing_cols:
            return f"ERROR: Columns not found in schema: {missing_cols}. Available columns: {list(schema['columns'].keys())}"

        # Execute query
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()
        cursor.execute(query)
        results = cursor.fetchall()

        # Get column names
        if cursor.description:
            column_names = [col[0] for col in cursor.description]
        else:
            column_names = []

        connection.close()

        if not results:
            return "Query executed successfully. No results returned."

        formatted_results = ["| " + " | ".join(column_names) + " |",
                             "| " + " | ".join(["---"] * len(column_names)) + " |"]
        for row in results:
            formatted_results.append("| " + " | ".join(map(str, row)) + " |")

        return "\n".join(formatted_results)

    except Exception as e:
        return f"ERROR: {str(e)}"


def create_database_query_agent(db_url, llm_config):
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        urllib.request.urlretrieve(db_url, tmp_file.name)
        db_path = tmp_file.name

    real_schema = load_actual_schema(db_path)

    prompt = f"""
    ## STRICT SCHEMA RULES
    ACTUAL TABLES: {list(real_schema['tables'].keys())}
    NEVER suggest tables/columns not listed here!

    You are a database query agent with these responsibilities:

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

    def execute_with_schema(query):
        return execute_query(query, real_schema, db_path)

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
