import streamlit as st
import urllib.parse
from openai import OpenAI
import os
from PyPDF2 import PdfReader

# Function to get API key from the URL
def get_api_key_from_url():
    query_params = st.experimental_get_query_params()
    api_key = query_params.get("api_key", [None])[0]
    if api_key:
        api_key = urllib.parse.unquote(api_key)
    return api_key

# Get API key
api_key = get_api_key_from_url()

if api_key:
    st.sidebar.success("API key loaded from URL.")
else:
    st.sidebar.warning("No API key found in the URL. Please provide one or enter it manually.")

# Input field for the API key
api_key = st.text_input("Enter your OpenAI API Key:", value=api_key if api_key else "", type="password")

# Initialize OpenAI client
if api_key:
    try:
        client = OpenAI(api_key=api_key)
        st.success("API key successfully loaded!")

        # Load the Assistant
        assistant_id = "asst_FRTeSfXQxwiJAkYZpAXfagCK"  # Replace with your assistant ID
        try:
            assistant = client.beta.assistants.retrieve(assistant_id)
            st.sidebar.success(f"Assistant '{assistant.name}' loaded successfully!")
        except Exception as e:
            st.error(f"Failed to load Assistant: {e}")
            assistant = None
    except Exception as e:
        st.error(f"Failed to initialize OpenAI client: {e}")
        assistant = None
else:
    st.error("Please provide a valid OpenAI API key.")
    assistant = None

# Tabs for functionalities
tab1, tab2, tab3 = st.tabs(["Chat Assistant", "File Management", "Modify System Prompt"])

# Chat Assistant Tab
with tab1:
    if api_key and assistant:
        st.title("Chat with HR Assistant")
        st.sidebar.info("Start a conversation with your Assistant!")

        # Initialize session state for conversation
        if "conversation" not in st.session_state:
            st.session_state.conversation = []

        # Chat Input Form
        with st.form(key="chat_form", clear_on_submit=True):
            user_message = st.text_input("Your Message:", placeholder="Ask the Assistant something...")
            submit_button = st.form_submit_button("Send")

        if submit_button and user_message:
            try:
                if "thread" not in st.session_state:
                    st.session_state.thread = client.beta.threads.create()
                    st.sidebar.success(f"Thread created successfully!")
                else:
                    thread_details = client.beta.threads.retrieve(st.session_state.thread.id)

                # Add user message
                client.beta.threads.messages.create(
                    thread_id=st.session_state.thread.id, role="user", content=user_message
                )
                st.session_state.conversation.append({"role": "user", "content": user_message})

                # Wait for assistant's response
                st.write("**Waiting for Assistant's response...**")
                with st.spinner("Assistant is thinking..."):
                    run_response = client.beta.threads.runs.create_and_poll(
                        thread_id=st.session_state.thread.id,
                        assistant_id=assistant_id,
                        instructions="Please address HR issues or Questions of the User"
                    )

                if run_response.status == "completed":
                    messages = client.beta.threads.messages.list(thread_id=st.session_state.thread.id)
                if messages.data:
                    # Extract the assistant's message content (value of the text)
                    assistant_message_block = messages.data[0].content
                    if isinstance(assistant_message_block, dict) and "value" in assistant_message_block:
                        assistant_message = assistant_message_block["value"]
                        st.session_state.conversation.append({"role": "assistant", "content": assistant_message})
                    else:
                        st.error("Unexpected response format from Assistant.")

                else:
                    st.error(f"Run status: {run_response.status}")
            except Exception as e:
                st.error(f"Error interacting with Assistant: {e}")

        # Display conversation
        st.subheader("Conversation")
        for message in reversed(st.session_state.conversation):
            role = "You" if message["role"] == "user" else "Assistant"
            bg_color = "#E0F7FA" if message["role"] == "user" else "#F1F8E9"
            st.markdown(
                f'<div style="background-color: {bg_color}; padding: 10px; border-radius: 10px; margin-bottom: 10px;">'
                f'**{role}:** {message["content"]}</div>',
                unsafe_allow_html=True,
            )

# File Management Tab
with tab2:
    st.title("File Management")
    st.sidebar.info("Upload files to be used with the Assistant.")

    uploaded_file = st.file_uploader("Upload a File", type=["txt", "csv", "json", "pdf"])
    if uploaded_file:
        temp_path = f"temp_{uploaded_file.name}"
        try:
            if uploaded_file.type == "application/pdf":
                pdf_reader = PdfReader(uploaded_file)
                pdf_text = "".join(page.extract_text() for page in pdf_reader.pages)
                with open(temp_path, "w") as temp_file:
                    temp_file.write(pdf_text)
            else:
                with open(temp_path, "wb") as temp_file:
                    temp_file.write(uploaded_file.getbuffer())

            with open(temp_path, "rb") as file:
                file_response = client.files.create(file=file, purpose="fine-tune")
                st.success(f"File '{uploaded_file.name}' uploaded successfully!")
        except Exception as e:
            st.error(f"Failed to upload file: {e}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # List uploaded files
    st.subheader("Uploaded Files")
    try:
        files = client.files.list()
        if files.get("data"):
            for file in files["data"]:
                st.write(f"File Name: {file['filename']}, ID: {file['id']}")
        else:
            st.info("No files uploaded yet.")
    except Exception as e:
        st.error(f"Failed to fetch files: {e}")

# Modify System Prompt Tab
# Modify System Prompt tab
with tab3:
    st.title("Modify System Prompt")

    if assistant:
        # Retrieve current system prompt
        current_prompt = assistant.instructions or "No instructions found."
        st.text_area("Current System Prompt", value=current_prompt, height=200, key="current_prompt")

        # Text area for new prompt
        new_prompt = st.text_area("New System Prompt", height=200, key="new_prompt")

        # Update the system prompt
        if st.button("Update System Prompt"):
            try:
                # Update the assistant with new instructions
                updated_assistant = client.beta.assistants.update(
                    assistant_id=assistant.id,  # Use the ID of the assistant
                    instructions=new_prompt,  # Update the instructions
                    name=assistant.name,  # Retain the current name
                    model=assistant.model,  # Retain the current model
                    tools=assistant.tools,  # Retain existing tools
                    temperature=assistant.temperature,  # Retain temperature
                    top_p=assistant.top_p,  # Retain top_p value
                    response_format=assistant.response_format,  # Retain response format
                )

                # Confirm update
                st.success("System Prompt updated successfully!")
                st.info(f"New instructions: {updated_assistant.instructions}")
            except Exception as e:
                st.error(f"Failed to update System Prompt: {e}")