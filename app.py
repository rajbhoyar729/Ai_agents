# FILE: app.py
import streamlit as st
import logging
from main import MainProcessor  # Import the central processor

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Page Configuration ---
st.set_page_config(
    page_title="FoodieSpot AI Assistant",
    page_icon="🍽️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- Custom CSS (Optional - for minor tweaks if needed) ---
# st.chat_message provides good defaults, so extensive CSS might not be necessary
CUSTOM_CSS = """
<style>
    /* Target the Streamlit chat container for potential height limits */
    .stChatFloatingInputContainer {
        bottom: 0rem; /* Adjust if input overlaps content */
    }
    /* You can add more specific styling here if desired */
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --- State Management ---
def initialize_state():
    """Initializes session state variables if they don't exist."""
    # Initialize the main processor ONCE per session
    if 'main_processor' not in st.session_state:
        try:
            st.session_state.main_processor = MainProcessor()
            logger.info("MainProcessor initialized and stored in session state.")
        except Exception as e:
            logger.error(f"Failed to initialize MainProcessor: {e}", exc_info=True)
            st.error(f"Critical Error: Could not initialize the AI assistant. Please check logs or environment variables (like GROQ_API_KEY). Error: {e}", icon="🚨")
            # Halt execution for this user if processor fails
            st.stop()

    # Initialize chat history for display
    if 'messages' not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Namaste! 🙏 I'm FoodieBot. How can I help you find the perfect dining spot in Delhi today?"}
        ]
        logger.info("Chat history initialized.")

    # Sync processor's history if it exists and display history is minimal (optional refinement)
    # This ensures if the processor had some initial state/history, it could be reflected.
    # However, with the current setup, the processor starts fresh too.
    # processor = st.session_state.main_processor
    # if processor and len(st.session_state.messages) == 1 and processor.get_conversation_history():
    #     # Logic to potentially merge histories if needed, complex and often not required
    #     pass

# --- UI Rendering ---
def render_chat_interface():
    """Renders the main chat UI elements."""
    st.title("🍽️ FoodieSpot AI Assistant")
    st.caption("Your friendly guide to dining in Delhi")

    # Display existing chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"]) # Use markdown for potential formatting

    # Main chat input
    if prompt := st.chat_input("Ask me about Delhi restaurants... (e.g., 'Find North Indian places in CP')"):
        logger.info(f"User input received: {prompt}")

        # Add user message to display state immediately
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Process the input using the persistent MainProcessor
        processor: MainProcessor = st.session_state.main_processor
        if not processor:
             st.error("Assistant is not available due to an earlier initialization error.", icon="🚨")
             st.stop()

        # Show a thinking indicator
        with st.chat_message("assistant"):
            with st.spinner("FoodieBot is thinking..."):
                try:
                    logger.debug(f"Sending to processor. Current history length for processor: {len(processor.get_conversation_history())}")
                    response = processor.process_user_input(prompt) # main.py handles its internal history now
                    logger.debug(f"Received response from processor: status={response['status']}")

                    if response["status"] == "success":
                        bot_message = response["message"]
                        st.markdown(bot_message)
                    else:
                        # Display error message clearly but as a bot response
                        error_message = f"😥 Oops! {response['message']}"
                        st.warning(error_message) # Use warning/error styling within the chat
                        bot_message = error_message # Store the error message for history

                    # Add bot response to display state
                    st.session_state.messages.append({"role": "assistant", "content": bot_message})

                except Exception as e:
                    logger.error(f"Error processing user input in app.py: {e}", exc_info=True)
                    error_text = "Sorry, I encountered an unexpected technical glitch. Please try asking again differently or refresh the page."
                    st.error(error_text, icon="🔥")
                    st.session_state.messages.append({"role": "assistant", "content": error_text})

        # No explicit st.rerun() needed with st.chat_input, it triggers automatically.

# --- Main Execution ---
if __name__ == "__main__":
    initialize_state()
    render_chat_interface()