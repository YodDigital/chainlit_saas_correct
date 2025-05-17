from typing import Dict, Optional, Union
from autogen import AssistantAgent, UserProxyAgent, Agent
import chainlit as cl

class ChainlitAssistantAgent(AssistantAgent):
    """Handles assistant side of conversation with Chainlit visualization"""
    def send(
        self,
        message: Union[Dict, str],
        recipient: Agent,
        request_reply: Optional[bool] = None,
        silent: Optional[bool] = False,
    ) -> bool:
        # Always extract content safely
        # content = message if isinstance(message, str) else message.get("content", "")
        # content = str(message.get("output", message)) if isinstance(message, dict) else str(message)
        
        # Show message in Chainlit
        cl.run_sync(cl.Message(
            content=f"{self.name} → {recipient.name}:\n{message}",
            author=self.name
        ).send())
        
        # Ensure message is actually sent
        return super().send(message, recipient, request_reply, silent)

class ChainlitUserProxyAgent(UserProxyAgent):
    """Handles user input through Chainlit"""
    def get_human_input(self, prompt: str) -> str:
        try:
            # Get user response from Chainlit
            response = cl.run_sync(cl.AskUserMessage(content=prompt).send())
            
            # Return empty string if no response
            if not response:
                return ""
                
            # Handle different response formats
            return str(response.get("content", response)).strip()
        except Exception:
            return ""  # Fallback if anything goes wrong

    def send(
        self,
        message: Union[Dict, str],
        recipient: Agent,
        request_reply: Optional[bool] = None,
        silent: Optional[bool] = False,
    ):
        # Show user proxy messages in Chainlit
        # content = message if isinstance(message, str) else message.get("content", "")
        cl.run_sync(cl.Message(
            content=f"{self.name} → {recipient.name}:\n{message}",
            author=self.name
        ).send())
        
        # Ensure message is actually sent
        super().send(message, recipient, request_reply, silent)