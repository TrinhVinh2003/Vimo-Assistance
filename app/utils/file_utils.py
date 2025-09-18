import os

import requests
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader


def load_pdf(file_path: str, max_chunks: int = 5) -> list:
    """Load and split PDF content into chunks, limit to max_chunks."""
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=30)
    chunks = text_splitter.split_documents(documents)

    # remove the file after read content
    os.remove(file_path)
    return chunks[:max_chunks]


def download_file_from_google_drive(file_id: str, destination: str) -> None:
    """Download file from Google Drive."""
    url = "https://drive.google.com/uc?export=download"

    session = requests.Session()

    response = session.get(url, params={"id": file_id}, stream=True)
    token = get_confirm_token(response)

    if token:
        params = {"id": file_id, "confirm": token}
        response = session.get(url, params=params, stream=True)

    save_response_content(response, destination)


def get_confirm_token(response: dict) -> str:
    """Get the confirmation token from the response."""
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            return value

    return None


def save_response_content(response: dict, destination: str) -> None:
    """Save the response content to the destination."""
    chunk_size = 32768

    with open(destination, "wb") as f:
        for chunk in response.iter_content(chunk_size):
            if chunk:
                f.write(chunk)
