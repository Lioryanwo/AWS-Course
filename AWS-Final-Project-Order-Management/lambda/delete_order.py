import json
import os

import boto3
import botocore

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,DELETE",
        },
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    order_id = (event.get("pathParameters") or {}).get("orderId")
    if not order_id:
        return _response(400, {"error": "orderId path parameter is required"})

    # Only deletes the DynamoDB item and returns. The S3 backup and SNS
    # notification are handled asynchronously by process_deleted_order.py,
    # triggered by the table's DynamoDB Stream, so neither side effect can
    # delay or block this response.
    try:
        table.delete_item(
            Key={"orderId": order_id, "recordType": "ORDER"},
            ConditionExpression="attribute_exists(orderId)",
        )
    except botocore.exceptions.ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return _response(404, {"error": f"Order '{order_id}' not found"})
        raise

    return _response(200, {"message": f"Order '{order_id}' deleted"})
