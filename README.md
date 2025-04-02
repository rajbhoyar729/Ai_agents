
# FoodieSpot AI Reservation Assistant

**A modern, AI-powered restaurant reservation system for Delhi foodies.**

FoodieSpot AI Reservation Assistant is a modular, user-centric application designed to streamline restaurant bookings in Delhi, India. Powered by Llama 3.1-8B via Groq, it integrates natural language processing with a robust toolset to deliver a seamless dining reservation experience. This project aims to enhance customer satisfaction and boost restaurant bookings by 25% through personalized, efficient interactions.

---

## Table of Contents
- [Setup Instructions](#setup-instructions)
- [Prompt Engineering Approach](#prompt-engineering-approach)
- [Example Conversations](#example-conversations)
- [Business Strategy Summary](#business-strategy-summary)
- [License](#license)

---

## Setup Instructions

### Prerequisites
- **Python 3.8+**: Ensure Python is installed ([Download](https://www.python.org/downloads/)).
- **Git**: For cloning the repository ([Download](https://git-scm.com/downloads)).
- **Groq API Key**: Obtain from [Groq Console](https://console.groq.com) and set as an environment variable.

### Installation
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/rajbhoyar729/Ai_agents.git
   cd Ai_agents
   ```

2. **Set Up a Virtual Environment** (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *Note*: If `requirements.txt` isn’t there , install manually:
   ```bash
   pip install streamlit groq python-dotenv
   ```

4. **Configure Environment**:
   - Create a `.env` file in the root directory:
     ```plaintext
     GROQ_API_KEY=your_groq_api_key_here
     ```

5. **Run the Application**:
   ```bash
   streamlit run app.py
   ```
   - Open your browser at `http://localhost:8501` to access the chat UI.

### Project Structure
```
foodiespot-ai/
├── app.py          # Simple chat UI interfacing with main.py
├── main.py         # Central processing unit coordinating LLM and tools
├── agent_brain.py  # LLM interaction logic using Groq API
├── tools.py        # Toolset for restaurant operations
├── README.md       # Project documentation (this file)
└── .env            # Environment variables (not tracked)
```

---

## Prompt Engineering Approach

The prompt engineering for FoodieSpot’s `agent_brain.py` is designed to optimize Llama 3.1-8B’s performance via Groq, ensuring a user comfort-centric experience. Key aspects include:

1. **Role Definition**:
   - Prompt: `"You are FoodieBot, a friendly and helpful AI assistant for FoodieSpot in Delhi, India."`
   - Purpose: Establishes a warm, approachable persona focused on Delhi dining.

2. **Task Clarity**:
   - Prompt: `"Your goal is to make dining reservations easy, enjoyable, and personalized for users. **ONLY handle requests related to Delhi restaurants.**"`
   - Purpose: Constrains scope to avoid irrelevant responses, aligning with business goals.

3. **Conversational Guidance**:
   - Prompt: `"Speak conversationally and warmly... If the user’s request is unclear (e.g., missing date or party size), ask polite clarifying questions like: 'Could you tell me how many people and when you’d like to dine?'"`
   - Purpose: Encourages natural dialogue and proactive clarification, enhancing usability.

4. **Tool Integration**:
   - Prompt: Lists available tools (`find_restaurants`, `check_availability`, `make_reservation`, `get_restaurant_details`) with instructions: `"Use tools when needed, and always aim to delight the user with a smooth, comforting experience!"`
   - Purpose: Leverages Groq’s tool-calling capability, ensuring actionable responses over raw data.

5. **Output Style**:
   - Prompt: `"After using tools, weave results into natural responses (e.g., 'I found Bukhara with a table for 4 at 7 PM!') instead of raw data."`
   - Purpose: Prioritizes user-friendly output, avoiding technical jargon.

This approach balances precision (tool use) with personality (warmth), optimized for Llama 3.1-8B’s 8k context window and Groq’s fast inference.

---

## Example Conversations

Below are sample user journeys demonstrating the assistant’s capabilities:

### 1. Simple Restaurant Search
- **User**: "Find Italian restaurants for 4 tomorrow at 7 PM"
- **FoodieBot**: "Here are some great options: Olive, Big Chill. Want to check availability at one of these?"
- **Outcome**: User gets quick, relevant suggestions with a follow-up prompt.

### 2. Reservation Booking
- **User**: "Book a table for 6 at Bukhara on April 3rd at 8 PM"
- **FoodieBot**: "Reservation confirmed for you at Bukhara!\n- Party Size: 6\n- Date: 2025-04-03\n- Time: 8:00 PM\n- Confirmation ID: FS-XYZ12345\nWe’ll see you soon!"
- **Outcome**: Seamless booking with detailed confirmation, enhancing trust.

### 3. Clarification Needed
- **User**: "I want a table tonight"
- **FoodieBot**: "I’d love to help! Could you tell me how many people and what time you’d like to dine tonight?"
- **User**: "4 people at 6 PM"
- **FoodieBot**: "Got it! I found a table for 4 at The Spice Route at 6 PM. Should I book it for you?"
- **Outcome**: Handles ambiguity gracefully, guiding the user to a solution.

### 4. Error Handling
- **User**: "Book a table for 100 at Olive tomorrow"
- **FoodieBot**: "Sorry, Olive can’t accommodate 100 people (max capacity: 50). How about splitting into smaller groups or trying another spot?"
- **Outcome**: Provides a helpful fallback instead of a dead-end error.

These examples showcase the assistant’s ability to handle diverse requests, from straightforward searches to complex bookings, with a focus on user satisfaction.

---

## Business Strategy Summary

### Objective
Increase restaurant bookings in Delhi by 25% within 6 months by leveraging AI to simplify the reservation process and enhance customer engagement.

### Key Strategies
1. **User-Centric Design**:
   - Offer a friendly, intuitive chat interface to reduce booking friction.
   - Provide personalized suggestions (e.g., top restaurants, alternatives) to delight users.

2. **Operational Efficiency**:
   - Automate reservation tasks (search, availability, booking) using AI tools, reducing staff workload.
   - Integrate real-time data (via `tools.py`) for accurate availability checks.

3. **Revenue Growth**:
   - Upsell premium options (e.g., “Want a premium table with a view for an extra fee?”) during booking.
   - Target Delhi’s urban foodies (20-40) with a modern UI and fast responses.

4. **Scalability**:
   - Modular architecture (`app.py`, `main.py`, `agent_brain.py`, `tools.py`) allows easy feature additions (e.g., loyalty programs, multi-city expansion).
   - Use Groq’s scalable API for consistent performance under load.

### Metrics for Success
- **Booking Conversion Rate**: Target 25% increase from baseline.
- **User Satisfaction**: Aim for 4.5/5 average rating via post-booking feedback.
- **Response Time**: Maintain <2-second average latency for user queries.

This strategy positions FoodieSpot as a leader in AI-driven dining reservations, capitalizing on Delhi’s vibrant food scene and tech-savvy audience.

---

## License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details (create a `LICENSE` file if needed).

---

### Notes for Use
- Replace `https://github.com/yourusername/foodiespot-ai.git` with your actual repository URL once hosted.
- Add a `requirements.txt` file with `streamlit`, `groq`, and `python-dotenv` for easier setup.
- Ensure `.env` is added to `.gitignore` to protect your API key.

---

### Instructions to Use
1. **Create the File**:
   - Copy the above content into a new file named `README.md` in your project directory (`C:\Users\bhoya\Desktop\New folder\Ai_agents\`).
   - Use a text editor like VS Code, Notepad++, or any IDE to save it.

2. **Customize**:
   - Update the GitHub URL (`https://github.com/yourusername/foodiespot-ai.git`) with your actual repository link once you host it online.
   - If you add a `requirements.txt` or `LICENSE` file, ensure they’re referenced correctly.

3. **View**:
   - Open `README.md` in a Markdown viewer (e.g., GitHub, VS Code with Markdown preview) to see the formatted version.

---

### Additional Suggestions
- **Requirements File**: Create a `requirements.txt` with:
  ```
  streamlit==1.20.0
  groq==0.4.0
  python-dotenv==1.0.0
  ```
Then update the README’s install step accordingly.
- **License File**: Add a basic MIT License file if desired:
   ```
   MIT License

  Copyright (c) 2025 [Raj Bhoyar]

  Permission is hereby granted, free of charge, to any person obtaining a copy...
  
  ```

