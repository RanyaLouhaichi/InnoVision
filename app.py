import streamlit as st
import requests
import json
import uuid
from pathlib import Path
import os
from dotenv import load_dotenv
import base64
from streamlit_lottie import st_lottie
import time

# Load environment variables
load_dotenv()

# Configure Streamlit page
st.set_page_config(
    page_title="Assistant INNOVISION",
    page_icon="🤖",
    layout="centered"
)

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    
    /* Main container */
    .main {
        font-family: 'Inter', sans-serif;
    }
    
    /* Chat messages */
    .user-message {
        background-color: #F5F5F5;
        padding: 15px;
        border-radius: 15px;
        margin: 10px 0;
        max-width: 80%;
        align-self: flex-end;
    }
    
    .assistant-message {
        background-color: #E3F2FD;
        padding: 15px;
        border-radius: 15px;
        margin: 10px 0;
        max-width: 80%;
        align-self: flex-start;
    }
    
    /* Buttons */
    .stButton button {
        background-color: #0288D1;
        color: white;
        border-radius: 20px;
        padding: 10px 25px;
        border: none;
        font-weight: 500;
    }
    
    .stButton button:hover {
        background-color: #0277BD;
    }
    
    /* File uploader */
    .uploadedFile {
        border: 2px dashed #6A1B9A;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    
    /* Audio player */
    audio {
        width: 100%;
        margin: 10px 0;
    }
    
    /* Success message */
    .success-message {
        color: #43A047;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    /* Error message */
    .error-message {
        color: #E53935;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if 'current_step' not in st.session_state:
    st.session_state.current_step = None
if 'validated_documents' not in st.session_state:
    st.session_state.validated_documents = set()

# API Configuration
API_URL = os.getenv('API_URL', 'http://localhost:8000')

def send_message(text: str, tts: bool = False) -> dict:
    """Send message to API and return response"""
    try:
        response = requests.post(
            f"{API_URL}/api/v1/query/text",
            json={"text": text, "user_id": st.session_state.user_id},
            params={"tts": str(tts).lower()}
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Error communicating with the server: {str(e)}")
        return None

def play_audio_response(audio_url: str):
    """Play audio response from the assistant"""
    if audio_url:
        full_url = f"{API_URL}{audio_url}"
        st.audio(full_url, format='audio/mp3', start_time=0)

def show_success_animation():
    """Show success animation using Lottie"""
    with open('animations/success.json', 'r') as f:
        animation = json.load(f)
    st_lottie(animation, height=200, key="success")
    time.sleep(2)

def handle_file_upload(file_type: str):
    """Handle file upload and validation"""
    uploaded_file = st.file_uploader(f"Upload your {file_type}", type=['pdf', 'jpg', 'jpeg', 'png'])
    if uploaded_file:
        # Here you would implement the file validation logic
        # For now, we'll simulate success
        st.session_state.validated_documents.add(file_type)
        show_success_animation()
        return True
    return False

# Main chat interface
st.title("Assistant INNOVISION 🤖")

# Chat messages display
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if "audio_url" in message and message["audio_url"]:
            play_audio_response(message["audio_url"])

# User input
user_input = st.chat_input("Comment puis-je vous aider ?")

if user_input:
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)
    
    # Get assistant response
    response = send_message(user_input, tts=True)
    
    if response:
        # Add assistant response to chat
        st.session_state.messages.append({
            "role": "assistant",
            "content": response["response_text"],
            "audio_url": response.get("audio_response_url")
        })
        
        with st.chat_message("assistant"):
            st.write(response["response_text"])
            if response.get("audio_response_url"):
                play_audio_response(response["audio_response_url"])
            
            # Handle document requests
            if response.get("todo_list"):
                for doc in response["todo_list"]:
                    if doc not in st.session_state.validated_documents:
                        st.write(f"📄 Please upload your {doc}")
                        if handle_file_upload(doc):
                            st.success(f"{doc} validated successfully!")

# Reset button
if st.button("Recommencer"):
    st.session_state.clear()
    st.experimental_rerun()