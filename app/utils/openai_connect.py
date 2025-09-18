import json
import os
import time
from typing import Generator, Optional

import requests
import tiktoken
from loguru import logger

# OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")
END_OF_STREAM = ""
USAGE_CHAR = ""

if OPENAI_BASE_URL.endswith("/"):
    OPENAI_BASE_URL = OPENAI_BASE_URL[:-1]

if not OPENAI_API_KEY:
    logger.error("OpenAI API key is not set, please set it to environment variable")
    raise Exception("OpenAI API key is not set, please set it to environment variable")

DEFAULT_PROMPT = "You are a helpful assistant"
OPENAI_TIMEOUT_SECONDS = 20

MAX_TOKENS = {
    "en": 4096,
    "vi": 8192,
}


# https://github.com/openai/openai-cookbook/blob/683e5f5a71bc7a1b0e5b7a35e087f53cc55fceea/examples/How_to_count_tokens_with_tiktoken.ipynb
def num_tokens_from_messages(
    messages: list,
    model: str = "gpt-4o-mini-2024-07-18",
) -> int:
    """Return the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        logger.warning("Warning: model not found. Using o200k_base encoding.")
        encoding = tiktoken.get_encoding("o200k_base")
    if model in {
        "gpt-3.5-turbo-0125",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
        "gpt-4o-mini-2024-07-18",
        "gpt-4o-2024-08-06",
    }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif "gpt-3.5-turbo" in model:
        logger.warning(
            "Warning: gpt-3.5-turbo may update over time. \
            Returning num tokens assuming gpt-3.5-turbo-0125.",
        )
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0125")
    elif "gpt-4o-mini" in model:
        logger.warning(
            "Warning: gpt-4o-mini may update over time. \
            Returning num tokens assuming gpt-4o-mini-2024-07-18.",
        )
        return num_tokens_from_messages(messages, model="gpt-4o-mini-2024-07-18")
    elif "gpt-4o" in model:
        logger.warning(
            "Warning: gpt-4o and gpt-4o-mini may update over time. \
            Returning num tokens assuming gpt-4o-2024-08-06.",
        )
        return num_tokens_from_messages(messages, model="gpt-4o-2024-08-06")
    elif "gpt-4" in model:
        logger.warning(
            "Warning: gpt-4 may update over time. \
            Returning num tokens assuming gpt-4-0613.",
        )
        return num_tokens_from_messages(messages, model="gpt-4-0613")
    else:
        raise NotImplementedError(
            f"""num_tokens_from_messages() is not implemented for model {model}.""",
        )
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens


def reduce_messages(
    system_message: str,
    history_messages: list,
    user_message: str,
    model: str = "gpt-4o-mini",
    language: Optional[str] = "vi",
) -> list:
    # first message is always the prompt
    # last message is always the question
    # reduce messages in between until they fit in max_tokens, oldest first
    # return the reduced messages
    start_time = time.time()
    original_size = len(history_messages) + 2  # +2 for system and question
    count_tokens = num_tokens_from_messages(
        [system_message, *history_messages, user_message],
        model=model,
    )
    is_reduced = False
    max_tokens = MAX_TOKENS.get(language, 4096)

    while len(history_messages) > 0 and count_tokens > max_tokens:
        # remove the oldest message history
        history_messages = history_messages[1:]
        count_tokens = num_tokens_from_messages(
            [system_message, *history_messages, user_message],
            model=model,
        )
        is_reduced = True
    logger.debug(f"Check token limit cost {time.time() - start_time!s} seconds!")
    if is_reduced:
        logger.debug(
            f"New messages size: {len(history_messages)}/{original_size} tokens: {count_tokens}",  # noqa: E501
        )
    return history_messages


def embed(texts: list, retried: int = 3) -> tuple:
    """Embed texts using OpenAI API."""

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + OPENAI_API_KEY,
    }
    data = {
        "model": "text-embedding-ada-002",
        "input": [t.lower() for t in texts],
    }
    try:
        start_time = time.time()
        response = requests.post(
            f"{OPENAI_BASE_URL}/v1/embeddings",
            headers=headers,
            data=json.dumps(data),
            timeout=OPENAI_TIMEOUT_SECONDS,
        )
        logger.info(
            f"Embedding {len(texts)} chunks cost {time.time() - start_time}s",
        )
        if response.status_code == 200:
            result = response.json()
            return True, [x["embedding"] for x in result["data"]], result["usage"]
        raise Exception(
            f"Embedding got status code {response.status_code}: {response.text}",
        )
    except Exception as e:
        logger.exception(f"OpenAI embedding failed: {e}")
        if retried > 0:
            logger.exception(f"OpenAI embedding failed, retrying {retried}...")
            return embed(texts, retried - 1)
        logger.exception("OpenAI embedding failed, give up.")
    return False, None, None


def chat_completion_stream(
    message: str,
    language: str = "en",
    model: str = "gpt-4o-mini",
    system_prompt: str = DEFAULT_PROMPT,
    histories: Optional[list] = None,
    retried: int = 1,
) -> Generator:
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + OPENAI_API_KEY,
    }

    system_message = {"role": "system", "content": system_prompt}
    user_message = {"role": "user", "content": message}

    messages = [system_message]
    if histories:
        messages.extend(histories)
    messages.append(user_message)

    data = {
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": 0.2,
    }

    try:
        response = requests.post(
            f"{OPENAI_BASE_URL}/v1/chat/completions",
            headers=headers,
            data=json.dumps(data),
            stream=True,
            timeout=OPENAI_TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            for line in response.iter_lines():
                chunk_content, usage = extract_streaming_chunk(line)
                if chunk_content is not None:
                    yield True, chunk_content, usage
        else:
            raise Exception(f"Got status code {response.status_code}: {response.text}")
    except Exception:
        if retried > 0:
            logger.exception("OpenAI chat completion failed, retrying...")
            yield from chat_completion_stream(
                message=message,
                language=language,
                model=model,
                system_prompt=system_prompt,
                histories=histories,
                retried=retried - 1,
            )
        else:
            logger.exception("OpenAI chat completion stream failed, give up.")
            yield False, None, None


def extract_streaming_chunk(line: bytes) -> tuple:
    # https://github.com/openai/openai-python/blob/5453a19efe6fa4395673782e5e3bd161572d383c/openai/api_requestor.py#L106
    if line and line.startswith(b"data: "):
        # SSE event may be valid when it contain whitespace
        line = line[len(b"data: ") :]
        # DONE
        if line.strip() == END_OF_STREAM.encode("utf-8"):
            # return here will cause GeneratorExit exception in urllib3
            # and it will close http connection with TCP Reset
            return END_OF_STREAM, None
        try:
            # Sometime, OpenAI send an invalid chunk. This seem a bug from OpenAI
            # OpenAI streaming chunk: b'"{\\"rate_limit_usage\\": {\\'
            # https://community.openai.com/t/receiving-rate-limit-usage-in-completion-stream/427476/
            chunk_decode = json.loads(line.decode("utf-8"))
            if chunk_decode["choices"]:
                return (
                    chunk_decode["choices"][0]["delta"].get("content"),
                    None,
                )
            return USAGE_CHAR, chunk_decode["usage"]
        except Exception:
            logger.warning(f"OpenAI streaming chunk: {line}")
            return None, None
    return None, None
