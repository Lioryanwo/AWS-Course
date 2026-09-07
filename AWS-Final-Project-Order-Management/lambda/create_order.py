import json
import math
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


def _is_valid_price(price):
    # bool is a subclass of int in Python, so isinstance(True, (int, float))
    # is True - reject it explicitly. Also reject NaN/Infinity, which pass
    # isinstance checks but DynamoDB rejects when writing the Decimal.
    if isinstance(price, bool):
        return False
    if not isinstance(price, (int, float)):
        return False
    return math.isfinite(price)


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST",
        },
        "body": json.dumps(body, default=str),
    }


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "Request body must be valid JSON"})

    description = body.get("description")
    price = body.get("price")

    if not description or not isinstance(description, str):
        return _response(400, {"error": "'description' is required and must be a string"})
    if price is None or not _is_valid_price(price):
        return _response(400, {"error": "'price' is required and must be a finite number"})

    now = datetime.now(timezone.utc).isoformat()
    order = {
        "orderId": str(uuid.uuid4()),
        "recordType": "ORDER",
        "creationDate": now,
        "lastModifiedDate": now,
        "price": Decimal(str(price)),
        "description": description,
    }

    table.put_item(Item=order)

    return _response(201, order)
