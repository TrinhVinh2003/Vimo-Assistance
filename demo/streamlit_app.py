import json
import logging

import requests
import streamlit as st

# Thiết lập logging
logger = logging.getLogger(__name__)

# URL của webhook n8n
N8N_WEBHOOK_URL = "http://localhost:5678/webhook-test/519802ae-d11c-4403-8a99-7c9b9452ebad"

def initialize_session_state() -> None:
    """Khởi tạo session state để lưu trữ lịch sử trò chuyện."""
    if "messages" not in st.session_state:
        st.session_state.messages = []

def clear_session() -> None:
    """Xóa session state và làm mới trang."""
    st.session_state.messages = []
    st.rerun()

def send_to_n8n(prompt: str, session_id: str, model: str) -> str:
    """Gửi yêu cầu HTTP đến webhook n8n và trả về kết quả."""
    payload = {
        "prompt": prompt,
        "session_id": session_id,
        "model": model
    }
    try:
        response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and data:
            return data[0].get("output", "No response from n8n")
        else:
            return "No response from n8n"
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending request to n8n: {e}")
        return f"Error: Unable to get response from n8n ({e})"

def main() -> None:
    initialize_session_state()
    
    # Cấu hình trang Streamlit
    st.set_page_config(
        page_title="Mozaic Assistant",
        page_icon="🎤",
    )

    # Thêm CSS để đặt hình ảnh background và ẩn avatar mặc định
    st.markdown(
        """
        <style>
    .stApp {
        background-image: url("https://i.ibb.co/3yYsycNV/image-2025-06-17-210432.png");
        height: 100%;
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
      
    }

        [data-testid="stChatMessageAvatar"] {
            display: none !important;
        }
        .stChatMessage > div:first-child {
            display: none !important;
        }
        .chat-container {
            margin: 1rem 0;
        }
        .user-message {
            display: flex;
            justify-content: flex-end;
            align-items: center;
            gap: 10px;
        }
        .assistant-message {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .message-bubble {
            background-color: rgba(255, 255, 255, 0.1);
            padding: 10px;
            border-radius: 10px;
            color: white;
            max-width: 70%;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.title("Mozaic Assistant :orange_heart:")

    # Sidebar: Cấu hình model và session
    with st.sidebar:
        st.subheader("Settings")
        session_id = st.text_input("Session ID", "test_session")
        llm_model = st.selectbox(
            "Select a model",
            ["gpt-4o-mini", "gpt-4o", "gpt-o1"],
        )
        if st.button("Clear session"):
            clear_session()

    # Hiển thị lịch sử trò chuyện
    for msg in st.session_state.messages:
        role = msg["role"]
        if role == "assistant":
            st.markdown(
                f"""
                <div class='chat-container assistant-message'>
                    <img src="https://i.postimg.cc/1RTtL01N/Mozaic-Group-Partners-Logo4.jpg" width="40" style="border-radius: 5px;" />
                    <div class='message-bubble'>
                        {msg['content']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div class='chat-container user-message'>
                    <div class='message-bubble'>
                        {msg['content']}
                    </div>
                    <img src="https://icon-library.com/images/windows-8-user-icon/windows-8-user-icon-15.jpg" width="40" style="border-radius: 5px;" />
                </div>
                """,
                unsafe_allow_html=True
            )

    # Nhập câu hỏi từ người dùng
    if prompt := st.chat_input("Enter your question"):
        # Lưu câu hỏi vào session state
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Hiển thị câu hỏi ngay lập tức
        st.markdown(
            f"""
            <div class='chat-container user-message'>
                <div class='message-bubble'>
                    {prompt}
                </div>
                <img src="https://icon-library.com/images/windows-8-user-icon/windows-8-user-icon-15.jpg" width="40" style="border-radius: 5px;" />
            </div>
            """,
            unsafe_allow_html=True
        )

        # Gửi yêu cầu đến n8n và hiển thị kết quả
        st.markdown(
            f"""
            <div class='chat-container assistant-message'>
                <img src="https://i.postimg.cc/1RTtL01N/Mozaic-Group-Partners-Logo4.jpg" width="40" style="border-radius: 5px;" />
                <div class='message-bubble'>
                    <div style='display: flex; align-items: center;'>
                        <span style='margin-right: 10px;'>Thinking🤔...</span>
                        <div class='spinner'></div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        response = send_to_n8n(prompt, session_id, llm_model)
        st.markdown(
            f"""
            <div class='chat-container assistant-message'>
                <img src="https://i.postimg.cc/1RTtL01N/Mozaic-Group-Partners-Logo4.jpg" width="40" style="border-radius: 5px;" />
                <div class='message-bubble'>
                    {response}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        # Lưu phản hồi vào session state
        st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()