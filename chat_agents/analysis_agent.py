from autogen import AssistantAgent
from .chainlit_agents import ChainlitAssistantAgent


def create_analysis_agent(llm_config, work_dir, next_agent_name="formulation_agent"):

    prompt_dwh_gen_agent = f"""
    You are the User Request Analysis Agent.

    1. Receive a user request and **rephrase** it in clearer analytical terms.
    2. Ask the user for confirmation: e.g., \"Did I understand correctly?\"
    3. Wait for a confirmation message like \"yes\", \"correct\", \"that's right\", etc.
    4. If confirmation is positive, output: 'PROCEED_TO_FORMULATION: [cleaned_request]'
    5. If the user says \"no\" or gives an unclear response, ask again for clarification.
    6. Always prioritize clarity and confirmation before proceeding.

    ONLY move forward if the user clearly agrees with your interpretation.
    """

    return ChainlitAssistantAgent(
        name="Comprehension_Assistant",
        system_message=f"""{prompt_dwh_gen_agent}\n\n
        CONTAINER PATHS:
        1. Working directory: {work_dir}""",
        llm_config=llm_config,
    )

