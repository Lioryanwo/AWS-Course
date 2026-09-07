import json
import os

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])
GSI_NAME = os.environ["GSI_NAME"]


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
    params = event.get("queryStringParameters") or {}
    ascending = params.get("order", "asc").lower() != "desc"

    result = table.query(
        IndexName=GSI_NAME,
        KeyConditionExpression=Key("recordType").eq("ORDER"),
        ScanIndexForward=ascending,
    )

    return _response(200, {"orders": result.get("Items", [])})
