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

if "app_key" not in st.session_state:
    app_key = st.text_input("Your Gemini App Key", type='password')
    if app_key:
        st.session_state.app_key = app_key

try:
    genai.configure(api_key = st.session_state.app_key)
    # gemini-1.5-flash
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
except AttributeError as e:
    st.warning("Please Put Your Gemini App Key First.")


def show_message(prompt, loading_str, image_bytes=None):
    model_chat = model.start_chat(history = st.session_state.history_pic)
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown(loading_str)
        full_response = ""
        try:
            if image_bytes:
                prompt = [prompt, image_bytes]
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
            image_bytes = None
        #     st.warning("Please upload an image first", icon="⚠️")
        prompt = prompt.replace('\n', '  \n')
        with st.chat_message("user"):
            st.markdown(prompt)
        show_message(prompt, "Thinking...", image_bytes)
            # show_message(prompt, image, "Thinking...")
