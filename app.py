import streamlit as st
import logging
from typing import Dict, List
from main import process_input, MainProcessor  # Import from main.py

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Page Configuration
st.set_page_config(
    page_title="FoodieSpot Chat",
    page_icon="🍽️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for Simple, Clean Design
CUSTOM_CSS = """
<style>
    .header {
        background-color: #4CAF50;  /* Simple green for a food theme */
        color: white;
        padding: 1rem;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .chat-container {
        max-height: 500px;
        overflow-y: auto;
        padding: 1rem;
        background-color: #f9f9f9;  /* Light gray for contrast */
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #4CAF50;
        color: white;
        padding: 0.8rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        text-align: right;
        max-width: 80%;
        margin-left: auto;
    }
    .bot-message {
        background-color: #ffffff;
        color: #333;
        padding: 0.8rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        text-align: left;
        max-width: 80%;
        border: 1px solid #ddd;
    }
    .input-container {
        display: flex;
        gap: 0.5rem;
        padding: 1rem;
    }
    .stTextInput > div > div > input {
        border-radius: 8px;
        padding: 0.5rem;
    }
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
    }
    ::-webkit-scrollbar {
        width: 6px;
    }
    ::-webkit-scrollbar-thumb {
        background: #888;
        border-radius: 3px;
    }
</style>
"""

def initialize_session_state(processor: MainProcessor):
    """Initialize session state and sync with MainProcessor."""
    if 'messages' not in st.session_state:
        st.session_state.messages = [
            {"role": "bot", "content": "Hello! How can I assist you with your dining today?"}
        ]
    # Sync with main.py’s conversation history on first load
    if len(st.session_state.messages) == 1:  # Only initial message
        st.session_state.messages.extend(
            [{"role": msg["role"], "content": msg["content"]} for msg in processor.get_conversation_history()]
        )

def display_header():
    """Render the chat header."""
    st.markdown(
        '<div class="header">🍽️ FoodieSpot Chat</div>',
        unsafe_allow_html=True
    )

def display_chat():
    """Render the conversation history."""
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(
                f'<div class="user-message">{message["content"]}</div>',
                unsafe_allow_html=True
            )
        else:  # bot or system (treated as bot here for simplicity)
            st.markdown(
                f'<div class="bot-message">{message["content"]}</div>',
                unsafe_allow_html=True
            )
    st.markdown('</div>', unsafe_allow_html=True)

def handle_input(processor: MainProcessor):
    """Process user input and interact with main.py."""
    with st.form(key="chat_form", clear_on_submit=True):
        col1, col2 = st.columns([4, 1])
        with col1:
            user_input = st.text_input("Type your message...", key="chat_input", label_visibility="collapsed")
        with col2:
            submit_button = st.form_submit_button("Send")

        if submit_button and user_input:
            logger.info(f"User input: {user_input}")
            st.session_state.messages.append({"role": "user", "content": user_input})

            # Process via main.py
            response = processor.process_user_input(user_input)
            if response["status"] == "success":
                st.session_state.messages.append({"role": "bot", "content": response["message"]})
            else:
                st.session_state.messages.append({"role": "bot", "content": f"Error: {response['message']}"})
            
            st.rerun()

def main():
    """Main function to run the chat UI."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    processor = MainProcessor()  # Persistent instance for history sync
    initialize_session_state(processor)
    display_header()
    display_chat()
    handle_input(processor)

if __name__ == "__main__":
    main()