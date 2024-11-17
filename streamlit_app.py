import streamlit as st
from openai import OpenAI
import time

# Function to get API key from the URL
def get_api_key_from_url():
    query_params = st.query_params
    return query_params.get("api_key", [None])[0]

# Get the API key from the URL
api_key = get_api_key_from_url()

# Notify the user
if api_key:
    st.sidebar.success("API key loaded from URL."+api_key)
else:
    st.sidebar.warning("No API key found in the URL. Please provide one or enter it manually.")

# Input field for the API key (fallback if not in URL or sanitized)
api_key = st.text_input(
    "Enter your OpenAI API Key:",
    value=api_key if api_key else "",
    type="password",  # Hide the key when typing
)

# Initialize OpenAI client
if api_key:
    try:
        client = OpenAI(api_key=api_key)
        st.success("API key successfully loaded!")

        # Load the Assistant
        try:
            assistant_id = "asst_FRTeSfXQxwiJAkYZpAXfagCK"  # Replace with your actual assistant ID
            assistant = client.beta.assistants.retrieve(assistant_id)
            st.sidebar.success(f"Assistant '{assistant.name}' loaded successfully!")
        except Exception as e:
            st.error(f"Failed to load Assistant: {e}")

    except Exception as e:
        st.error(f"Failed to initialize OpenAI client: {e}")
else:
    st.error("Please provide a valid OpenAI API key.")

# Chat UI (if API key and Assistant are available)
if api_key and "assistant" in locals():
    st.title("Chat with HR Assistant")
    st.sidebar.title("Instructions")
    st.sidebar.info(
        "Start a conversation with your Assistant! Your conversation history will persist during this session."
    )

    # Initialize session state for conversation
    if "conversation" not in st.session_state:
        st.session_state.conversation = []

    # Form to allow submission with "Enter" key
    with st.form(key="chat_form", clear_on_submit=True):
        user_message = st.text_input("Your Message:", placeholder="Ask the Assistant something...")
        submit_button = st.form_submit_button("Send")

    # Submit button logic
    if submit_button and user_message:
        try:
            # Create a thread for the conversation (if not already created)
            if "thread" not in st.session_state:
                st.session_state.thread = client.beta.threads.create()
                st.sidebar.success(f"Thread created successfully! Thread ID ")
            else:
                # If thread already exists, print thread details
                thread_details = client.beta.threads.retrieve(st.session_state.thread.id)

            # Add user message to the thread
            message = client.beta.threads.messages.create(
                thread_id=st.session_state.thread.id,
                role="user",
                content=user_message
            )
            
            st.session_state.conversation.append({"role": "user", "content": user_message})
            st.sidebar.info(f"User message added: {user_message}")

            # Display "Waiting..." while the Assistant is processing
            st.write("**Waiting for Assistant's response...**")
            st.spinner("Assistant is thinking...")

            # Run the Assistant to generate a response
            run_response = client.beta.threads.runs.create_and_poll(
                thread_id=st.session_state.thread.id,
                assistant_id=assistant_id,
                instructions="Please address HR issues or Questions of the User"
            )

            # After the run is complete, fetch the assistant's response
            if run_response.status == 'completed':
                # Fetch the assistant's messages
                messages = client.beta.threads.messages.list(
                    thread_id=st.session_state.thread.id
                )

                # Get the Assistant's latest response from the list of messages
                if messages.data:
                    # Access the first TextContentBlock in the content
                    assistant_message = messages.data[0].content[0].text.value
                    
                    st.session_state.conversation.append({"role": "assistant", "content": assistant_message})
                    st.sidebar.success("Assistant response received.")
                else:
                    st.error("No response from Assistant.")
            else:
                st.error(f"Run status: {run_response.status}")

        except Exception as e:
            st.error(f"Error interacting with Assistant: {e}")

    # Display conversation history (latest message at the top)
    st.subheader("Conversation")
    for message in reversed(st.session_state.conversation):  # Reversed to show latest message first
        if message["role"] == "user":
            # Style for user messages
            st.markdown(f'<div style="background-color: #E0F7FA; padding: 10px; border-radius: 10px; margin-bottom: 10px;">**You:** {message["content"]}</div>', unsafe_allow_html=True)
        else:
            # Style for assistant messages
            st.markdown(f'<div style="background-color: #F1F8E9; padding: 10px; border-radius: 10px; margin-bottom: 10px;">**Assistant:** {message["content"]}</div>', unsafe_allow_html=True)
