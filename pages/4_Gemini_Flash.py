import os
import time
import random
import streamlit as st

from PIL import Image
from pathlib import Path
from google import genai
from google.genai import types

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
    'gemini-2.5-flash-preview-05-20': "Think-Pre",
    'gemini-2.5-flash': "Think-Flash",
    "gemini-2.5-pro":"Think-PRO"
    }
default_index = list(model_options.keys()).index('gemini-2.5-flash-preview-05-20')
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
    # gemini-pro-vision
    client = genai.Client(api_key = st.session_state.app_key)
    config = types.GenerateContentConfig(
      thinking_config=types.ThinkingConfig(
        include_thoughts=True
      )
    )
except AttributeError as e:
    st.warning("Please Put Your Gemini App Key First.")


def clear_state():
    st.session_state.history_pic = []


def convert_history_model(history_list):
    model_history = []
    if len(st.session_state.history_pic) > 0:
        for message in st.session_state.history_pic:
            data_dict = {}
            role = "model" if message.role == "assistant" else message.role
            if "text" in message:
                content = message["text"]
            elif "image" in message:
                content = {
                    "mime_type": "image/png",
                    "data": message["image"],
                }
            data_dict[role] = content
            model_history.append(data_dict)
    return model_history


def convert_history_gemini():
    model_history = []
    if len(st.session_state.history_pic) > 0:
        for message in st.session_state.history_pic:
            content = message["text"]
            if message['role'] == "assistant":
                # data = types.Content(role='model',parts=[types.Part.from_text(text=content)],)
                model_history.append(types.ModelContent(content))
            else:
                # data = types.Content(role='user',parts=[types.Part.from_text(text=content)],)
                 model_history.append(types.UserContent(content))
            if "image" in message:
                content_image = {
                    "mime_type": "image/png",
                    "data": message["image"],
                }
                if message['role'] == "assistant":
                    model_history.append(types.ModelContent(content_image))
                else:
                    model_history.append(types.UserContent(content_image))
    return model_history


def show_message(prompt, image, file, loading_str):
    if image:
        prompt = [prompt, image]
    if file:
        prompt = [prompt, file]
    history = convert_history_gemini()
    chat = client.chats.create(model=selected_model, config=config, history=history)
    # 开启对话
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown(loading_str)
        # 初始化变量
        image_count = 0
        full_response = "#### 正式回答：\n" 
        thought_text = "#### 思维链：\n"
        image_data = None
        try:
            for chunk in chat.send_message_stream(prompt):
                word_count = 0
                random_int = random.randint(10, 20)
                if not chunk.candidates or not chunk.candidates[0].content or not chunk.candidates[0].content.parts:
                    continue
                for part in chunk.candidates[0].content.parts:
                    if part.inline_data:
                        image_data = part.inline_data.data
                        mime_type = part.inline_data.mime_type
                        # 检查 image_data 是否为空或为 None
                        if image_data:
                            try:
                                output_file = f"genai_image_{image_count}.{mime_type.split('/')[-1]}"
                                st.image(image_data, caption=f"Generated Image {output_file}", use_column_width=True)
                                image_count += 1
                            except Exception as e:
                                st.error(f"Error displaying image: {e}")
                    elif part.thought:
                        thought_text += part.text
                        message_placeholder.markdown(thought_text + "_")
                    elif part.text:
                        full_response += part.text
                        message_placeholder.markdown(full_response + "_")
            # 结束流式输出后一次性全部刷新
            # if thought_text:
            #     message_placeholder.markdown(thought_text)
            # elif full_response:
            #     message_placeholder.markdown(full_response)
        except Exception as e:
            st.exception(e)
        full_response = thought_text + full_response
        message_placeholder.markdown(full_response)
        # 只有回答成功时，更新历史消息
        st.session_state.history_pic.append({"role": "user", "text": prompt})
        if image_data:
            st.session_state.history_pic.append({"role": "assistant", "text": full_response, "image": image_data})
        else:
             #只保存文本，图像设置为None
            st.session_state.history_pic.append({"role": "assistant", "text": full_response, "image": None})


def save_uploaded_pdf(uploaded_file, save_path):
  """
  保存上传的PDF文件到本地。
  """
  try:
    with open(save_path, "wb") as f:  # 以二进制写入模式打开文件
      f.write(uploaded_file.getbuffer())  # 将上传文件的内容写入文件
    return True
  except Exception as e:
    print(f"保存文件失败: {e}")  # 打印错误信息，方便调试
    return False


def clear_other_pdfs(dir_path, keep_filename=None):
    """删除指定目录下除 keep_filename 外的所有pdf文件。"""
    pdf_files = dir_path.glob("*.pdf")
    for f in pdf_files:
        if keep_filename is not None and f.name == keep_filename:
            continue
        try:
            f.unlink()
        except Exception as e:
            st.warning(f"删除 {f} 失败: {e}")


@st.cache_data(show_spinner=False)
def input_file(file):
    # uploaded_file = st.file_uploader('请打开一个文件', type=['pdf'], accept_multiple_files=True)
    file_save_path = None
    if file:
        clear_other_pdfs(BASE_PATH, keep_filename=file.name)
        file_save_path = BASE_PATH / file.name
        save_uploaded_pdf(file, file_save_path)
    return file_save_path


image, file = None, None
if "app_key" in st.session_state:
    uploaded_file = st.file_uploader("请选择本地PDF或图片...", type=["pdf", "jpg", "png", "jpeg", "gif"], label_visibility='collapsed', on_change = clear_state)
    if uploaded_file is not None:
        if uploaded_file.type == "application/pdf":
            file_path = input_file(uploaded_file)
            file = client.files.upload(file=file_path, config={'display_name': 'reference'})
        else:
            image = Image.open(uploaded_image).convert('RGB')
            image_bytes = image.tobytes()
            width, height = image.size
            resized_img = image.resize((128, int(height/(width/128))), Image.LANCZOS)
            st.image(resized_img)

if len(st.session_state.history_pic) > 0:
    for item in st.session_state.history_pic:
        image_count = 0
        with st.chat_message(item["role"]):
            if "text" in item and item["text"]:
                st.markdown(item["text"])
            if "image" in item and item["image"]:
                st.image(item["image"], caption=f"Generated Image_{image_count}", use_column_width=True)
                image_count += 1

if "app_key" in st.session_state:
    if prompt := st.chat_input("请输入问题"):
        if image is None:
            pass
        prompt = prompt.replace('\n', '  \n')
        with st.chat_message("user"):
            st.markdown(prompt)
        show_message(prompt, image, file, "Thinking...")
