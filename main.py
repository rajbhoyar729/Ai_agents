import logging
import json
from typing import Dict, List, Optional, Union, Any, Tuple

# Local imports (ensure these modules are correct and accessible)
from agent_brain import AgentBrain  # Handles LLM communication
from tools import AVAILABLE_TOOLS    # Dictionary of available tool functions

# --- Constants ---
MAX_HISTORY_TURNS = 7  # Number of User/Assistant turns to keep (adjust based on context needs and token limits)
                       # Total messages sent will be roughly 2 * MAX_HISTORY_TURNS + system prompt + tool messages

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Main Orchestration Class ---

class MainProcessor:
    """
    Central processing unit for FoodieSpot AI Reservation Assistant.

    Orchestrates interaction between the user interface, the LLM (via AgentBrain),
    and the available tools. Manages conversation history and state.
    Leverages the LLM to synthesize tool results into natural language.
    """

    def __init__(self) -> None:
        """Initialize the processor with AgentBrain and an empty conversation history."""
        try:
            self.agent = AgentBrain()  # Instantiate the LLM interaction handler
            # Store the system prompt for easy access during history preparation
            self.system_prompt = getattr(self.agent, 'SYSTEM_PROMPT',
                                         "You are a helpful assistant.") # Fallback if not found
            logger.info("AgentBrain initialized successfully.")
        except ValueError as e:
            logger.error(f"Failed to initialize AgentBrain: {e}", exc_info=True)
            # Propagate the error so the UI layer knows initialization failed
            raise ValueError(f"AgentBrain initialization failed: {e}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during MainProcessor initialization: {e}", exc_info=True)
            raise RuntimeError(f"Unexpected error during MainProcessor setup: {e}") from e

        self.conversation_history: List[Dict[str, Any]] = [] # Stores the *full* history including tool interactions
        self.tools = AVAILABLE_TOOLS # Tool registry from tools.py

        logger.info("MainProcessor initialized.")

    def _prepare_history_for_llm(self) -> List[Dict[str, Any]]:
        """
        Prepares the conversation history for the LLM call.

        Includes the system prompt and prunes older messages if the history
        exceeds MAX_HISTORY_TURNS, ensuring the payload fits context limits.

        Returns:
            List[Dict[str, Any]]: The pruned history ready for the LLM API.
        """
        system_message = {"role": "system", "content": self.system_prompt}
        pruned_history = [system_message]

        # Calculate the maximum number of individual messages to keep (excluding system prompt)
        # This includes user, assistant, tool_calls, and tool messages
        max_messages_to_keep = MAX_HISTORY_TURNS * 3 # Rough estimate: user, assistant_decision/tool_call, tool_result per turn
                                                     # Adjust this multiplier based on typical tool usage patterns

        if len(self.conversation_history) <= max_messages_to_keep:
            pruned_history.extend(self.conversation_history)
        else:
            logger.warning(f"History length ({len(self.conversation_history)}) exceeds max ({max_messages_to_keep}). Pruning...")
            # Keep the most recent messages
            pruned_history.extend(self.conversation_history[-max_messages_to_keep:])

        logger.debug(f"Prepared history for LLM with {len(pruned_history)} messages.")
        return pruned_history

    def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Executes the tool calls requested by the LLM.

        Args:
            tool_calls: List of tool call objects from the LLM response.
                        Expected format per call: {'id': 'call_xyz', 'type': 'function', 'function': {'name': '...', 'arguments': '{"arg": "val"}'}}

        Returns:
            Tuple containing:
            - tool_results_for_llm: List of results formatted for the *next* LLM call (role='tool').
            - executed_calls_details: List containing info about executed calls for logging/debugging.
        """
        tool_results_for_llm = []
        executed_calls_details = []

        if not tool_calls:
            logger.warning("LLM requested tool calls, but the list was empty.")
            return [], []

        for call in tool_calls:
            tool_call_id = call.get('id')
            function_details = call.get('function', {})
            tool_name = function_details.get('name')
            arguments_str = function_details.get('arguments', '{}')

            if not tool_call_id or not tool_name:
                logger.error(f"Skipping invalid tool call object: {call}")
                continue

            logger.info(f"Attempting to execute tool '{tool_name}' (ID: {tool_call_id}) with args: {arguments_str}")

            if tool_name in self.tools:
                try:
                    # Parse arguments safely
                    try:
                        arguments = json.loads(arguments_str)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON arguments for tool '{tool_name}' (ID: {tool_call_id}): {arguments_str}")
                        result_content = json.dumps({"status": "error", "message": "Internal error: Failed to parse tool arguments."})
                        status = "error"
                    else:
                        # Execute the actual tool function
                        tool_function = self.tools[tool_name]
                        tool_result: Dict[str, Any] = tool_function(**arguments) # Tools should return dicts

                        # Log the raw result structure for debugging
                        logger.debug(f"Raw result from tool '{tool_name}' (ID: {tool_call_id}): {tool_result}")

                        # Serialize the entire result dict as JSON content for the LLM
                        result_content = json.dumps(tool_result)
                        status = tool_result.get("status", "success") # Assume success if status missing

                except TypeError as e:
                    # Handle cases where arguments don't match function signature
                    logger.exception(f"Argument mismatch error executing tool '{tool_name}' (ID: {tool_call_id}): {e}")
                    result_content = json.dumps({"status": "error", "message": f"Internal error: Incorrect arguments provided for tool '{tool_name}'."})
                    status = "error"
                except Exception as e:
                    # Catch unexpected errors during tool execution
                    logger.exception(f"Unexpected error executing tool '{tool_name}' (ID: {tool_call_id}): {e}")
                    result_content = json.dumps({"status": "error", "message": f"Sorry, an unexpected issue occurred while trying to use the '{tool_name}' tool."})
                    status = "error"

            else:
                # Tool requested by LLM is not available/defined
                logger.warning(f"LLM requested unknown tool: '{tool_name}' (ID: {tool_call_id})")
                result_content = json.dumps({"status": "error", "message": f"Sorry, I don't have a tool called '{tool_name}' available."})
                status = "error"

            # Append result formatted for the next LLM call
            tool_results_for_llm.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": tool_name,
                "content": result_content, # Send structured JSON result back
            })
            # Store execution details for logging/internal use
            executed_calls_details.append({
                 "tool_call_id": tool_call_id,
                 "name": tool_name,
                 "arguments": arguments_str,
                 "status": status,
                 "result_summary": result_content[:100] + "..." if len(result_content) > 100 else result_content # Keep summary brief
            })

        logger.info(f"Executed {len(executed_calls_details)} tool calls.")
        return tool_results_for_llm, executed_calls_details


    def process_user_input(self, user_input: str) -> Dict[str, str]:
        """
        Processes user input, manages conversation flow with the LLM and tools.

        Handles tool execution and relies on the LLM to synthesize final responses.

        Args:
            user_input: User's input string from the UI (e.g., app.py).

        Returns:
            Dict containing 'status' ('success' or 'error') and 'message' (user-friendly response).
        """
        logger.info(f"Processing user input: {user_input}")

        # 1. Add user input to the full conversation history
        self.conversation_history.append({"role": "user", "content": user_input})

        try:
            # 2. Prepare pruned history for the first LLM call
            history_for_llm = self._prepare_history_for_llm()

            # 3. First LLM Call: Get response or tool requests
            logger.info("Making initial call to AgentBrain...")
            llm_response = self.agent.process_message(
                user_message=user_input, # Pass current input explicitly if needed by agent
                conversation_history=history_for_llm
                # Note: agent_brain.process_message might need adjustment
                # if it expects user_message *only* when role='user' is last in history.
            )
            logger.debug(f"Initial LLM response details: {llm_response}")

            # 4. Handle LLM Response
            response_type = llm_response.get("response_type")
            response_content = llm_response.get("content")
            response_message = llm_response.get("message", "...") # User-facing intermediate message

            if response_type == "text":
                # Direct text response, no tools needed for this turn
                final_message = response_content
                self.conversation_history.append({"role": "assistant", "content": final_message})
                logger.info(f"LLM provided direct text response: {final_message}")
                return {"status": "success", "message": final_message}

            elif response_type == "tool_calls":
                # LLM requested tool execution
                logger.info("LLM requested tool calls. Executing...")
                requested_tool_calls = response_content # List of tool call objects

                # Add the assistant's decision to call tools to history
                # The Groq API response structure includes the 'tool_calls' on the assistant message
                assistant_message_with_calls = {"role": "assistant", "content": None} # Content might be null when tool_calls present
                # Ensure the tool_calls structure from Groq is preserved
                if isinstance(requested_tool_calls, list):
                     assistant_message_with_calls["tool_calls"] = requested_tool_calls
                self.conversation_history.append(assistant_message_with_calls)

                # Execute tools and get structured results
                tool_results_for_llm, executed_calls_details = self._execute_tool_calls(requested_tool_calls)
                logger.debug(f"Tool execution details: {executed_calls_details}")

                # Add tool results to the *full* history
                self.conversation_history.extend(tool_results_for_llm)

                if not tool_results_for_llm:
                    # Handle case where execution failed for all requested tools
                     logger.error("Tool execution yielded no usable results.")
                     fallback_message = "I tried to use my tools, but something went wrong. Could you try rephrasing?"
                     self.conversation_history.append({"role": "assistant", "content": fallback_message})
                     return {"status": "error", "message": fallback_message}

                # 5. Second LLM Call: Send tool results back for synthesis
                logger.info("Sending tool results back to LLM for synthesis...")
                history_for_synthesis = self._prepare_history_for_llm() # Prepare pruned history again, now *with* tool results

                final_llm_response = self.agent.process_message(
                    user_message=None, # No new user input for this call
                    conversation_history=history_for_synthesis
                )
                logger.debug(f"LLM synthesis response details: {final_llm_response}")

                # 6. Process Final Synthesized Response
                final_response_type = final_llm_response.get("response_type")
                final_response_content = final_llm_response.get("content")

                if final_response_type == "text":
                    final_message = final_response_content
                    self.conversation_history.append({"role": "assistant", "content": final_message})
                    logger.info(f"LLM synthesized final response: {final_message}")
                    return {"status": "success", "message": final_message}
                else:
                    # Handle unexpected response after synthesis (e.g., LLM asks for tools again?)
                    logger.error(f"Unexpected LLM response type '{final_response_type}' after sending tool results.")
                    fallback_message = "I've processed the information using my tools, but I'm having trouble summarizing it. What would you like to do next?"
                    self.conversation_history.append({"role": "assistant", "content": fallback_message})
                    return {"status": "error", "message": fallback_message}

            elif response_type == "error":
                # Error reported by AgentBrain (e.g., API error)
                error_message = llm_response.get("message", "An unspecified error occurred.")
                logger.error(f"AgentBrain reported an error: {error_message}")
                # Don't add agent error messages to history? Or add as assistant? Let's not add.
                return {"status": "error", "message": error_message}

            else:
                # Unknown response type from AgentBrain
                logger.error(f"Received unknown response type from AgentBrain: {response_type}")
                return {"status": "error", "message": "An unexpected internal response occurred. Please try again."}

        except Exception as e:
            logger.exception(f"Critical error in MainProcessor.process_user_input: {e}")
            # Provide a generic error message to the user in case of unexpected failures
            return {
                "status": "error",
                "message": "Oops! Something went wrong on my end. Please try again in a moment."
            }

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Returns the full, un-pruned conversation history managed by this processor."""
        # Return a copy to prevent external modification
        return list(self.conversation_history)

# --- Standalone Function for Stateless Testing ---

def process_input(user_input: str) -> Dict[str, str]:
    """
    External interface for **stateless** processing of user input.

    Creates a new MainProcessor instance for each call, meaning it has no memory
    of previous interactions via this function. Suitable for simple testing or
    command-line interaction where conversation history is not required.

    **Do not use this for the main chat application (app.py) which needs state.**

    Args:
        user_input: User’s input string.

    Returns:
        Dict with 'message' (response) and 'status' ('success' or 'error').
    """
    logger.info("Executing stateless process_input function...")
    try:
        # Create a temporary, stateless processor instance for this single call
        stateless_processor = MainProcessor()
        result = stateless_processor.process_user_input(user_input)
        logger.info("Stateless process_input completed.")
        return result
    except Exception as e:
        # Catch initialization or processing errors for the stateless call
        logger.error(f"Error during stateless process_input: {e}", exc_info=True)
        return {"status": "error", "message": f"Stateless processing failed: {e}"}


# --- Testing Block ---

if __name__ == "__main__":
    print("\n--- Testing Stateless Interaction ---")
    # Using the stateless function (no memory between calls)
    test_input_1 = "Find me an Italian restaurant in Connaught Place for 2 people tonight at 8 PM"
    result_1 = process_input(test_input_1)
    print(f"User: {test_input_1}")
    print(f"Bot : {result_1['message']} (Status: {result_1['status']})")

    test_input_2 = "Okay, check availability for the first one you mentioned." # This will fail in stateless
    result_2 = process_input(test_input_2)
    print(f"\nUser: {test_input_2}")
    print(f"Bot : {result_2['message']} (Status: {result_2['status']})")
    print("------------------------------------")

    print("\n--- Testing Stateful Interaction (Simulated) ---")
    # Simulating how app.py would use a single instance
    try:
        stateful_processor = MainProcessor() # Create one instance

        print("User: Find North Indian spots in Khan Market")
        response_a = stateful_processor.process_user_input("Find North Indian spots in Khan Market")
        print(f"Bot : {response_a['message']} (Status: {response_a['status']})")
        print(f"History Length: {len(stateful_processor.get_conversation_history())}")

        print("\nUser: Check availability for SodaBottleOpenerWala for 3 people tomorrow at 7pm")
        # Assuming SodaBottleOpenerWala ID is del006 from restaurants.py default data
        # Tool might need restaurant ID, LLM might infer it or ask. Let's assume LLM asks for ID or fails gracefully.
        # Or, if the LLM uses find_restaurants first, it gets the ID.
        # Let's try a request that needs the ID explicitly for make_reservation.
        # First find:
        print("\nUser: Find Bukhara")
        response_b1 = stateful_processor.process_user_input("Find Bukhara")
        print(f"Bot : {response_b1['message']} (Status: {response_b1['status']})")
        print(f"History Length: {len(stateful_processor.get_conversation_history())}")

        # Now make reservation using ID (assuming ID del001 was returned or known)
        print("\nUser: Book Bukhara (del001) for 2 people on 2025-07-15 at 8:00 PM, Name: Raj Test, Contact: 12345")
        response_b2 = stateful_processor.process_user_input(
            "make_reservation restaurant_id=del001 party_size=2 date=2025-07-15 time=8:00 PM user_name='Raj Test' user_contact='12345'"
            # Using explicit command style here for testing tool directly via LLM; natural language preferred
            # A natural input would be: "Book Bukhara for 2 on July 15th at 8 PM. Name is Raj Test, phone 12345"
            # The LLM would then parse this and generate the tool call.
        )
        print(f"Bot : {response_b2['message']} (Status: {response_b2['status']})")
        print(f"History Length: {len(stateful_processor.get_conversation_history())}")

        print("\n--- Final Conversation History (Stateful) ---")
        # print(json.dumps(stateful_processor.get_conversation_history(), indent=2)) # Can be very verbose
        print(f"Total messages in history: {len(stateful_processor.get_conversation_history())}")
        print("------------------------------------")

    except (ValueError, RuntimeError) as e:
         print(f"\nInitialization failed for stateful test: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred during stateful test: {e}")