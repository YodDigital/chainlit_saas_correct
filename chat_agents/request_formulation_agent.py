from autogen import AssistantAgent
from .chainlit_agents import ChainlitAssistantAgent
import sqlite3
import json

def create_formulation_agent(llm_config, work_dir, db_path, schema_path):
    def load_schema_description(schema_path):
        with open(schema_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def summarize_schema(schema):
        summary = []
        for table, details in schema["tables"].items():
            summary.append(f"Table: {table}")
            for col, dtype in details["columns"].items():
                summary.append(f"  {col}: {dtype}")
        return "\n".join(summary)

    schema = load_schema_description(schema_path)
    schema_summary = summarize_schema(schema)

    prompt = f"""You are a Data Warehouse SQL Formulation Expert. Your task is to generate accurate and optimized SQL queries based on the user's request and the schema provided.

## ACTIVE SCHEMA SUMMARY
{schema_summary}

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
1. Always validate that every table and column you use exists in the schema.
2. When joining tables, ensure foreign key relationships are respected as defined.
3. Detect the correct dimension table when mapping user terms (e.g., "women" → dim_gender).
4. Ensure joins go from fact table to dimension table using defined foreign keys.
5. If a request is ambiguous or uses undefined terms, request clarification.

## JOIN EXAMPLES:
- A join between `sales_fact` and `product_dimension` should be:
  `JOIN product_dimension ON sales_fact.product_code = product_dimension.product_code`

- A composite key (e.g., customer_name, phone) must be joined using both columns.

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
 - [correction explanation]
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

If any elements are invalid, respond with a correction following the SELF-CORRECTION PROTOCOL.
"""
            validation_messages = [{"role": "user", "content": validation_prompt}]
            validation_response = original_generate_reply(messages=validation_messages, sender=sender, **kwargs)

            if "SELF-CORRECTION NEEDED:" in validation_response:
                return validation_response

        return response

    base_agent.generate_reply = generate_reply_with_validation.__get__(base_agent)

    return base_agent

