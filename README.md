# Academic Chat — AWS Serverless Chatbot

A serverless multi-turn AI chatbot built with AWS and the OpenAI API.

The project demonstrates how to build a simple full-stack chatbot using a static frontend, Amazon API Gateway, AWS Lambda, and OpenAI's Responses API.

## Architecture

```text
Browser
  │
  │  POST /chat
  │  { messages: [...] }
  ▼
Amazon API Gateway
  │
  ▼
AWS Lambda (Python)
  │
  │  OpenAI Responses API
  ▼
OpenAI
  │
  ▼
AWS Lambda
  │
  ▼
API Gateway
  │
  ▼
Browser
```

## Technologies

- HTML
- CSS
- JavaScript
- Python 3.11
- AWS Lambda
- Amazon API Gateway
- AWS Amplify
- OpenAI Responses API

## How It Works

The frontend maintains the conversation history in the browser.

Each message is stored as:

```json
{
  "role": "user",
  "content": "What is 2 + 2?"
}
```

When the user sends a new message, the frontend sends the complete conversation history to the backend:

```json
{
  "messages": [
    {
      "role": "user",
      "content": "1 + 1 = ?"
    },
    {
      "role": "assistant",
      "content": "1 + 1 = 2"
    },
    {
      "role": "user",
      "content": "What was my last question?"
    }
  ]
}
```

This allows the chatbot to maintain a multi-turn conversation while keeping the Lambda function completely stateless.

Refreshing the browser clears the conversation history.

## Backend

The backend is implemented as an AWS Lambda function written in Python.

The Lambda function:

1. Receives the conversation history from API Gateway.
2. Validates the request body and messages.
3. Adds the application's system/developer prompt.
4. Sends the conversation to the OpenAI Responses API.
5. Returns the assistant's response to the frontend.

The current model configuration is:

```text
Model: gpt-4.1-nano
Maximum output tokens: 500
```

## API

The application exposes the following endpoint:

```text
POST /chat
```

Example request:

```json
{
  "messages": [
    {
      "role": "user",
      "content": "2 + 2 = ?"
    }
  ]
}
```

Example response:

```json
{
  "reply": "2 + 2 = 4"
}
```

## Multi-Turn Conversation

Conversation state is managed manually by the frontend.

For example:

```text
User:      1 + 1 = ?
Assistant: 1 + 1 = 2

User:      2 + 2 = ?
Assistant: 2 + 2 = 4

User:      4 + 4 = ?
Assistant: 4 + 4 = 8

User:      What was my last question?
Assistant: Your last question was: "4 + 4 = ?"
```

No database or server-side conversation storage is required.

## CORS

CORS is configured through API Gateway so that the browser frontend can communicate with the API.

The API supports:

```text
OPTIONS
POST
```

API Gateway handles browser preflight requests before the actual POST request is sent to Lambda.

## Security

The OpenAI API key is never stored in the frontend or committed to the repository.

The Lambda function reads it from the environment:

```python
client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)
```

The following local/build files are excluded from Git:

```text
.venv/
lambda-layer/
lambda-layer.zip
```

Never commit API keys or other secrets to the repository.

## Project Structure

```text
AWS-Lab8-chatbot/
│
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
│
├── lambda/
│   └── lambda_function.py
│
├── chat.py
├── .gitignore
└── README.md
```

## Request Validation

The Lambda validates incoming requests and returns HTTP `400` responses for invalid input, including:

- Invalid JSON
- Non-object JSON bodies
- Missing `messages`
- Empty message arrays
- Invalid message roles
- Missing or empty message content

Unexpected OpenAI/API failures return an appropriate backend error response.

## Deployment

The application uses the following AWS architecture:

**Frontend**

```text
AWS Amplify
```

**Backend**

```text
API Gateway
      ↓
AWS Lambda
      ↓
OpenAI Responses API
```

The Lambda runtime is:

```text
Python 3.11
Architecture: x86_64
```

The OpenAI Python SDK and its dependencies are provided through a custom AWS Lambda Layer.

## Verification

The deployed application was tested against the live API Gateway endpoint.

Verified functionality includes:

- Successful OpenAI responses
- Multi-turn conversation history
- Request validation
- Invalid JSON handling
- Non-object JSON handling
- CORS preflight handling
- End-to-end API Gateway → Lambda → OpenAI communication

## Purpose

This project was built as part of an AWS course lab to demonstrate:

- Serverless application architecture
- REST API development
- AWS Lambda integration
- API Gateway configuration
- Lambda Layers
- Environment-variable secret management
- CORS configuration
- OpenAI API integration
- Client-side conversation state management
