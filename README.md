# AWS Course Projects

A collection of serverless AWS projects built as part of an AWS course. Each project lives in its own folder, is independently deployable, and has its own detailed README.

## Projects

### [AWS-Final-Project-Order-Management](./AWS-Final-Project-Order-Management)

A serverless, event-driven **Order Management System** — the course's final project.

- REST APIs (API Gateway + Lambda) for full order CRUD, backed by DynamoDB
- Email notifications on order deletion via SNS, delivered asynchronously through DynamoDB Streams
- Deleted orders backed up as `.txt` files in S3, fully decoupled from the delete request
- On-demand PDF summary of all deleted orders, generated from the S3 backups and returned via a pre-signed URL
- CloudWatch-based operational metrics exposed through the client (freestyle enhancement)
- Static HTML/CSS/JS frontend hosted on AWS Amplify

**Stack:** API Gateway · Lambda (Python) · DynamoDB · DynamoDB Streams · S3 · SNS · CloudWatch · Amplify

### [step-functions-project](./step-functions-project)

**Order Processing Workflow** — a Step Functions state machine built to teach orchestration primitives.

- Declarative branching (Choice state) instead of scattered `if/else` logic
- Built-in Retry/Catch error handling instead of hand-rolled retry loops
- A live, visual execution graph per run, including retry attempts

**Stack:** AWS Step Functions (Standard) · Lambda (Python)

### [serverless-chatbot](./serverless-chatbot)

**Academic Chat** — a serverless multi-turn AI chatbot combining AWS with the OpenAI API.

- Static frontend calling a single `POST /chat` endpoint
- Stateless Lambda backend; the browser owns the full conversation history and resends it on every request
- Demonstrates API Gateway + Lambda + Lambda Layers + CORS + environment-variable secret management

**Stack:** API Gateway · Lambda (Python) · OpenAI Responses API · Amplify

## Repository Structure

```text
AWS-Course/
├── AWS-Final-Project-Order-Management/   # Final project - serverless order management system
├── step-functions-project/               # Step Functions orchestration demo
├── serverless-chatbot/                   # Serverless multi-turn AI chatbot
└── .gitignore
```

## Conventions

- All backend code is Python; all frontends are static HTML/CSS/vanilla JS.
- Every project is deployed manually to an AWS Academy Learner Lab account (`us-east-1`, execution role `LabRole`) — no IaC/CI-CD is used anywhere in this repo.
- Each project folder's own `README.md` is the source of truth for its architecture, deployment steps, and API reference.

## Author

Lior Yanwo
