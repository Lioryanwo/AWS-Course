import json
import os

import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,GET",
        },
        "body": json.dumps(body, default=str),
    }


def lambda_handler(event, context):
    order_id = (event.get("pathParameters") or {}).get("orderId")
    if not order_id:
        return _response(400, {"error": "orderId path parameter is required"})

    result = table.get_item(Key={"orderId": order_id, "recordType": "ORDER"})
    item = result.get("Item")

    if not item:
        return _response(404, {"error": f"Order '{order_id}' not found"})

    return _response(200, item)
