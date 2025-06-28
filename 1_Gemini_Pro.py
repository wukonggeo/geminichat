import google.generativeai as genai
import streamlit as st
import time
import random
from utils import SAFETY_SETTTINGS


st.set_page_config(
    page_title="Chat To Gemini",
    page_icon="🔥",
    menu_items={
        'About': "# Make By Test"
    }
)

login_key = 'Gemini123'

# 初始化参数
if 'is_authenticated' not in st.session_state:
    st.session_state.is_authenticated = False
if 'history' not in st.session_state:
    st.session_state.history = []
if 'app_key' not in st.session_state:
    st.session_state.app_key = None

# 检查是否已经登录
if not st.session_state.is_authenticated: 
    # 要求用户输入密码
    password_input = st.text_input("Please enter the login Key", type='password', key='login_key_input')
    
    # 提交按钮，用于触发密码验证
    if st.button('Submit'):
        if password_input == login_key:
            st.session_state.is_authenticated = True
            st.write("Password is correct, welcome to the app!")
            # 刷新页面，重新加载程序
            st.rerun()
        else:
            st.error("Password is incorrect, access denied.")
            # 刷新页面
            # st.experimental_rerun()
            # 清除密码输入框的值，以便用户重新输入
            # st.text_input("Please enter the login Key", type='password', key=f'login_key_input_{random.randint(0, 1000)}', value='')

else:
    st.title("Chat To Gemini")
    st.caption("a chatbot, powered by google gemini pro.")
    
    if "app_key" not in st.session_state or st.session_state.app_key is None:
        app_key = st.text_input("Your Gemini App Key", type='password', key='gemini_key_input')
        # app_key = st.secrets["Gemini_Key"]
        if app_key:
            st.session_state.app_key = app_key
            st.rerun()
    try:
        genai.configure(api_key = st.session_state.app_key)
    except AttributeError as e:
        st.warning("Please Put Your Gemini App Key First.")
    # gemini-1.5-pro-latest gemini-2.0-flash-thinking-exp-01-21 gemini-2.0-flash-thinking-exp
    model = genai.GenerativeModel('gemini-2.5-pro')
    chat = model.start_chat(history = st.session_state.history)
    
    with st.sidebar:
        if st.button("Clear Chat Window", use_container_width = True, type="primary"):
            st.session_state.history = []
            st.rerun()
        
    for message in chat.history:
        role = "assistant" if message.role == "model" else message.role
        with st.chat_message(role):
            st.markdown(message.parts[0].text)
    
    if "app_key" in st.session_state:
        if prompt := st.chat_input(""):
            prompt = prompt.replace('\n', '  \n')
            with st.chat_message("user"):
                st.markdown(prompt)
    
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                message_placeholder.markdown("Thinking...")
                try:
                    full_response = ""
                    # safety_settings = SAFETY_SETTTINGS
                    for chunk in chat.send_message(prompt, stream=True):
                        # 增加等待时间，减少报错
                        time.sleep(0.3)
                        word_count = 0
                        random_int = random.randint(5, 10)
                        for word in chunk.text:
                            full_response += word
                            word_count += 1
                            if word_count == random_int:
                                time.sleep(0.05)
                                message_placeholder.markdown(full_response + "_")
                                word_count = 0
                                random_int = random.randint(5, 10)
                    message_placeholder.markdown(full_response)
                except genai.types.generation_types.BlockedPromptException as e:
                    st.exception(e)
                except Exception as e:
                    st.exception(e)
                st.session_state.history = chat.history
