import logging
from typing import Dict, List, Optional, Union, Any  # Ensure 'Any' is included
from groq import Groq, GroqError
import json
import os
from dotenv import load_dotenv
from tools import AVAILABLE_TOOLS

# Load environment variables
load_dotenv()

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# System Prompt for User Comfort and Tool Use
SYSTEM_PROMPT = """
You are FoodieBot, a friendly and helpful AI assistant for FoodieSpot in Delhi, India. Your goal is to make dining reservations easy, enjoyable, and personalized for users. **ONLY handle requests related to Delhi restaurants.**

Speak conversationally and warmly, offering assistance in English or Hindi based on user preference (detect Hindi if used, otherwise default to English). If the user’s request is unclear (e.g., missing date or party size), ask polite clarifying questions like: “Could you tell me how many people and when you’d like to dine?”

Proactively suggest top restaurants or alternatives if the user’s criteria are narrow or unavailable. After using tools, weave results into natural responses (e.g., “I found Bukhara with a table for 4 at 7 PM!”) instead of raw data.

Available tools:
- `find_restaurants`: Find restaurants by cuisine, location, party size, date, or time.
- `check_availability`: Check table availability for a specific restaurant.
- `make_reservation`: Book a table with user details.
- `get_restaurant_details`: Get detailed info about a restaurant.

Use tools when needed, and always aim to delight the user with a smooth, comforting experience!
"""

class AgentBrain:
    """Handles LLM interaction with Groq API and tool invocation for FoodieSpot."""

    def __init__(self) -> None:
        """Initialize the Groq client with API key."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables.")
        self.client = Groq(api_key=api_key)
        self.model = "llama3-8b-8192"  # Llama 3.1-8B via Groq
        self.tools = AVAILABLE_TOOLS   # Tool registry from tools.py

    def process_message(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Union[str, List[Dict[str, str]]]]:
        """
        Process user input, invoke tools if needed, and return a response.

        Args:
            user_message: The user’s input string.
            conversation_history: List of previous messages for context (optional).

        Returns:
            Dict with 'response_type' ('text', 'tool_calls', 'error'),
            'content' (response or tool call details), and 'message' (user-friendly text).
        """
        logger.info(f"Processing user message: {user_message}")

        # Build message history
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})

        try:
            # Call Groq API with tool support
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": name,
                            "description": func.__doc__.split('\n')[1].strip() if func.__doc__ else f"{name} tool",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    arg: {"type": "string"} for arg in func.__code__.co_varnames[:func.__code__.co_argcount]
                                },
                                "required": []
                            }
                        }
                    } for name, func in self.tools.items()
                ],
                tool_choice="auto",
                temperature=0.3,
                max_tokens=1024
            )

            # Handle response
            completion = response.choices[0].message

            if hasattr(completion, "tool_calls") and completion.tool_calls:
                tool_calls = []
                for tool_call in completion.tool_calls:
                    tool_name = tool_call.function.name
                    if tool_name in self.tools:
                        try:
                            args = json.loads(tool_call.function.arguments)
                            result = self.tools[tool_name](**args)
                            tool_calls.append({
                                "name": tool_name,
                                "arguments": args,
                                "result": result
                            })
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse tool arguments: {e}")
                            return {
                                "response_type": "error",
                                "content": None,
                                "message": "Oops! I had trouble understanding that request. Could you try again?"
                            }
                    else:
                        logger.warning(f"Unknown tool called: {tool_name}")
                logger.info(f"Tool calls generated: {tool_calls}")
                return {
                    "response_type": "tool_calls",
                    "content": tool_calls,
                    "message": "I’m working on that for you! One moment..."
                }

            elif completion.content:
                logger.info(f"Text response generated: {completion.content}")
                return {
                    "response_type": "text",
                    "content": completion.content,
                    "message": completion.content
                }

            else:
                logger.warning("Empty response from LLM")
                return {
                    "response_type": "error",
                    "content": None,
                    "message": "Hmm, I didn’t get a clear response. Let’s try that again!"
                }

        except GroqError as e:
            logger.exception(f"Groq API error: {e}")
            return {
                "response_type": "error",
                "content": None,
                "message": "Sorry, something went wrong on my end. Please try again in a moment."
            }
        except Exception as e:
            logger.exception(f"Unexpected error in AgentBrain: {e}")
            return {
                "response_type": "error",
                "content": None,
                "message": "Oops! An unexpected glitch happened. Can you try again?"
            }

    def _execute_tool(self, tool_name: str, arguments: Dict[str, str]) -> Dict[str, Any]:
        """
        Execute a tool with given arguments (not directly called; used internally).

        Args:
            tool_name: Name of the tool to execute.
            arguments: Dictionary of tool arguments.

        Returns:
            Tool execution result.
        """
        if tool_name in self.tools:
            return self.tools[tool_name](**arguments)
        else:
            logger.error(f"Tool {tool_name} not found")
            return {"status": "error", "message": f"Tool {tool_name} is not available."}