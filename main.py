import logging
from typing import Dict, List, Optional, Union
import json
from agent_brain import AgentBrain
from tools import AVAILABLE_TOOLS

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MainProcessor:
    """Central processing unit for FoodieSpot AI Reservation Assistant."""

    def __init__(self) -> None:
        """Initialize the processor with AgentBrain and conversation history."""
        self.agent = AgentBrain()
        self.conversation_history: List[Dict[str, str]] = []
        self.tools = AVAILABLE_TOOLS

    def process_user_input(self, user_input: str) -> Dict[str, str]:
        """
        Process user input, coordinate with LLM and tools, and return a response.

        Args:
            user_input: User’s input string from app.py.

        Returns:
            Dict with 'message' (user-friendly response) and 'status' ('success', 'error').
        """
        logger.info(f"Processing user input: {user_input}")

        # Add user input to history
        self.conversation_history.append({"role": "user", "content": user_input})

        try:
            # Get LLM response from AgentBrain
            llm_response = self.agent.process_message(user_input, self.conversation_history)

            if llm_response["response_type"] == "text":
                # Direct text response from LLM
                response_message = llm_response["content"]
                self.conversation_history.append({"role": "assistant", "content": response_message})
                logger.info(f"Text response: {response_message}")
                return {"status": "success", "message": response_message}

            elif llm_response["response_type"] == "tool_calls":
                # Handle tool calls
                tool_results = self._process_tool_calls(llm_response["content"])
                final_response = self._format_tool_results(tool_results)
                self.conversation_history.append({"role": "assistant", "content": final_response})
                logger.info(f"Tool-based response: {final_response}")
                return {"status": "success", "message": final_response}

            elif llm_response["response_type"] == "error":
                # LLM error handling
                logger.warning(f"LLM error: {llm_response['message']}")
                return {"status": "error", "message": llm_response["message"]}

            else:
                logger.error(f"Unknown response type: {llm_response['response_type']}")
                return {
                    "status": "error",
                    "message": "Hmm, something unexpected happened. Let’s try that again!"
                }

        except Exception as e:
            logger.exception(f"Error in process_user_input: {e}")
            return {
                "status": "error",
                "message": "Oops! Something went wrong. Please try again in a moment."
            }

    def _process_tool_calls(self, tool_calls: List[Dict[str, Union[str, Dict]]]) -> List[Dict[str, Union[str, Dict]]]:
        """
        Execute tools based on LLM tool calls and return results.

        Args:
            tool_calls: List of tool call dictionaries from AgentBrain.

        Returns:
            List of tool execution results with status and messages.
        """
        results = []
        for call in tool_calls:
            tool_name = call["name"]
            arguments = call["arguments"]
            logger.info(f"Executing tool: {tool_name} with args: {arguments}")

            if tool_name in self.tools:
                try:
                    tool_result = self.tools[tool_name](**arguments)
                    results.append({
                        "tool_name": tool_name,
                        "status": tool_result.get("status", "success"),
                        "result": tool_result
                    })
                except Exception as e:
                    logger.exception(f"Tool execution failed for {tool_name}: {e}")
                    results.append({
                        "tool_name": tool_name,
                        "status": "error",
                        "result": {"message": f"Sorry, I couldn’t complete that step ({tool_name})."}
                    })
            else:
                logger.warning(f"Unknown tool: {tool_name}")
                results.append({
                    "tool_name": tool_name,
                    "status": "error",
                    "result": {"message": f"I don’t have a tool called {tool_name} yet!"}
                })
        return results

    def _format_tool_results(self, tool_results: List[Dict[str, Union[str, Dict]]]) -> str:
        """
        Merge tool results into a natural language response.

        Args:
            tool_results: List of tool execution results.

        Returns:
            User-friendly response string.
        """
        if not tool_results:
            return "I couldn’t find anything to do with that request. How can I assist you?"

        response_lines = []
        for result in tool_results:
            tool_name = result["tool_name"]
            status = result["status"]
            tool_output = result["result"]

            if status == "error":
                response_lines.append(tool_output["message"])
            elif tool_name == "find_restaurants":
                if tool_output["status"] == "success":
                    restaurant_names = ", ".join(r["name"] for r in tool_output["results"])
                    response_lines.append(f"Here are some great options: {restaurant_names}. Want to check availability?")
                else:
                    response_lines.append(tool_output["message"])
            elif tool_name == "check_availability":
                response_lines.append(tool_output["message"])
            elif tool_name == "make_reservation":
                if tool_output["status"] == "success":
                    response_lines.append(tool_output["message"])
                else:
                    response_lines.append(f"Booking didn’t work out: {tool_output['message']}")
            elif tool_name == "get_restaurant_details":
                if tool_output["status"] == "success":
                    details = tool_output["details"]
                    response_lines.append(
                        f"{details['name']} ({details['cuisine']}) is at {details['address']}. "
                        f"Open: {details['opening_hours']}. More info: {details['description']}"
                    )
                else:
                    response_lines.append(tool_output["message"])

        final_response = "\n".join(response_lines)
        if not final_response:
            final_response = "I’ve got the info, but I’m not sure how to present it yet. What’s next?"
        return final_response

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Return the current conversation history."""
        return self.conversation_history

def process_input(user_input: str) -> Dict[str, str]:
    """
    External interface for app.py to process user input.

    Args:
        user_input: User’s input string.

    Returns:
        Dict with 'message' and 'status'.
    """
    processor = MainProcessor()  # Singleton-like instance for now; could be persistent
    return processor.process_user_input(user_input)

if __name__ == "__main__":
    # For testing purposes only; app.py will call process_input()
    test_input = "Find Italian restaurants for 4 tomorrow at 7 PM"
    result = process_input(test_input)
    logger.info(f"Test result: {json.dumps(result, indent=2)}")