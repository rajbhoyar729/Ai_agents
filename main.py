import streamlit as st
import json
import logging
from typing import Dict, Any, List, Union, Optional

# --- Import custom modules ---
try:
    from agent_brain import AgentBrain
    from tools import AVAILABLE_TOOLS
except ImportError as e:
    st.error(f"Fatal Error: Could not import modules. Ensure correct paths. Details: {e}")
    st.stop()

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Page Configuration ---
st.set_page_config(
    page_title="FoodieSpot AI Assistant (Delhi)",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- Custom CSS ---
# (Keep your CSS markdown here)
st.markdown("""
<style>
    /* Dark Gradient Background */
    .stApp {
        background: linear-gradient(to bottom right, #232526, #414345); /* Dark grey gradient */
        color: #E0E0E0; /* Light grey text for readability */
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    /* --- Keep all other CSS rules --- */
    .stChatMessage { border-radius: 10px; padding: 0.8rem 1.1rem; margin-bottom: 0.6rem; box-shadow: 0 3px 5px rgba(0,0,0,0.2); max-width: 85%; border: 1px solid rgba(255, 255, 255, 0.1); }
    [data-testid="stChatMessage"]:has(div[data-testid="stChatMessageContent"][style*="flex-direction: row-reverse;"]) { background-color: #0b3d91; margin-left: auto; margin-right: 0; color: #FFFFFF; }
    [data-testid="stChatMessage"]:has(div[data-testid="stChatMessageContent"][style*="flex-direction: row-reverse;"]) div[data-testid="stChatMessageContent"] p { color: #FFFFFF; }
     [data-testid="stChatMessage"]:has(div[data-testid="stChatMessageContent"][style*="flex-direction: row;"]) { background-color: #3a3f44; margin-right: auto; margin-left: 0; color: #E5E5E5; }
     [data-testid="stChatMessage"]:has(div[data-testid="stChatMessageContent"][style*="flex-direction: row;"]) div[data-testid="stChatMessageContent"] p { color: #E5E5E5; }
    .tool-display { background-color: rgba(85, 85, 85, 0.7); color: #ccc; font-style: italic; font-size: 0.9em; padding: 0.5rem 0.8rem; border-radius: 5px; margin-top: 0.3rem; border: 1px dashed rgba(255, 255, 255, 0.2); word-wrap: break-word; }
    .tool-display strong { color: #ddd; }
    .tool-display pre { background-color: rgba(0,0,0,0.3); padding: 0.3rem; border-radius: 3px; color: #eee; white-space: pre-wrap; word-wrap: break-word; }
    .stChatInputContainer { background: linear-gradient(to top, #414345, #232526); border-top: 1px solid rgba(255, 255, 255, 0.15); padding: 1rem; position: sticky; bottom: 0; z-index: 10;}
    [data-testid="stChatInput"] > div { background-color: #2D2D2D; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.2); box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
     [data-testid="stChatInput"] textarea { background-color: transparent; color: #E0E0E0; }
    [data-testid="stChatInput"] textarea::placeholder { color: #888; }
     [data-testid="stChatInput"] button { border: none; background-color: #0b3d91; color: white; }
    .stHeadingContainer { text-align: center; color: #F5F5F5; margin-bottom: 1.5rem; padding-top: 1.5rem; }
    h1 { font-weight: 600; letter-spacing: -1px; color: #FFFFFF; }
    .stHeadingContainer p { color: #B0B0B0; }
    .stSpinner > div > div { border-top-color: #0b3d91 !important; border-right-color: transparent !important; border-bottom-color: transparent !important; border-left-color: transparent !important; }
    .stException { background-color: #5c1a1a; border-color: #d9534f; color: #f8d7da; }
    div[data-testid="stVerticalBlock"] { padding-bottom: 5rem; } /* Adjust if necessary */
</style>
""", unsafe_allow_html=True)

# --- App Header ---
st.markdown("<div class='stHeadingContainer'><h1>🤖 FoodieSpot AI Assistant (Delhi)</h1><p>Find restaurants and book tables with your AI helper!</p></div>", unsafe_allow_html=True)

# --- Initialize Agent Brain (ONCE per session) ---
if 'agent_brain' not in st.session_state:
    try:
        st.session_state.agent_brain = AgentBrain()
        logger.info("AgentBrain (Native Tool Calling) initialized and stored in session state.")
    except (ValueError, Exception) as e:
        logger.error(f"Fatal Error: Failed to initialize AgentBrain: {e}", exc_info=True)
        st.error(f"Could not initialize AI Agent. Check config. Error: {e}")
        st.stop()
agent_brain = st.session_state.agent_brain

# --- Initialize Chat History in Session State ---
if "messages" not in st.session_state:
    st.session_state.messages: List[Dict[str, Any]] = [
        {"role": "assistant", "content": "Welcome to FoodieSpot! I can help you find restaurants and make reservations in Delhi. How can I assist?"}
    ]

# --- Display Chat History ---
message_container = st.container()
with message_container:
    for message in st.session_state.messages:
        role = message.get("role")
        content = message.get("content")

        if role == "assistant":
            if content:
                with st.chat_message("assistant"): st.markdown(content)
        elif role == "user":
            with st.chat_message("user"): st.markdown(content)
        elif role == "tool":
             with st.chat_message("assistant", avatar="⚙️"):
                 tool_name = message.get("name", "unknown_tool")
                 tool_content_str = message.get("content", "{}")
                 try:
                     tool_content_dict = json.loads(tool_content_str)
                     is_error = tool_content_dict.get("status") == "error" or "error" in tool_content_dict
                     display_content = json.dumps(tool_content_dict, indent=2)
                 except json.JSONDecodeError:
                     is_error = False; display_content = tool_content_str
                 st.markdown(f"""<div class="tool-display {'tool-error' if is_error else ''}">"""
                             f"""<strong>Executed:</strong> <code>{tool_name}</code><br>"""
                             f"""<strong>Result:</strong> <pre>{display_content}</pre></div>""",
                             unsafe_allow_html=True)

# --- Handle User Input ---
if prompt := st.chat_input("Ask about Delhi restaurants..."):
    logger.info(f"User input: {prompt}")

    # 1. Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Start agent processing logic within the assistant's chat context
    with message_container:
        with st.chat_message("assistant"):
            current_spinner = st.spinner("Thinking...") # Define spinner before try
            try:
                # --- Agent Processing Loop ---
                max_turns = 5
                turn_count = 0
                while turn_count < max_turns:
                    turn_count += 1
                    logger.info(f"--- Agent Turn {turn_count} ---")

                    # Call AgentBrain with CURRENT history
                    response_type, response_data, raw_assistant_message = agent_brain.get_response(st.session_state.messages)
                    logger.info(f"Agent response type: {response_type}")

                    # Store raw assistant response (content or tool_calls)
                    if raw_assistant_message:
                        st.session_state.messages.append(raw_assistant_message)

                    # --- Process Response ---
                    if response_type == "error":
                        error_msg = f"🤖 Sorry, an error occurred: {response_data}"
                        st.error(error_msg) # Display error inside the assistant bubble
                        if not raw_assistant_message: # Add error to history if not captured
                            st.session_state.messages.append({"role": "assistant", "content": error_msg})
                        break # Exit loop

                    elif response_type == "text":
                        # Final text response
                        if response_data: st.markdown(response_data) # Display the text
                        else: st.markdown("...")
                        break # Exit loop, turn complete

                    elif response_type == "tool_calls":
                        # Execute tools
                        current_spinner.text = "Running tools..."
                        tool_messages_for_next_call = []
                        any_tool_error = False; error_details = ""

                        for tool_call in response_data:
                            tool_id = tool_call["id"]; tool_name = tool_call["tool_name"]; tool_args = tool_call["arguments"]
                            logger.info(f"Executing tool: {tool_name} (ID: {tool_id}) Args: {tool_args}")
                            if tool_name in AVAILABLE_TOOLS:
                                tool_function = AVAILABLE_TOOLS[tool_name]
                                try:
                                    tool_result = tool_function(**tool_args)
                                    tool_result_content = json.dumps(tool_result)
                                    logger.info(f"Tool '{tool_name}' (ID: {tool_id}) successful.")
                                    tool_messages_for_next_call.append({"role": "tool", "tool_call_id": tool_id, "name": tool_name, "content": tool_result_content})
                                except Exception as e:
                                    logger.exception(f"Tool '{tool_name}' error.", exc_info=True)
                                    error_msg = f"Tool {tool_name} Error: {e}"
                                    tool_messages_for_next_call.append({"role": "tool", "tool_call_id": tool_id, "name": tool_name, "content": json.dumps({"error": error_msg})})
                                    any_tool_error = True; error_details += f"{tool_name}: {error_msg}\n"
                            else:
                                logger.error(f"Tool '{tool_name}' not found.")
                                error_msg = "Tool function not found."
                                tool_messages_for_next_call.append({"role": "tool", "tool_call_id": tool_id, "name": tool_name, "content": json.dumps({"error": error_msg})})
                                any_tool_error = True; error_details += f"{tool_name}: {error_msg}\n"

                        # Add tool results to history BEFORE next call
                        st.session_state.messages.extend(tool_messages_for_next_call)

                        # Display tool results visually
                        for tool_msg in tool_messages_for_next_call:
                            tool_name_disp = tool_msg.get("name", "unknown_tool")
                            tool_content_str_disp = tool_msg.get("content", "{}")
                            try:
                                tool_content_dict_disp = json.loads(tool_content_str_disp); is_error_disp = tool_content_dict_disp.get("status") == "error" or "error" in tool_content_dict_disp; display_content_disp = json.dumps(tool_content_dict_disp, indent=2)
                            except json.JSONDecodeError: is_error_disp = False; display_content_disp = tool_content_str_disp
                            st.markdown(f"""<div class="tool-display {'tool-error' if is_error_disp else ''}">"""
                                        f"""<strong>⚙️ Executed:</strong> <code>{tool_name_disp}</code><br>"""
                                        f"""<strong>Result:</strong> <pre>{display_content_disp}</pre></div>""",
                                        unsafe_allow_html=True)

                        # Optional: Check if only errors occurred and break early
                        # if any_tool_error and not any('error' not in json.loads(m['content']) for m in tool_messages_for_next_call if 'content' in m):
                        #    error_summary = "Sorry, errors occurred using tools:\n" + error_details
                        #    st.error(error_summary)
                        #    st.session_state.messages.append({"role": "assistant", "content": error_summary})
                        #    break

                        # Continue loop for the second call to LLM
                        current_spinner.text = "Formulating response..."
                        continue # Go to next iteration of the while loop

                    elif response_type == "stop":
                        st.markdown("...")
                        if not raw_assistant_message or not raw_assistant_message.get('content'):
                            st.session_state.messages.append({"role": "assistant", "content": "..."})
                        break # Exit loop

                # --- End of while loop ---

            except Exception as main_loop_error: # Catch errors in the main processing loop
                 logger.exception("Error during agent processing loop.", exc_info=True)
                 st.error(f"An unexpected error occurred during processing: {main_loop_error}")
                 # Add error to history
                 st.session_state.messages.append({"role": "assistant", "content": f"System Error: {main_loop_error}"})

            finally:
                 # This block ALWAYS executes after the try block finishes or if an exception occurs
                 logger.info("Ensuring spinner is removed after processing.")
                 current_spinner.empty() # Safely remove the spinner


    # 3. Rerun at the VERY END to update the display with final results
    st.rerun()