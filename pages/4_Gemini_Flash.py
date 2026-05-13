import os
import json
import time
import random
import tempfile
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
    'gemini-2.0-flash-exp': "Vision",
    'gemini-2.5-flash': "Flash",
    'gemini-2.5-pro': "Pro",
    'gemini-3-pro-image-preview': "Vision-Dev",
    'gemini-3-flash-preview': "Flash-Dev",
    'gemini-3-pro-preview': "Pro-Dev",
    'gemini-3.1-pro-preview': "Pro-Pre",
    }
default_index = list(model_options.keys()).index('gemini-2.5-pro')
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
if 'data_file' not in st.session_state:
    st.session_state['data_file'] = False
if 'use_vertex' not in st.session_state:
     st.session_state['use_vertex'] = False

# 侧边状态栏
st.markdown("""
<style>
    .stDownloadButton button {
        width: 100%;
        background-color: #8E75FF; /* Gemini 紫色 */
        color: white !important;
        border-radius: 10px;
        border: none;
        padding: 0.6rem;
        font-weight: 600;
        margin-top: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stDownloadButton button:hover {
        background-color: #7A62E0;
        border: none;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)


def get_history_json(model_name):
    import copy
    
    # 深度拷贝一份历史记录，避免修改原始对话显示
    safe_history = []
    
    for item in st.session_state.history_pic:
        # 复制字典，防止修改 session_state 本身
        new_item = item.copy()
        
        # 处理 text 字段（可能是字符串，也可能是包含 File 对象的列表）
        raw_text = new_item.get("text", "")
        if isinstance(raw_text, list):
            # 如果是列表，将其中的非字符串对象转为描述文字
            clean_parts = []
            for part in raw_text:
                if isinstance(part, str):
                    clean_parts.append(part)
                else:
                    # 将 Google File 对象或其他对象转为字符串描述
                    clean_parts.append(f"<{type(part).__name__} file/object>")
            new_item["text"] = " ".join(clean_parts)
        
        # 处理 image 字段（bytes 类型无法直接 JSON 序列化）
        if "image" in new_item and new_item["image"] is not None:
            # bytes 类型转为占位符描述
            new_item["image"] = f"<Binary Image Data: {len(new_item['image'])} bytes>"
            
        safe_history.append(new_item)

    try:
        return json.dumps(
            {
                "model": model_name,
                "history": safe_history
            },
            ensure_ascii=False,
            indent=2
        )
    except Exception as e:
        # 如果还是报错，返回错误信息
        return json.dumps({"error": f"序列化失败: {str(e)}"})

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
    
    st.download_button(
        label="⬇️ Download Chat History (JSON)",
        data=get_history_json(selected_model),
        file_name="chat_history.json",
        mime="application/json",
        use_container_width=True
    )

try:
    # gemini-pro-vision
    app_key = st.session_state.app_key
    if app_key is None:
        st.warning("Please Put Your Gemini App Key First.")
    else:
        if len(app_key) < 40:
            client = genai.Client(api_key = app_key)
        else:
            st.session_state['use_vertex'] = True
            client = genai.Client(api_key = app_key, vertexai=True)
    config = types.GenerateContentConfig(
      thinking_config=types.ThinkingConfig(
          thinking_level="low",
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
            if "image" in message and message['image'] is not None:
                content = [
                    message["text"],
                    types.Part.from_bytes(data= message['image'], mime_type="image/png"),
                ]
            if message['role'] == "assistant":
                # data = types.Content(role='model',parts=[types.Part.from_text(text=content)],)
                model_history.append(types.ModelContent(content))
            else:
                # data = types.Content(role='user',parts=[types.Part.from_text(text=content)],)
                 model_history.append(types.UserContent(content))
    return model_history


def show_message(prompt, image, file, loading_str):
    global data_cache
    if image and not st.session_state.data_file:
        prompt = [prompt, image]
        st.session_state.data_file = True
    if file and not st.session_state.data_file:
        if st.session_state.use_vertex:
            prompt = [prompt, types.Part.from_bytes(data=file, mime_type="application/pdf")]
        else:
            prompt = [prompt, file]
        st.session_state.data_file = True
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
  保存上传的PDF文件到本地，并返回数据流。
  """
  try:
    pdf_data = uploaded_file.getvalue()
    with open(save_path, "wb") as f:  # 以二进制写入模式打开文件
      f.write(uploaded_file.getbuffer())  # 将上传文件的内容写入文件
    return pdf_data
  except Exception as e:
    print(f"保存文件失败: {e}")  # 打印错误信息，方便调试
    return None


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
    file_data = None
    if file:
        clear_other_pdfs(BASE_PATH, keep_filename=file.name)
        file_save_path = BASE_PATH / file.name
        file_data = save_uploaded_pdf(file, file_save_path)
        st.session_state['data_file'] = False
    return file_save_path, file_data


image, file = None, None
if "app_key" in st.session_state and st.session_state.app_key is not None:
    uploaded_file = st.file_uploader("请选择本地PDF或图片...", type=["pdf", "jpg", "png", "jpeg", "gif"], label_visibility='collapsed', on_change = clear_state)
    if uploaded_file is not None:
        if uploaded_file.type == "application/pdf":
            try:
                # 将文件保存到本地
                file_path, file_data = input_file(uploaded_file)
                if not st.session_state['use_vertex']:
                    # 使用client加载的文件数据，可以作为展示名称 uploaded_file.name
                    file = client.files.upload(file=file_path, config={'display_name':'reference materials' })
                    st.success(f"文件 '{uploaded_file.name}' 上传成功！")
                    st.write(f"Google GenAI File ID: {file.name}")
                else:
                    # 使用二进制数据
                    file = file_data
            except Exception as e:
                st.error(f"文件上传失败: {e}")
                # 打印详细错误以帮助调试
                st.exception(e)
        else:
            image = Image.open(uploaded_file).convert('RGB')
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
