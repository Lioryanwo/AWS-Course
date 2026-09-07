import json
import math
import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3
import botocore

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
            "Access-Control-Allow-Methods": "OPTIONS,PUT",
        },
        "body": json.dumps(body, default=str),
    }


def lambda_handler(event, context):
    order_id = (event.get("pathParameters") or {}).get("orderId")
    if not order_id:
        return _response(400, {"error": "orderId path parameter is required"})

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "Request body must be valid JSON"})

    description = body.get("description")
    price = body.get("price")

    if description is None and price is None:
        return _response(400, {"error": "At least one of 'description' or 'price' must be provided"})
    if description is not None and not isinstance(description, str):
        return _response(400, {"error": "'description' must be a string"})
    if price is not None and not _is_valid_price(price):
        return _response(400, {"error": "'price' must be a finite number"})

    # Attribute names are referenced via placeholders (#name) rather than
    # literally, since several plain-English words used as DynamoDB
    # attribute names (e.g. "description") are on DynamoDB's reserved
    # words list and would otherwise fail with a ValidationException.
    update_expression_parts = ["#lastModifiedDate = :lastModifiedDate"]
    expression_attribute_names = {"#lastModifiedDate": "lastModifiedDate"}
    expression_values = {":lastModifiedDate": datetime.now(timezone.utc).isoformat()}

    if description is not None:
        update_expression_parts.append("#description = :description")
        expression_attribute_names["#description"] = "description"
        expression_values[":description"] = description
    if price is not None:
        update_expression_parts.append("#price = :price")
        expression_attribute_names["#price"] = "price"
        expression_values[":price"] = Decimal(str(price))

    try:
        result = table.update_item(
            Key={"orderId": order_id, "recordType": "ORDER"},
            UpdateExpression="SET " + ", ".join(update_expression_parts),
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_values,
            ConditionExpression="attribute_exists(orderId)",
            ReturnValues="ALL_NEW",
        )
    except botocore.exceptions.ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return _response(404, {"error": f"Order '{order_id}' not found"})
        raise

    return _response(200, result["Attributes"])
