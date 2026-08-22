# Order Processing Workflow — AWS Step Functions

A serverless order-processing workflow built to demonstrate AWS Step Functions: Task orchestration, Choice-based branching, and Retry/Catch error handling.

This project's teaching focus is **AWS Step Functions itself**, not payment technology. Payment processing is a simple simulated Lambda used only to demonstrate Retry and Catch.

## Project Objective

The workflow orchestrates a simple order-processing process — validate an order, then attempt simulated payment — to demonstrate:

1. **Declarative branching** (Choice state) instead of `if/else` scattered across application code.
2. **Built-in retry/backoff and error routing** (Retry/Catch) instead of hand-rolled retry loops.
3. **A live, visual execution graph** showing exactly which path an execution took, including retry attempts.

The central teaching point is the distinction between two kinds of outcome:

- A **business validation failure** (invalid order) — an expected, correctly-handled outcome. No retry is needed because nothing technically failed.
- A **technical processing failure** (simulated payment error) — something actually broke, and Step Functions automatically retries before routing to a controlled failure state via Catch.

## Architecture

```text
Manual JSON input (Step Functions console "Start execution")
        ↓
AWS Step Functions — Standard state machine
        ↓
ValidateOrder Lambda → Choice → ProcessPayment Lambda
```

No API Gateway, DynamoDB, S3, SNS, SQS, or real payment services. The state machine is a **Standard** (not Express) type, so the console shows full per-execution visual history, including retry attempts.

## Input Contract

```json
{
  "orderId": "ORD-1001",
  "product": "Laptop",
  "quantity": 2,
  "simulatePaymentFailure": false
}
```

- `quantity >= 1` → valid order
- `quantity <= 0`, missing, or non-numeric → invalid order (never throws — always a clean business outcome)
- `simulatePaymentFailure: false` → simulated payment succeeds
- `simulatePaymentFailure: true` → simulated payment throws a processing error

## Workflow States

| # | State name | Type | Purpose | Next |
|---|---|---|---|---|
| 1 | `ValidateOrder` | Task (Lambda: `validate-order`) | Check `quantity >= 1` | `ChoiceValidOrder` |
| 2 | `ChoiceValidOrder` | Choice | `isValid == true` → `ProcessPayment`; **Default** → `RejectOrder` | see above |
| 3 | `RejectOrder` | Succeed | Correctly-handled invalid order — not a technical failure | *(terminal)* |
| 4 | `ProcessPayment` | Task (Lambda: `process-payment`), with Retry + Catch | Simulated payment; throws on `simulatePaymentFailure=true` | success → `OrderApproved`; exhausted retries → `PaymentFailed` |
| 5 | `OrderApproved` | Succeed | Reached when simulated payment succeeds | *(terminal)* |
| 6 | `PaymentFailed` | Fail | Reached when `ProcessPayment` keeps failing after retries are exhausted | *(terminal)* |

`ChoiceValidOrder` routes through the **Default** branch to `RejectOrder` — this is the safe fallback for any non-valid order, not an explicit `isValid == false` rule.

## Lambda Responsibilities

**`validate-order`** (`lambda/validate_order.py`)
- Input: raw order JSON
- Output: order fields + `{isValid, reason}`
- Never throws for a business-invalid quantity (missing, non-numeric, or `<= 0`) — always returns `isValid: false` with a reason instead.

**`process-payment`** (`lambda/process_payment.py`)
- Input: valid order JSON
- Output on success: order fields + `{status: "payment_approved", processedAt: <ISO 8601 timestamp>}`
- Raises `PaymentProcessingError` when `simulatePaymentFailure` is `true` — the only intentional exception in this project, and the trigger for Retry/Catch.

## Retry / Catch Behavior

Configured only on `ProcessPayment`:

```json
"Retry": [
  {
    "ErrorEquals": ["PaymentProcessingError"],
    "IntervalSeconds": 2,
    "MaxAttempts": 2,
    "BackoffRate": 2.0
  }
],
"Catch": [
  {
    "ErrorEquals": ["PaymentProcessingError"],
    "ResultPath": "$.error",
    "Next": "PaymentFailed"
  }
]
```

`MaxAttempts: 2` means up to two retry attempts *after* the initial invocation (three attempts total) before Catch routes to `PaymentFailed`. Scoped to the named `PaymentProcessingError` (not `States.ALL`) so the demo can point at exactly what's being matched.

## Live Demo Scenarios

**1. Valid order, payment succeeds** (`examples/valid_order_payment_success.json`)
`ValidateOrder` (valid) → `ProcessPayment` (succeeds) → `OrderApproved`.

**2. Invalid order** (`examples/invalid_order.json`)
`ValidateOrder` (invalid) → `ChoiceValidOrder` Default branch → `RejectOrder`. `ProcessPayment` is never invoked — no payment attempt happens for an invalid order.

**3. Valid order, payment fails** (`examples/valid_order_payment_failure.json`)
`ValidateOrder` (valid) → `ProcessPayment` throws → automatic Retry attempts visible in the graph → retries exhausted → Catch → `PaymentFailed`. The only red/failed path in the demo, deliberately reserved for a genuine technical failure — contrast directly against scenario 2's green rejection.

## Repository Structure

```text
step-functions-project/
├── lambda/
│   ├── validate_order.py
│   └── process_payment.py
├── step-functions/
│   └── order_processing.asl.json
├── examples/
│   ├── valid_order_payment_success.json
│   ├── invalid_order.json
│   └── valid_order_payment_failure.json
└── README.md
```

## Presentation Mapping

| Assignment topic | Covered by |
|---|---|
| What Step Functions is | Project Objective + Architecture |
| Problem it solves | Project Objective |
| Architecture / components | Architecture + Workflow States |
| Alternative services | AWS SWF (legacy), EventBridge (event routing, not stateful orchestration), MWAA/Airflow (code-based DAGs), plain Lambda-chaining (no built-in retry/visualization) |
| Advantages | Visual execution history, declarative Retry/Catch, serverless, native AWS integrations |
| Limitations | ASL learning curve, per-transition billing (Standard), execution duration limits, graph density on larger workflows |
| Real-world use case | E-commerce order + payment processing (this demo, generalized) |
| Lessons learned | To be filled in after the AWS Console build and live-demo rehearsal |
| Live demo | Live Demo Scenarios section above |

## Scope Boundaries

**In scope**: one Standard state machine, two Lambdas, Choice branching via Default, Retry+Catch on `ProcessPayment` only, manual console execution with three example inputs, manually-created IAM roles.

**Out of scope**: API Gateway, DynamoDB, S3, SNS, SQS, real payment gateway integration, authentication, CI/CD/IaC, multi-region concerns, idempotency/concurrency handling, automated test suite.

## Deployment Status

**Deployed and verified in AWS.**

- Region: `us-east-1`
- State machine: `OrderProcessingWorkflow` (Standard)
- Execution role: `LabRole`
- `validate-order`: `arn:aws:lambda:us-east-1:121125730756:function:validate-order`
- `process-payment`: `arn:aws:lambda:us-east-1:121125730756:function:process-payment`

`step-functions/order_processing.asl.json` references these real ARNs directly — no placeholders remain.

### Verified Scenarios

**Scenario 1 — Valid order, payment succeeds**
`ValidateOrder → ChoiceValidOrder → ProcessPayment → OrderApproved`
Execution succeeded.

**Scenario 2 — Invalid order (`quantity = 0`)**
`ValidateOrder → ChoiceValidOrder → RejectOrder`
`ProcessPayment` was not invoked. Execution succeeded because rejection is an expected business outcome.

**Scenario 3 — Valid order, simulated payment failure**
`ValidateOrder → ChoiceValidOrder → ProcessPayment → Retry/Catch → PaymentFailed`
Execution failed as designed after payment processing failure.
