import streamlit as st
from openai import OpenAI

# Function to get API key from the URL
def get_api_key_from_url():
    query_params = st.query_params
    return query_params.get("api_key", [None])[0]

# Function to redirect to a sanitized URL
def sanitize_url():
    # Clear all query parameters to sanitize the URL
    st.experimental_set_query_params()

# Get the API key from the URL
api_key = get_api_key_from_url()

# Notify the user and sanitize the URL if the key is provided
if api_key:
    st.sidebar.success("API key loaded from URL. Redirecting to sanitized URL...")
    sanitize_url()
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
    st.title("Chat with OpenAI Assistant")
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
                st.sidebar.success(f"Thread created successfully! Thread ID: {st.session_state.thread.id}")
            else:
                # If thread already exists, print thread details
                thread_details = client.beta.threads.retrieve(st.session_state.thread.id)
                st.sidebar.info(f"Thread already exists! Thread ID: {st.session_state.thread.id}")
                st.sidebar.info(f"Thread Details: {thread_details}")

            # Add user message to the thread
            message = client.beta.threads.messages.create(
                thread_id=st.session_state.thread.id,
                role="user",
                content=user_message
            )
            
            st.session_state.conversation.append({"role": "user", "content": user_message})
            st.sidebar.info(f"User message added: {user_message}")

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
                    #print(messages.data[0])
                    assistant_message = messages.data[0].content[0].text.value  # Accessing the first TextContentBlock in the content
                    
                    st.session_state.conversation.append({"role": "assistant", "content": assistant_message})
                    st.sidebar.success("Assistant response received.")
                else:
                    st.error("No response from Assistant.")
            else:
                st.error(f"Run status: {run_response.status}")

        except Exception as e:
            st.error(f"Error interacting with Assistant: {e}")

    # Display conversation history
    st.subheader("Conversation")
    for message in st.session_state.conversation:
        if message["role"] == "user":
            st.write(f"**You:** {message['content']}")
        else:
            st.write(f"**Assistant:** {message['content']}")
