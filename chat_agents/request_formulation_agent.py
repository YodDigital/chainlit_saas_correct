import tempfile
from autogen import AssistantAgent
import urllib
from .chainlit_agents import ChainlitAssistantAgent
import sqlite3
import json

def load_actual_schema(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    schema = {"tables": {}}

    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()

    for table in tables:
        table_name = table[0]
        columns_info = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
        column_dict = {}

        for col in columns_info:
            col_name = col[1]
            col_type = col[2]
            column_dict[col_name] = col_type

        schema["tables"][table_name] = {"columns": column_dict}

    conn.close()
    return schema
    
def summarize_schema(schema):
    summary = []
    for table, details in schema["tables"].items():
        summary.append(f"Table: {table}")
        for col, dtype in details["columns"].items():
            summary.append(f"  {col}: {dtype}")
    return "\n".join(summary)

def flatten_schema_dict(schema):
    return json.dumps(schema["tables"], indent=2)

def create_formulation_agent(llm_config, work_dir, db_url, schema_path):
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        urllib.request.urlretrieve(db_url, tmp_file.name)
        db_path = tmp_file.name

    
    schema = load_actual_schema(db_path)
    schema_summary = summarize_schema(schema)
    schema_dict_str = flatten_schema_dict(schema)

    prompt = f"""You are a Data Warehouse SQL Formulation Expert. Your task is to generate accurate and optimized SQL queries based on the user's request and the schema provided.

## ACTIVE SCHEMA SUMMARY
{schema_summary}

## FULL SCHEMA DICTIONARY (for strict validation)
{schema_dict_str}

## MODE 1: Initial Request Processing
When receiving a new business request, 'PROCEED_TO_FORMULATION: [cleaned_request]', follow standard formulation process.

## MODE 2: Revision Processing
When receiving 'ROUTE_TO_FORMULATION_AGENT:' from DataBaseQueryAgent:

1. Parse the validation errors from the database agent
2. Extract the original user request
3. Apply corrections based on specific feedback
4. Re-validate against schema before resubmitting
5. Document changes made in response to database feedback

## RULES TO FOLLOW:
1. 🚫 DO NOT invent tables or columns not explicitly in the schema.
2. ✅ Always validate that every table and column you use exists in the schema_dict.
3. ✅ Join logic must follow foreign key definitions.
4. ✅ Composite keys must be joined using all relevant columns.
5. ✅ If the request refers to an invalid column (like 'region_desc'), suggest the closest valid one (e.g., 'territory').
6. ❓ If unclear, request clarification before assuming.

## EXAMPLES:
JOIN example:
JOIN product_dimension ON sales_fact.product_code = product_dimension.product_code
JOIN customer_dimension ON sales_fact.customer_name = customer_dimension.customer_name AND sales_fact.phone = customer_dimension.phone

## OUTPUT FORMAT:
```sql
PROCEED_TO_DATABASE:
/* Business Request: [exact user request] */
/* Schema Validation:
 - Table and column matches with full schema reference
 - Join logic justified */
SELECT ...
FROM ...
JOIN ... ON ...
WHERE ...
```

## SELF-CORRECTION PROTOCOL:
If your SQL contains errors, respond with:
```
SELF-CORRECTION NEEDED:
/* Issues found: */
 - [describe the issue]
 - [correction explanation based on schema_dict]
CORRECTED QUERY:
[Correct SQL]
```
"""

    base_agent = ChainlitAssistantAgent(
        name="RequestFormulationAgent",
        system_message=prompt,
        llm_config=llm_config,
    )

    original_generate_reply = base_agent.generate_reply

    def generate_reply_with_validation(self, messages=None, sender=None, **kwargs):
        response = original_generate_reply(messages=messages, sender=sender, **kwargs)

        if "PROCEED_TO_DATABASE:" in response:
            validation_prompt = f"""
Validate this SQL query against the full schema:

SCHEMA:
{schema_summary}

RESPONSE:
{response}

If any elements are invalid, respond with a correction following the SELF-CORRECTION PROTOCOL. Only allow column/table names found in the schema_dict.
"""
            validation_messages = [{"role": "user", "content": validation_prompt}]
            validation_response = original_generate_reply(messages=validation_messages, sender=sender, **kwargs)

            if "SELF-CORRECTION NEEDED:" in validation_response:
                return validation_response

        return response

    base_agent.generate_reply = generate_reply_with_validation.__get__(base_agent)

    return base_agent
