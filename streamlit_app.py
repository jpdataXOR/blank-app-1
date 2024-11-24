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
                     # Extract the assistant's message content (value of the text)
                        assistant_message_block = messages.data[0].content[0].text.value
                        st.session_state.conversation.append({"role": "assistant", "content": assistant_message_block})
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
    st.title("Vector Store Management")
    st.sidebar.info("Manage vector stores and associated files.")

    # List all vector stores
    st.subheader("List of Vector Stores")
    try:
        # Fetch vector stores
        vector_stores = client.beta.vector_stores.list()

        # Check if the 'data' attribute contains stores
        if vector_stores.data and isinstance(vector_stores.data, list):
            st.subheader("Vector Stores")
            for store in vector_stores.data:
                st.write(f"**Name:** {store.name}")
                st.write(f"**ID:** {store.id}")
                st.write(f"**Created At:** {store.created_at}")
                st.write(f"**Total Files:** {store.file_counts.total}")
                st.write("---")
        else:
            st.info("No vector stores found.")
    except Exception as e:
        st.error(f"Failed to fetch vector stores: {e}")


    # Select a vector store to manage files
    vector_store_id = st.text_input("Enter Vector Store ID to Manage Files:")
    if vector_store_id:
        st.subheader(f"Files in Vector Store: {vector_store_id}")
    # Fetch files in a vector store
        try:
            vector_store_files = client.beta.vector_stores.files.list(vector_store_id=vector_store_id)

            # Check if the 'data' attribute contains files
            if vector_store_files.data and isinstance(vector_store_files.data, list):
                st.subheader(f"Files in Vector Store {vector_store_id}")
                for file in vector_store_files.data:
                    st.write(f"**File ID:** {file.id}")
                    st.write(f"**Created At:** {file.created_at}")
                    st.write(f"**Vector Store ID:** {file.vector_store_id}")
                    st.write("---")
            else:
                st.info("No files found in this vector store.")
        except Exception as e:
            st.error(f"Failed to fetch files in vector store {vector_store_id}: {e}")

            # List files in the selected vector store
            vector_store_files = client.beta.vector_stores.files.list(vector_store_id=vector_store_id)
            if vector_store_files.data:
                for file in vector_store_files.data:
                    st.write(f"**File ID:** {file.id}, **Created At:** {file.created_at}")
            else:
                st.info("No files found in this vector store.")
        except Exception as e:
            st.error(f"Failed to fetch files in vector store {vector_store_id}: {e}")

        # Add new files to the vector store
        st.subheader("Add Files to Vector Store")
        uploaded_files = st.file_uploader("Upload Files to Add to Vector Store", type=["txt", "csv", "json", "pdf"], accept_multiple_files=True)
        if uploaded_files:
            file_streams = []
            for uploaded_file in uploaded_files:
                temp_path = f"temp_{uploaded_file.name}"
                try:
                    # Handle PDF separately (convert to text)
                    if uploaded_file.type == "application/pdf":
                        pdf_reader = PdfReader(uploaded_file)
                        pdf_text = "".join(page.extract_text() for page in pdf_reader.pages)
                        with open(temp_path, "w") as temp_file:
                            temp_file.write(pdf_text)
                    else:
                        # Save other file types as binary
                        with open(temp_path, "wb") as temp_file:
                            temp_file.write(uploaded_file.getbuffer())
                    
                    file_streams.append(open(temp_path, "rb"))
                except Exception as e:
                    st.error(f"Failed to process file {uploaded_file.name}: {e}")

            # Upload files and add to vector store
            if st.button("Upload and Add Files to Vector Store"):
                try:
                    file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
                        vector_store_id=vector_store_id, files=file_streams
                    )
                    st.success(f"Files successfully added to vector store {vector_store_id}.")
                    st.write(f"Batch Status: {file_batch.status}, File Counts: {file_batch.file_counts}")
                except Exception as e:
                    st.error(f"Failed to add files to vector store {vector_store_id}: {e}")
                finally:
                    # Close and clean up temporary file streams
                    for stream in file_streams:
                        stream.close()
                    for uploaded_file in uploaded_files:
                        temp_path = f"temp_{uploaded_file.name}"
                        if os.path.exists(temp_path):
                            os.remove(temp_path)

    # Update assistant to use vector store
    st.subheader("Associate Vector Store with Assistant")
    assistant_id = st.text_input("Enter Assistant ID to Associate Vector Store:")
    if assistant_id and vector_store_id:
        if st.button(f"Associate Vector Store {vector_store_id} with Assistant {assistant_id}"):
            try:
                updated_assistant = client.beta.assistants.update(
                    assistant_id=assistant_id,
                    tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}}
                )
                st.success(f"Vector store {vector_store_id} successfully associated with assistant {updated_assistant.name}.")
            except Exception as e:
                st.error(f"Failed to associate vector store {vector_store_id} with assistant: {e}")

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