from autogen import UserProxyAgent
from .chainlit_agents import ChainlitUserProxyAgent

def create_user_agent():
    return ChainlitUserProxyAgent (
        name='User',
        human_input_mode = 'ALWAYS',
    )