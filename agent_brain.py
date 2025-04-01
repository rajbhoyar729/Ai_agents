# agent_brain.py (Native Tool Calling - Refined Prompt)

import os
import json
import logging
from typing import List, Dict, Tuple, Union, Optional, Any
from groq import Groq, GroqError
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Tool Schema Definition (Keep as before) ---
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "find_restaurants",
            "description": "Searches for FoodieSpot restaurants in Delhi based on cuisine, location, party size, date, and time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cuisine": {"type": "string", "description": "e.g., North Indian, Italian"},
                    "location": {"type": "string", "description": "Area within Delhi, e.g., Connaught Place"},
                    "party_size": {"type": "integer"},
                    "date": {"type": "string", "description": "Format: YYYY-MM-DD"},
                    "time": {"type": "string", "description": "e.g., 7:00 PM"},
                },
                "required": ["party_size", "date", "time"],
            },
        },
    },
    # --- Keep schemas for check_availability, make_reservation, get_restaurant_details ---
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Checks if a specific Delhi restaurant has table availability.",
            "parameters": {
                "type": "object",
                "properties": {
                    "restaurant_id": {"type": "string"}, "party_size": {"type": "integer"},
                    "date": {"type": "string"}, "time": {"type": "string"},
                }, "required": ["restaurant_id", "party_size", "date", "time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "make_reservation",
            "description": "Creates a new reservation at a specific Delhi restaurant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "restaurant_id": {"type": "string"}, "party_size": {"type": "integer"},
                    "date": {"type": "string"}, "time": {"type": "string"},
                    "user_name": {"type": "string"}, "user_contact": {"type": "string"},
                }, "required": ["restaurant_id", "party_size", "date", "time", "user_name", "user_contact"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_restaurant_details",
            "description": "Retrieves detailed information about a specific Delhi restaurant.",
            "parameters": {
                "type": "object",
                "properties": {"restaurant_id": {"type": "string"}}, "required": ["restaurant_id"],
            },
        },
    },
]


class AgentBrain:
    """
    Handles interaction with the LLM via Groq API using native tool calling.
    Focus: Delhi, India restaurants. Includes prompt refinement for waiting.
    """

    # --- System Prompt (Updated to emphasize WAITING for tool results) ---
    SYSTEM_PROMPT = """
    You are FoodieBot, an AI assistant for the FoodieSpot restaurant chain in Delhi, India.
    **IMPORTANT: You ONLY handle requests for Delhi.** Decline requests for other cities politely.

    Your primary purpose is to help users find information and book tables at FoodieSpot restaurants in Delhi using the available tools. Be friendly and conversational. Ask clarifying questions if needed.

    **CRITICAL TOOL USE FLOW:**
    1. Analyze the user's request (ensure it's for Delhi).
    2. If external information or an action is needed, decide which tool function to use (e.g., `find_restaurants`, `check_availability`).
    3. You will then generate a 'tool_calls' request. **STOP generating text after this.**
    4. The system running the tools will execute the function you requested.
    5. You will then receive a **new message** in the conversation with the role `tool`. This message contains the results (or errors) from the tool execution. Its `tool_call_id` matches your request.
    6. **IMPORTANT: WAIT** until you receive this message with `role: tool`. **DO NOT** try to predict or summarize the tool's outcome before receiving the actual results in the `tool` message.
    7. **ONLY AFTER** receiving the `tool` message(s), formulate your next **conversational response** to the original user, incorporating the information provided in the `content` of the `tool` message(s). Refer to the results clearly.
    8. If no tool was needed in step 2, respond directly to the user conversationally.
    9. Before requesting `make_reservation`, always confirm all details with the user conversationally.

    Available Tool Functions: `find_restaurants`, `check_availability`, `make_reservation`, `get_restaurant_details`.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.1-8b-instant", temperature: float = 0.1): # Lowered temp
        """Initializes the AgentBrain for native tool calling."""
        resolved_api_key = api_key or os.getenv("GROQ_API_KEY")
        if not resolved_api_key:
            logger.error("Groq API key not provided or found in env vars (GROQ_API_KEY).")
            raise ValueError("GROQ_API_KEY is required.")
        try:
            self.client = Groq(api_key=resolved_api_key)
            self.model = model
            self.temperature = temperature # Lower temperature for more deterministic behavior
            logger.info(f"AgentBrain (Native Tool Calling, Refined Prompt) initialized: {self.model}, Temp: {self.temperature}")
        except GroqError as e:
            logger.exception(f"Failed to initialize Groq client: {e}", exc_info=True)
            raise

    def _prepare_messages(self, conversation_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Formats the message list for the Groq API call for native tool use.
        Includes system prompt and ensures correct formatting for user, assistant, and tool messages.
        """
        # (Keep the _prepare_messages function exactly as in the previous 'native tool calling' update - it should be correct)
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        for msg in conversation_history:
            role = msg.get("role")
            if role == "assistant":
                 message_to_add = {"role": "assistant"}
                 if "content" in msg and msg["content"] is not None: message_to_add["content"] = msg["content"]
                 if "tool_calls" in msg and isinstance(msg["tool_calls"], list): message_to_add["tool_calls"] = msg["tool_calls"]
                 if "content" in message_to_add or "tool_calls" in message_to_add: messages.append(message_to_add)
            elif role == "user" and msg.get("content") is not None:
                messages.append({"role": "user", "content": msg["content"]})
            elif role == "tool" and msg.get("tool_call_id") and msg.get("content") is not None:
                 messages.append({"role": "tool", "tool_call_id": msg["tool_call_id"], "content": msg["content"]})
            else: logger.warning(f"Skipping malformed message in history: {msg}")
        return messages


    def get_response(self, conversation_history: List[Dict[str, Any]]) -> Tuple[str, Union[str, List[Dict[str, Any]], None], Optional[Dict]]:
        """
        Gets a response from the LLM using native tool calling.
        Expects the full conversation history.
        """
        # (Keep the get_response function exactly as in the previous 'native tool calling' update - it correctly handles the API call and response parsing)
        messages = self._prepare_messages(conversation_history)
        logger.info(f"Sending request to LLM ({self.model}) with {len(messages)} messages (Native Tool Call).")
        # logger.debug(f"Messages payload: {json.dumps(messages, indent=2)}") # Uncomment for detailed debugging

        raw_assistant_msg_for_history = None # To store the message for history later

        try:
            response = self.client.chat.completions.create(
                model=self.model, messages=messages, tools=TOOLS_SCHEMA, tool_choice="auto",
                temperature=self.temperature, max_tokens=1024,
            )
            response_message = response.choices[0].message
            finish_reason = response.choices[0].finish_reason
            raw_assistant_msg_for_history = {"role": "assistant", "content": response_message.content, "tool_calls": response_message.tool_calls if response_message.tool_calls else None,}
            raw_assistant_msg_for_history = {k: v for k, v in raw_assistant_msg_for_history.items() if v is not None}

            if response_message.tool_calls:
                logger.info(f"LLM response contains tool calls. Finish reason: {finish_reason}")
                parsed_tool_calls = []
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name; tool_call_id = tool_call.id
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                        parsed_tool_calls.append({"id": tool_call_id, "tool_name": function_name, "arguments": arguments})
                        logger.info(f"Parsed tool call: ID={tool_call_id}, Name={function_name}, Args={arguments}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse args for tool call {tool_call_id} ({function_name}): {tool_call.function.arguments}. Error: {e}")
                        return "error", f"Failed to parse arguments for tool {function_name}.", None
                    except Exception as e:
                         logger.error(f"Unexpected error processing tool call {tool_call_id} ({function_name}): {e}")
                         return "error", f"Unexpected error processing tool call for {function_name}.", None
                return "tool_calls", parsed_tool_calls, raw_assistant_msg_for_history
            elif response_message.content is not None:
                logger.info(f"LLM response contains text content. Finish reason: {finish_reason}")
                return "text", response_message.content, raw_assistant_msg_for_history
            else:
                 logger.warning(f"LLM response has no tool_calls and no content. Finish reason: {finish_reason}")
                 return "stop", None, raw_assistant_msg_for_history
        except GroqError as e:
            logger.error(f"Groq API error: {e}", exc_info=True); return "error", f"AI service error ({e.status_code}).", None
        except Exception as e:
            logger.exception("Unexpected error in get_response.", exc_info=True); return "error", "Unexpected internal error.", None