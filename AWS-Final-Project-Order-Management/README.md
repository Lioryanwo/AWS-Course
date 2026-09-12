# Order Management System — Event-Driven Serverless

![Status](https://img.shields.io/badge/status-deployed%20%26%20verified-brightgreen)
![AWS](https://img.shields.io/badge/AWS-serverless-orange)
![Region](https://img.shields.io/badge/region-us--east--1-blue)
![Runtime](https://img.shields.io/badge/lambda-python%203.11-blue)

A serverless, event-driven Order Management System built on API Gateway, Lambda, DynamoDB, DynamoDB Streams, S3, SNS, and CloudWatch, with a static web client hosted on AWS Amplify.

## Live Demo

| | |
|---|---|
| **Client (Amplify)** | https://feature-order-management-system.d3s37t68mari98.amplifyapp.com |
| **API base URL** | `https://b849mbwba8.execute-api.us-east-1.amazonaws.com/prod` |
| **Region** | `us-east-1` |

## Table of Contents

- [Live Demo](#live-demo)
- [Architecture](#architecture)
- [Client (Frontend)](#client-frontend)
- [DynamoDB Key Design](#dynamodb-key-design)
- [Lambda Functions (10 total)](#lambda-functions-10-total)
- [S3 Bucket](#s3-bucket)
- [Freestyle Enhancement: CloudWatch Metrics API](#freestyle-enhancement-cloudwatch-metrics-api)
- [API List](#api-list)
- [Lambda Environment Variables](#lambda-environment-variables)
- [IAM Permissions (`LabRole`)](#iam-permissions-labrole)
- [Deployment Verification Checklist](#deployment-verification-checklist)
- [Building the PDF Lambda Layer](#building-the-pdf-lambda-layer)
- [Repository Structure](#repository-structure)
- [Deployment Status](#deployment-status)

## Architecture

```text
Browser (Amplify-hosted static site)
     |
     v
API Gateway (REST API)
     |
     +--> create_order / get_orders / get_order / update_order / delete_order  --> DynamoDB table "orders"
     |                                                                               |
     |                                                                               v
     |                                                                    DynamoDB Streams (REMOVE events)
     |                                                                               |
     |                                                                               v
     |                                                              process_deleted_order (async consumer)
     |                                                                        /              \
     |                                                                       v                v
     |                                                              S3 backups/*.txt     SNS topic --> confirmed email subscribers
     |
     +--> subscribe_notification / unsubscribe_notification  --> SNS topic (email protocol)
     |
     +--> generate_summary_pdf  --> reads S3 backups/*.txt, writes S3 summaries/*.pdf, returns a pre-signed URL
     |
     +--> get_metrics  --> reads CloudWatch (AWS/Lambda, AWS/ApiGateway built-in metrics)
```

**Why this shape:** deleting an order must never wait on notification or backup. `delete_order` performs a single `DeleteItem` call and returns immediately. The DynamoDB Stream on the `orders` table is the actual event source for everything downstream — `process_deleted_order` is invoked independently, after the delete has already completed and been returned to the client, and handles the S3 backup and SNS publish as two independently-failing steps (a failure in one never suppresses the other).

## Client (Frontend)

Static HTML/CSS/vanilla JS, hosted on AWS Amplify, calling the API above and only the API — no business logic on the client. Beyond the 9 required operations, the UI includes:

- **Dashboard summary cards** — active order count and three of the CloudWatch metrics, computed from data the client already fetches (no extra API calls).
- **Toast notifications + per-section status pills** — every action reports its real HTTP status back to the user, success or failure.
- **Collapsible "API Response" panels** — the raw JSON response is always available (per the assignment's "always display the result returned from the backend" requirement), tucked behind a `<details>` toggle so the UI stays clean.
- **A live API-status badge** in the header, based on the actual result of the initial `GET /orders` and `GET /metrics` calls on page load.
- **Semantic button colors** — creation/subscribe in green, update in amber, delete/unsubscribe in red, informational actions in blue.

## DynamoDB Key Design

**Base table `orders`:**
- Partition key: `orderId` (String, UUID)
- Sort key: `recordType` (String, constant value `"ORDER"` on every item)

**GSI `CreationDateIndex`:**
- Partition key: `recordType` (constant `"ORDER"`)
- Sort key: `creationDate` (ISO 8601 string)
- **Projection type: `ALL`** — required so `get_orders.py`'s `Query` returns complete order records (`price`, `description`, `lastModifiedDate`, etc.), not just key attributes. If the index is created with `KEYS_ONLY` or a partial `INCLUDE` projection instead, `GET /orders` will silently return incomplete items. When creating via CLI, this means passing `Projection={"ProjectionType": "ALL"}` explicitly; via the console, selecting "All" under attribute projections.

**Honest justification, so this isn't overstated:** the base table's sort key (`recordType`) is a structural piece of the composite key, not the mechanism used for chronological ordering. It exists so the table has a genuine, DynamoDB-required sort key rather than a placeholder — and because it's constant across every item, `orderId` alone still functions as a unique identifier in practice, so `Get`/`Update`/`Delete`-by-ID Lambdas can build the full key from just the `orderId` path parameter with no extra lookup. **Chronological sorting for "get all orders sorted by creation date" is provided entirely by the `CreationDateIndex` GSI**, whose own partition+sort key (`recordType` + `creationDate`) is what makes a single, efficient `Query` (not a `Scan`+sort) return orders in date order.

An alternative design — using the real `creationDate` as the base table's sort key — was considered and rejected: it would still require a separate GSI for listing all orders sorted by date (a base-table `Query` only ranges within one partition, i.e. one order), while forcing `Get`/`Update`/`Delete`-by-ID into a two-step Query-then-act flow to first discover the item's `creationDate`. The constant-sort-key design avoids that cost entirely.

## Lambda Functions (10 total)

**9 API-facing Lambdas** (one per REST endpoint, see API list below), plus:

**1 DynamoDB Streams consumer:**
- `process_deleted_order` — triggered by the `orders` table's stream on `REMOVE` events; writes the S3 `.txt` backup and publishes the SNS notification, independently of each other and independently of the API request that caused the delete.

## S3 Bucket

Bucket name must be **globally unique** — use a deterministic suffix such as the AWS account ID, e.g.:

```text
order-management-storage-<AWS_ACCOUNT_ID>
```

Kept fully private (no public access, no bucket policy) with two logical prefixes:
- `backups/{orderId}.txt` — one file per deleted order, written by `process_deleted_order`.
- `summaries/{timestamp}-summary.pdf` — generated PDF summaries, served only via pre-signed URLs returned in the `GET /reports/summary` response body (never a public link).

## Freestyle Enhancement: CloudWatch Metrics API

`GET /metrics` (via `get_metrics.py`) reads **built-in** CloudWatch metrics — no custom `PutMetricData` instrumentation — over a rolling 24-hour window:

| UI label | Source | What it actually measures |
|---|---|---|
| Create API Invocations | `AWS/Lambda` `Invocations` for `create_order` | Number of times the create-order Lambda was invoked |
| Delete API Invocations | `AWS/Lambda` `Invocations` for `delete_order` | Number of times the delete-order Lambda was invoked |
| Lambda Errors | `AWS/Lambda` `Errors`, summed across **all 10** Lambda functions (via `MONITORED_FUNCTION_NAMES`) | Number of Lambda execution errors system-wide, including `process_deleted_order` (not business failures) |
| API 4XX Errors | `AWS/ApiGateway` `4XXError` | Client-error responses at the API Gateway stage |
| API 5XX Errors | `AWS/ApiGateway` `5XXError` | Server-error responses at the API Gateway stage |

Labels are deliberately named after what these built-in metrics *are* (invocation/error counts) rather than implying business outcomes like "Orders Created" or "Orders Deleted" — a Lambda invocation is not the same as a successful business operation, and these metrics can't tell the two apart. The UI renders these as plain stat tiles fetched from this API — no embedded CloudWatch console.

`process_deleted_order` deliberately raises an exception if either the S3 backup or the SNS publish fails (see [Async Failure Handling](#async-failure-handling-process_deleted_order) below), so a failure there is counted in "Lambda Errors" here too, not just visible in CloudWatch Logs.

## API List

| API | Method | Path | Notes |
|---|---|---|---|
| Create order | POST | `/orders` | body: `{description, price}` |
| Get all orders | GET | `/orders?order=asc\|desc` | sorted by creation date via `CreationDateIndex` |
| Get a specific order | GET | `/orders/{orderId}` | |
| Update order | PUT | `/orders/{orderId}` | body: `{description?, price?}` |
| Delete order | DELETE | `/orders/{orderId}` | returns immediately; backup/notify run async |
| Subscribe to notifications | POST | `/subscriptions` | body: `{email}` |
| Unsubscribe from notifications | POST | `/subscriptions/unsubscribe` | body: `{email}` |
| Generate deleted-orders summary PDF | GET | `/reports/summary` | returns `{url, deletedOrderCount}` |
| Get system metrics (freestyle) | GET | `/metrics` | returns `{windowHours, metrics}` |

See [examples/sample-requests.http](examples/sample-requests.http) for full sample request/response bodies (source for the deliverable doc's API table).

**Note on Unsubscribe:** a `404 "No confirmed subscription found"` is expected — not a bug — when the given email was never subscribed, was already unsubscribed, or is still in SNS's `PendingConfirmation` state (an unconfirmed subscription has no real `SubscriptionArn`, and SNS provides no API to cancel one). It only auto-resolves by the user confirming it or by SNS's ~3-day auto-expiry. `unsubscribe_notification.py` allowlists only real `arn:aws:sns:` ARNs when searching for a match, so a confirmed subscription unsubscribes cleanly with a `200`.

## Lambda Environment Variables

| Lambda | Required environment variables |
|---|---|
| `create_order`, `get_order`, `update_order`, `delete_order` | `TABLE_NAME` |
| `get_orders` | `TABLE_NAME`, `GSI_NAME` (`CreationDateIndex`) |
| `process_deleted_order` | `BUCKET_NAME`, `TOPIC_ARN` |
| `subscribe_notification`, `unsubscribe_notification` | `TOPIC_ARN` |
| `generate_summary_pdf` | `BUCKET_NAME` |
| `get_metrics` | `CREATE_ORDER_FUNCTION_NAME`, `DELETE_ORDER_FUNCTION_NAME`, `MONITORED_FUNCTION_NAMES` (comma-separated list of **all 10** deployed Lambda function names, so "Lambda Errors" is accurate system-wide), `API_GATEWAY_NAME`, `API_GATEWAY_STAGE` |

## IAM Permissions (`LabRole`)

Every Lambda runs under the AWS Academy Learner Lab's `LabRole`. The table below lists exactly what each function needs — verify these are actually granted before deploying, since a generically-scoped `LabRole` is not guaranteed to cover all of them (SNS and CloudWatch actions in particular are easy to miss).

| Lambda | Required permissions |
|---|---|
| `create_order` | `dynamodb:PutItem` on the `orders` table |
| `get_orders` | `dynamodb:Query` on the `CreationDateIndex` GSI |
| `get_order` | `dynamodb:GetItem` on the `orders` table |
| `update_order` | `dynamodb:UpdateItem` on the `orders` table |
| `delete_order` | `dynamodb:DeleteItem` on the `orders` table |
| `process_deleted_order` | `dynamodb:GetRecords`, `dynamodb:GetShardIterator`, `dynamodb:DescribeStream`, `dynamodb:ListStreams` on the table's stream (usually granted via the `AWSLambdaDynamoDBExecutionRole` managed policy attached to the event source mapping's execution role); `s3:PutObject` on `backups/*` in the bucket; `sns:Publish` on the topic |
| `subscribe_notification` | `sns:Subscribe` on the topic |
| `unsubscribe_notification` | `sns:ListSubscriptionsByTopic`, `sns:Unsubscribe` on the topic |
| `generate_summary_pdf` | `s3:ListBucket` (scoped to the `backups/` prefix), `s3:GetObject` on `backups/*`, `s3:PutObject` on `summaries/*`, **and `s3:GetObject` on `summaries/*`** — this last one is easy to miss: it isn't needed to *generate* the pre-signed URL, only for that URL to actually succeed when a client uses it, since the URL is authorized against the Lambda role's live permissions at request time, not frozen at generation time |
| `get_metrics` | `cloudwatch:GetMetricStatistics` (or `ListMetrics` if diagnosing missing data) |
| All 10 functions | `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` (standard Lambda execution logging) |

## Deployment Verification Checklist

### DynamoDB Streams (`process_deleted_order`)

This is the single point of failure for both the notification (10 pts) and backup (5 pts) requirements — a misconfiguration here fails silently (deletes keep succeeding; nothing downstream happens). Verify all of the following after deployment, in order:

1. **Streams are enabled** on the `orders` table (`aws dynamodb describe-table` → `StreamSpecification.StreamEnabled: true`).
2. **`StreamViewType` is `OLD_IMAGE` or `NEW_AND_OLD_IMAGES`** — `NEW_IMAGE`-only or `KEYS_ONLY` will make `process_deleted_order.py` log a `missing_old_image` warning and skip every deletion (no backup, no notification, no error raised).
3. **The Lambda event source mapping exists** between the table's stream and `process_deleted_order` (`aws lambda list-event-source-mappings --function-name process_deleted_order`) — enabling Streams on the table does **not** automatically create this; it's a separate resource.
4. **The mapping's `State` is `Enabled`** (not `Creating`, `Disabled`, or `Failed` — a `Failed` state usually means the execution role lacks the stream-read permissions listed above).
5. **A real end-to-end delete test** — delete an order via the API and confirm *both*: a new `backups/{orderId}.txt` object appears in S3, and a notification email arrives at a confirmed subscriber address. Passing steps 1–4 doesn't guarantee step 5 works (e.g. wrong `BUCKET_NAME`/`TOPIC_ARN` env values would still let the mapping be `Enabled` while every invocation fails) — this is the only step that actually proves the pipeline works.

### API Gateway CORS

The web client calls `POST`/`PUT`/`DELETE` endpoints from a different origin (the Amplify domain), which triggers a browser CORS preflight (`OPTIONS`) request. None of the 9 Lambdas handle `OPTIONS` themselves — this must be handled at the API Gateway level:

1. For **every** resource (`/orders`, `/orders/{orderId}`, `/subscriptions`, `/subscriptions/unsubscribe`, `/reports/summary`, `/metrics`), enable CORS (API Gateway's "Enable CORS" action, which adds an `OPTIONS` method backed by a `MOCK` integration returning the appropriate `Access-Control-Allow-*` headers).
2. Redeploy the API stage after enabling CORS — it does not take effect until deployed.
3. Verify from the browser, not just `curl`/Postman: `curl` doesn't send preflight requests, so a resource can appear to work in manual testing while still being broken for the actual web client. Test each non-GET action (create, update, delete, subscribe, unsubscribe) from the deployed Amplify site itself.

### Async Failure Handling (`process_deleted_order`)

`process_deleted_order.py` always attempts both the S3 backup and the SNS publish independently (one failing never prevents the other from being attempted), logs the full exception with order-level context for each failure via CloudWatch Logs, and then raises after both attempts if either failed — so the invocation is counted as a Lambda error (visible in `GET /metrics`'s "Lambda Errors" tile) and the Streams poller will retry the batch, instead of the failure being silently absorbed.

## Building the PDF Lambda Layer

`generate_summary_pdf` needs `reportlab`, which isn't in the Lambda runtime by default:

```bash
pip install -r lambda-layer/requirements.txt -t lambda-layer/python
cd lambda-layer && zip -r ../lambda-layer.zip python && cd ..
```

Publish `lambda-layer.zip` as a Lambda Layer and attach it to `generate_summary_pdf`.

## Repository Structure

```text
AWS-Final-Project-Order-Management/
├── lambda/
│   ├── create_order.py
│   ├── get_orders.py
│   ├── get_order.py
│   ├── update_order.py
│   ├── delete_order.py
│   ├── process_deleted_order.py
│   ├── subscribe_notification.py
│   ├── unsubscribe_notification.py
│   ├── generate_summary_pdf.py
│   └── get_metrics.py
├── lambda-layer/
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── examples/
│   └── sample-requests.http
└── README.md
```

## Deployment Status

**Deployed and manually verified in AWS.**

- Region: `us-east-1`
- Client (Amplify): https://feature-order-management-system.d3s37t68mari98.amplifyapp.com
- API Gateway: `https://b849mbwba8.execute-api.us-east-1.amazonaws.com/prod`

### Verified flows

- Create Order, Get All Orders, Get Specific Order, Update Order, Delete Order
- SNS deletion-notification email delivery
- Deleted order appears correctly in the generated PDF; PDF generation and download both work
- Amplify frontend exercising every action against the live API
- CloudWatch metrics rendering correctly in the frontend
- Subscribe, confirmed via the SNS confirmation email
- Unsubscribe of a confirmed subscription; the `404` for an unconfirmed/nonexistent one is expected behavior, not a bug (see [API List](#api-list))
