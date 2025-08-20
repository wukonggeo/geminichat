from PIL import Image
import google.generativeai as genai
import streamlit as st
import time
import random
from pathlib import Path
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
    'gemini-2.5-flash-preview-05-20': "Think-Flash-pre",
    'gemini-2.5-flash': "Think-Flash",
    "gemini-2.5-pro":"Think-PRO"
    }
default_index = list(model_options.keys()).index('gemini-2.0-flash')
BASE_PATH = Path(__file__).resolve().parents[1] / 'resource'

# 初始化状态信息
if "history_pic" not in st.session_state:
    st.session_state.history_pic = []
if 'app_key' not in st.session_state:
    st.session_state.app_key = None
if st.session_state.app_key is None:
    app_key = st.text_input("Your Gemini App Key", type='password', key="gemini_key_input")
    if app_key:
        st.session_state.app_key = app_key
        st.rerun()

# 侧边状态栏
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


def clear_state():
    st.session_state.history_pic = []


def show_message(prompt, loading_str, image=None):
    model_chat = model.start_chat(history = st.session_state.history_pic)
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown(loading_str)
        full_response = ""
        try:
            if image:
                prompt = [prompt, image]
            for chunk in model_chat.send_message(prompt, stream = True):                   
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


def save_uploaded_pdf(uploaded_file, save_path):
  """
  保存上传的 PDF 文件到本地。
  """
  try:
    with open(save_path, "wb") as f:  # 以二进制写入模式打开文件
      f.write(uploaded_file.getbuffer())  # 将上传文件的内容写入文件
    return True
  except Exception as e:
    print(f"保存文件失败: {e}")  # 打印错误信息，方便调试
    return False


@st.cache_data(show_spinner=False)
def input_file(file):
    # uploaded_file = st.file_uploader('请打开一个文件', type=['pdf'], accept_multiple_files=True)
    if file:
        file_save_path = BASE_PATH / file.name
        save_uploaded_pdf(file, file_save_path)
    with st.spinner("正在处理文件..."):
        time.sleep(2)
    return file_save_path


# Streamlit每次对话都会将所有函数重新执行一遍
uploaded_pdf = st.file_uploader(
    "请打开一个文件", type=["pdf"], accept_multiple_files=True
)
if uploaded_pdf is not None:
    file_path = input_file(uploaded_pdf)
else:
    file_path = None

image = None
if "app_key" in st.session_state and st.session_state.app_key is not None:
    uploaded_image = st.file_uploader("choose a pic...", type=["jpg", "png", "jpeg", "gif"], label_visibility='collapsed', on_change = clear_state)
    if uploaded_image is not None:
        image = Image.open(uploaded_image).convert('RGB')
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
