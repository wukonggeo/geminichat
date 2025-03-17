import time
import random
import streamlit as st

from PIL import Image
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

if "app_key" not in st.session_state:
    app_key = st.text_input("Your Gemini App Key", type='password')
    if app_key:
        st.session_state.app_key = app_key

try:
    # gemini-pro-vision
    client = genai.Client(api_key = st.session_state.app_key)
    config = types.GenerateContentConfig(
        temperature=1,
        top_p=.95,
        top_k=40,
        response_modalities=["Text", "Image"]
    )
except AttributeError as e:
    st.warning("Please Put Your Gemini App Key First.")


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
    

def show_message(prompt, image, loading_str):
    if image:
        prompt = [prompt, image]
    response_stream = client.models.generate_content_stream(
        model="gemini-2.0-flash-exp",
        contents=prompt,
        config=config,
    )
    image_count = 0
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown(loading_str)
        full_response = ""
        try:
            for chunk in response_stream:
                word_count = 0
                random_int = random.randint(10, 20)
                if not chunk.candidates or not chunk.candidates[0].content or not chunk.candidates[0].content.parts:
                    continue
                for part in chunk.candidates[0].content.parts:
                    if part.inline_data:
                        image_data = part.inline_data.data
                        mime_type = part.inline_data.mime_type
                        try:
                            output_file = f"genai_image_{image_count}.{mime_type.split('/')[-1]}"
                            st.image(image_data, caption=f"Generated Image {output_file}", use_column_width=True)
                            image_count += 1
                        except Exception as e:
                            st.error(f"Error displaying image: {e}")
                    elif part.text:
                        full_response += part.text
                        message_placeholder.markdown(full_response + "_")
        except Exception as e:
            st.exception(e)
        message_placeholder.markdown(full_response)
        if image_data:
            st.session_state.history_pic.append({"role": "assistant", "image": image_data})
        st.session_state.history_pic.append({"role": "assistant", "text": full_response})
        

def clear_state():
    st.session_state.history_pic = []


if "history_pic" not in st.session_state:
    st.session_state.history_pic = []


image = None
if "app_key" in st.session_state:
    uploaded_file = st.file_uploader("请选择本地图片...", type=["jpg", "png", "jpeg", "gif"], label_visibility='collapsed', on_change = clear_state)
    if uploaded_file is not None:
        image = Image.open(uploaded_file).convert('RGB')
        width, height = image.size
        resized_img = image.resize((256, int(height/(width/256))), Image.LANCZOS)
        st.image(resized_img)    

if len(st.session_state.history_pic) > 0:
    for item in st.session_state.history_pic:
        with st.chat_message(item["role"]):
            if "text" in item and item["text"]:
                st.markdown(item["text"])
            if "image" in item and item["image"]:
                st.image(item["image"], caption=f"Generated Image", use_column_width=True)

if "app_key" in st.session_state:
    if prompt := st.chat_input("请输入问题"):
        if image is None:
            pass
        prompt = prompt.replace('\n', '  \n')
        with st.chat_message("user"):
            st.markdown(prompt)
            st.session_state.history_pic.append({"role": "user", "text": prompt})
        show_message(prompt, image, "Thinking...")
