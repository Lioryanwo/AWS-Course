import json
import os

import boto3

sns = boto3.client("sns")
TOPIC_ARN = os.environ["TOPIC_ARN"]


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


def _find_subscription_arn(email):
    paginator = sns.get_paginator("list_subscriptions_by_topic")
    for page in paginator.paginate(TopicArn=TOPIC_ARN):
        for subscription in page["Subscriptions"]:
            subscription_arn = subscription["SubscriptionArn"]
            # SNS uses non-ARN sentinel strings for subscriptions that
            # aren't unsubscribable ("PendingConfirmation", "Deleted", and
            # potentially others) - only a real ARN is safe to pass to
            # sns.unsubscribe(), so allowlist the real ARN shape instead of
            # denylisting individual sentinel values.
            if subscription["Endpoint"] == email and subscription_arn.startswith("arn:aws:sns:"):
                return subscription_arn
    return None


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "Request body must be valid JSON"})

    email = body.get("email")
    if not email:
        return _response(400, {"error": "'email' is required"})

    subscription_arn = _find_subscription_arn(email)
    if not subscription_arn:
        return _response(404, {"error": f"No confirmed subscription found for '{email}'"})

    sns.unsubscribe(SubscriptionArn=subscription_arn)

    return _response(200, {"message": f"Unsubscribed '{email}' from notifications"})
