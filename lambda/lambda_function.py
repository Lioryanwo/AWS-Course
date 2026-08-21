import json
import os

from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

MODEL = "gpt-4.1-nano"
MAX_OUTPUT_TOKENS = 500

SYSTEM_PROMPT = (
    "You are a helpful academic assistant. Answer clearly and concisely, "
    "as if helping a student learn faster and build better."
)

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "OPTIONS,POST",
}


def _response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(payload),
    }


def _validate_messages(messages):
    if not isinstance(messages, list) or not messages:
        return False

    for message in messages:
        if not isinstance(message, dict):
            return False

        if message.get("role") not in ("user", "assistant"):
            return False

        if (
            not isinstance(message.get("content"), str)
            or not message["content"].strip()
        ):
            return False

    return True


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(
            400,
            {"error": "Request body must be valid JSON."},
        )

    if not isinstance(body, dict):
        return _response(
            400,
            {"error": "Request body must be a JSON object."},
        )

    messages = body.get("messages")

    if not _validate_messages(messages):
        return _response(
            400,
            {
                "error": (
                    "Request must include a non-empty 'messages' array "
                    "of {role, content} objects."
                )
            },
        )

    conversation = [
        {"role": "developer", "content": SYSTEM_PROMPT}
    ] + messages

    try:
        response = client.responses.create(
            input=conversation,
            model=MODEL,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
    except Exception:
        return _response(
            502,
            {
                "error": (
                    "The assistant is currently unavailable. "
                    "Please try again."
                )
            },
        )

    return _response(
        200,
        {"reply": response.output_text},
    )