import json
import os
import re

import boto3

sns = boto3.client("sns")
TOPIC_ARN = os.environ["TOPIC_ARN"]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST",
        },
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "Request body must be valid JSON"})

    email = body.get("email")
    if not email or not EMAIL_RE.match(email):
        return _response(400, {"error": "A valid 'email' is required"})

    sns.subscribe(TopicArn=TOPIC_ARN, Protocol="email", Endpoint=email)

    return _response(200, {
        "message": f"Confirmation email sent to {email}. Notifications begin only after the link in that email is confirmed.",
    })
