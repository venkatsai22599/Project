import streamlit as st
from backend import chatbot
from langchain_core.messages import HumanMessage, AIMessage
import uuid
import re

# ========================== utils ===================================

def generate_thread_id():
    return uuid.uuid4()

def summarize_first_line(text: str, max_len: int = 40) -> str:
    """Create a short, clean title from the first user message."""
    # take first sentence/line
    first = re.split(r'[.\n\r!?]+', text.strip(), maxsplit=1)[0]
    first = re.sub(r'\s+', ' ', first)  # collapse spaces
    if not first:
        return "New chat"
    return (first[:max_len] + "…") if len(first) > max_len else first

def add_thread(thread_id):
    # keep list of ids for order, and a title map for labels
    if 'chat_threads' not in st.session_state:
        st.session_state['chat_threads'] = []
    if 'thread_titles' not in st.session_state:
        st.session_state['thread_titles'] = {}

    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)
    st.session_state['thread_titles'].setdefault(thread_id, "New chat")

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    st.session_state['message_history'] = []
    add_thread(thread_id)

def load_conversation(thread_id):
    state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
    return state.values.get('messages', [])

# ========================== session setup ============================

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = []

if 'thread_titles' not in st.session_state:
    st.session_state['thread_titles'] = {}

add_thread(st.session_state['thread_id'])

# ========================== sidebar =================================

st.sidebar.title('Chatbot')

if st.sidebar.button('New Chat', use_container_width=True):
    reset_chat()

st.sidebar.header('My Conversations')

# show newest first
for tid in st.session_state['chat_threads'][::-1]:
    title = st.session_state['thread_titles'].get(tid, str(tid))  # fallback if missing
    # unique key so buttons don't clash
    if st.sidebar.button(title, key=f"thread-btn-{tid}", use_container_width=True):
        st.session_state['thread_id'] = tid
        messages = load_conversation(tid)

        temp_messages = []
        for msg in messages:
            role = 'user' if isinstance(msg, HumanMessage) else 'assistant'
            temp_messages.append({'role': role, 'content': msg.content})

        st.session_state['message_history'] = temp_messages

# ========================== main UI =================================

# render conversation
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])

user_input = st.chat_input('Type here')

if user_input:
    # append user message
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.text(user_input)

    # if this is the first user message for this thread, set a title
    tid = st.session_state['thread_id']
    if st.session_state['thread_titles'].get(tid, "New chat") == "New chat":
        st.session_state['thread_titles'][tid] = summarize_first_line(user_input)

    CONFIG = {'configurable': {'thread_id': tid}}

    with st.chat_message("assistant"):
        def ai_only_stream():
            for message_chunk, metadata in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode="messages"
            ):
                if isinstance(message_chunk, AIMessage):
                    # yield only assistant tokens
                    yield message_chunk.content

        ai_message = st.write_stream(ai_only_stream())

    st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})
