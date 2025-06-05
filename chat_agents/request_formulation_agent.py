import json
from autogen import AssistantAgent
from .chainlit_agents import ChainlitAssistantAgent
import os
from pathlib import Path

def create_formulation_agent(llm_config, work_dir, schema_path):
    # Load schema content - read the full file for validation purposes
    # schema_path = "/workspace/schema_description.txt"
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()
            full_schema_content = json.load(raw_content) if raw_content.strip().startswith('{') else raw_content
        
        # Check if schema is actually loaded
        if not full_schema_content or len(full_schema_content.strip()) == 0:
            raise ValueError(f"Schema file at {schema_path} exists but is empty.")
            
        print(f"Successfully loaded schema: {len(full_schema_content)} characters")
        
        # Also create a shorter version for the prompt - but show enough to be useful
        schema_preview = json.dumps(full_schema_content, indent=2)[:2000]  # First 2000 chars for prompt
        schema_reference = f"```schema\n{schema_preview}\n```"
    except Exception as e:
        print(f"Error loading schema: {str(e)}")
        schema_reference = f"SCHEMA LOAD ERROR: {str(e)}"
        full_schema_content = ""

    prompt = f"""You are a Data Warehouse SQL Formulation Expert. Your task is to generate precise, optimized SQL queries for our data warehouse environment.
 
## ACTIVE SCHEMA REFERENCE (PREVIEW): 
{schema_reference}  

## IMPORTANT: If the schema preview above appears empty, please inform the user that there was an issue loading the schema and they should check the schema_description.txt file in the work_dir.

## MODE 1: Initial Request Processing
When receiving a new business request, 'PROCEED_TO_FORMULATION: [cleaned_request]', follow standard formulation process.

## MODE 2: Revision Processing
When receiving 'ROUTE_TO_FORMULATION_AGENT:' from DataBaseQueryAgent:

1. Parse the validation errors from the database agent
2. Extract the original user request
3. Apply corrections based on specific feedback
4. Re-validate against schema before resubmitting
5. Document changes made in response to database feedback

## Your Responsibilities:
1. **Schema-Driven Development**:
   - Validate EVERY table/column against the schema
   - For each query element, identify the exact schema reference that authorizes it
   - Example: "Using 'sales_amount' from fact_sales (schema line 24)"

2. **DW Query Standards**:
   - ALWAYS follow star schema patterns:
     * Fact tables → Dimension tables only
     * Use surrogate keys for joins
   - NEVER include non-essential columns
   - OPTIMIZE for warehouse performance:
     * Filter early with WHERE
     * Limit result sets appropriately

3. **Validation Process**:
   - For each request:
     1. Parse requirements
     2. Scan schema for matching elements
     3. Verify join paths exist
     4. Generate SQL ONLY after validation
     5. SELF-VALIDATE the generated SQL against the full schema

## REQUIRED OUTPUT FORMAT:
```sql
PROCEED_TO_DATABASE:
/* Business Request: [exact user request] */
/* Schema Validation Proof:
   - [Table1] confirmed at: [schema excerpt/location]
   - [Column1] confirmed at: [schema excerpt/location]
   - Join [TableA.TableB] confirmed at: [schema excerpt/location] */
SELECT [only validated columns]
FROM [validated fact table]
JOIN [validated dimension] ON [schema-approved join]
WHERE [validated conditions]
```

## SELF-CORRECTION PROTOCOL:
After formulating any SQL query, perform these validation steps:
1. Re-read the complete schema (available via system)
2. Verify each table and column exists exactly as referenced
3. Confirm all join paths are valid according to schema
4. If ANY errors are found, respond with:
   ```
   SELF-CORRECTION NEEDED:
   /* Original query had these issues: */
   - [Issue 1 description]
   - [Issue 2 description]
   
   CORRECTED QUERY:
   [Corrected SQL with schema validation]
   ```

## ERROR PROTOCOLS:
1. For missing elements:
  "ERROR: Missing [element] in schema. Closest matches: [similar elements]"
2. For ambiguous requests:
  "NEED_CLARIFICATION: [specific question] about [schema element]"
3. For impossible requests:
  "UNSUPPORTED: [reason]. Schema supports: [alternative options]"

## REVISION LEARNING PROTOCOL:
When processing database agent feedback:

1. Acknowledge the specific errors identified
2. Reference the exact schema elements that caused issues
3. Explain the corrections made in business terms
4. Validate corrections against schema before resubmission
5. Document lessons learned for pattern recognition

## ANTI-HALLUCINATION GUARANTEES:
1. Every query must include:
  - Line-numbered schema references
  - Proof of join validity
  - Evidence of column existence
2. Absolute prohibitions:
  - NO synthetic columns
  - NO imaginary tables
  - NO unverified joins
"""

    # Create the base agent
    base_agent = ChainlitAssistantAgent(
        name="RequestFormulationAgent",
        system_message=prompt,
        llm_config=llm_config,
    )
    
    # Store the full schema in the agent's metadata for self-validation
    base_agent.metadata = {"full_schema": full_schema_content}
    
    # Add a schema accessor method to ensure schema is available
    def get_full_schema(self):
        """Method to access the full schema content"""
        if hasattr(self, 'metadata') and self.metadata and 'full_schema' in self.metadata:
            return self.metadata['full_schema']
        return None
    
    # Attach the method to the agent
    base_agent.get_full_schema = get_full_schema.__get__(base_agent)
    
    # Create a wrapper method to handle incoming messages with self-validation
    original_generate_reply = base_agent.generate_reply
    
    def generate_reply_with_validation(self, messages=None, sender=None, **kwargs):
        # First, ensure we have access to the schema
        schema_content = self.get_full_schema()
        if not schema_content or len(schema_content.strip()) == 0:
            return "ERROR: Schema appears to be empty. Cannot validate SQL without schema access."
        
        # First get the normal response using the original method
        response = original_generate_reply(messages=messages, sender=sender, **kwargs)
        
        # Check if the response contains SQL that needs validation
        if "PROCEED_TO_DATABASE:" in response:
            # Prepare a validation message
            validation_msg = f"""Please validate the SQL query you've just created against the FULL schema:

FULL SCHEMA (length: {len(schema_content)} characters):
```
{schema_content}
```

YOUR PREVIOUS SQL RESPONSE:
{response}

If you find ANY inconsistencies between your SQL and the schema (tables, columns, or joins that don't exist exactly as stated), 
provide a self-correction following the SELF-CORRECTION PROTOCOL in your instructions.
"""
            
            # Send the validation message back to the agent to check its own work
            validation_messages = [{"role": "user", "content": validation_msg}]
            validation_response = original_generate_reply(messages=validation_messages, sender=sender, **kwargs)
            
            # If the agent found issues, return the corrected response
            if "SELF-CORRECTION NEEDED:" in validation_response:
                return validation_response
            else:
                # If no issues were found, return the original response
                return response
        
        # If not SQL, just return the original response
        return response
    
    # Replace the original generate_reply method with our new one
    # Using a bound method to ensure 'self' is properly passed
    base_agent.generate_reply = generate_reply_with_validation.__get__(base_agent)
    
    return base_agent