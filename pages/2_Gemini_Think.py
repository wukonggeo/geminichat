from PIL import Image
import google.generativeai as genai
import streamlit as st
import time
import random
from utils import SAFETY_SETTTINGS

st.set_page_config(
    page_title="Chat To XYthing",
    page_icon="🔥",
    menu_items={
        'About': "# Test Demo"
    }
)
st.title('Upload Image And Ask')
model_options = {
    'gemini-2.0-pro-exp-02-05': "Pro",
    'gemini-2.0-flash': "Flash",
    'gemini-2.0-flash-exp': "Vison",
    'gemini-2.0-flash-thinking-exp-01-21': "Think",
    "gemini-2.5-pro-exp-03-25":"Think-PRO"
    }
default_index = list(model_options.keys()).index('gemini-2.0-flash')

if "app_key" not in st.session_state:
    app_key = st.text_input("Your Gemini App Key", type='password')
    if app_key:
        st.session_state.app_key = app_key

with st.sidebar:
    if st.button("Clear Chat Window", use_container_width = True, type="primary"):
        st.session_state.history_pic  = []
        st.rerun()
    selected_model = st.selectbox(
        "Select Model",
        options=list(model_options.keys()),
        format_func=lambda x: model_options[x],  #显示的名称
        index=default_index
        )
try:
    genai.configure(api_key = st.session_state.app_key)
    # gemini-1.5-flash gemini-2.0-flash
    model = genai.GenerativeModel(selected_model)
except AttributeError as e:
    st.warning("Please Put Your Gemini App Key First.")


def show_message(prompt, loading_str, image=None):
    model_chat = model.start_chat(history = st.session_state.history_pic)
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown(loading_str)
        full_response = ""
        try:
            if image:
                prompt = [prompt, image]
            for chunk in model_chat.send_message(prompt, stream = True, safety_settings = SAFETY_SETTTINGS):                   
                word_count = 0
                random_int = random.randint(10, 20)
                for word in chunk.text:
                    full_response += word
                    word_count += 1
                    if word_count == random_int:
                        time.sleep(0.05)
                        message_placeholder.markdown(full_response + "_")
                        word_count = 0
                        random_int = random.randint(10, 20)
        except genai.types.generation_types.BlockedPromptException as e:
            st.exception(e)
        except Exception as e:
            st.exception(e)
        message_placeholder.markdown(full_response)
        st.session_state.history_pic = model_chat.history

def clear_state():
    st.session_state.history_pic = []


if "history_pic" not in st.session_state:
    st.session_state.history_pic = []


image = None
if "app_key" in st.session_state:
    uploaded_file = st.file_uploader("choose a pic...", type=["jpg", "png", "jpeg", "gif"], label_visibility='collapsed', on_change = clear_state)
    if uploaded_file is not None:
        image = Image.open(uploaded_file).convert('RGB')
        image_bytes = image.tobytes()
        width, height = image.size
        resized_img = image.resize((128, int(height/(width/128))), Image.LANCZOS)
        st.image(resized_img)    

for message in st.session_state.history_pic:
      role = "assistant" if message.role == "model" else message.role
      with st.chat_message(role):
            for part in message.parts:
                  if part.text:
                      st.markdown(part.text)
                  elif part.image:
                      st.image(part.image.bytes)

if "app_key" in st.session_state:
    if prompt := st.chat_input("输入问题"):
        if image is None:
            pass
        #     st.warning("Please upload an image first", icon="⚠️")
        prompt = prompt.replace('\n', '  \n')
        with st.chat_message("user"):
            st.markdown(prompt)
        show_message(prompt, "Thinking...", image)
            # show_message(prompt, image, "Thinking...")
