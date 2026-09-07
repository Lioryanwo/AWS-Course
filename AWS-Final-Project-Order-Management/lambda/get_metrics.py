import json
import os
from datetime import datetime, timedelta, timezone

import boto3

cloudwatch = boto3.client("cloudwatch")

CREATE_ORDER_FUNCTION_NAME = os.environ["CREATE_ORDER_FUNCTION_NAME"]
DELETE_ORDER_FUNCTION_NAME = os.environ["DELETE_ORDER_FUNCTION_NAME"]
# All 10 Lambda function names (the 9 API-facing functions plus
# process_deleted_order), so "Lambda Errors" genuinely covers every
# function in the system rather than only a subset of it.
MONITORED_FUNCTION_NAMES = os.environ["MONITORED_FUNCTION_NAMES"].split(",")
API_GATEWAY_NAME = os.environ["API_GATEWAY_NAME"]
API_GATEWAY_STAGE = os.environ["API_GATEWAY_STAGE"]

WINDOW_HOURS = 24


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,GET",
        },
        "body": json.dumps(body),
    }


def _sum_metric(namespace, metric_name, dimensions, start, end):
    result = cloudwatch.get_metric_statistics(
        Namespace=namespace,
        MetricName=metric_name,
        Dimensions=dimensions,
        StartTime=start,
        EndTime=end,
        Period=WINDOW_HOURS * 3600,
        Statistics=["Sum"],
    )
    datapoints = result.get("Datapoints", [])
    return int(sum(dp["Sum"] for dp in datapoints)) if datapoints else 0


def lambda_handler(event, context):
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=WINDOW_HOURS)

    try:
        create_invocations = _sum_metric(
            "AWS/Lambda", "Invocations",
            [{"Name": "FunctionName", "Value": CREATE_ORDER_FUNCTION_NAME}],
            start, end,
        )
        delete_invocations = _sum_metric(
            "AWS/Lambda", "Invocations",
            [{"Name": "FunctionName", "Value": DELETE_ORDER_FUNCTION_NAME}],
            start, end,
        )
        lambda_errors = sum(
            _sum_metric(
                "AWS/Lambda", "Errors",
                [{"Name": "FunctionName", "Value": function_name}],
                start, end,
            )
            for function_name in MONITORED_FUNCTION_NAMES
        )
        api_4xx = _sum_metric(
            "AWS/ApiGateway", "4XXError",
            [{"Name": "ApiName", "Value": API_GATEWAY_NAME}, {"Name": "Stage", "Value": API_GATEWAY_STAGE}],
            start, end,
        )
        api_5xx = _sum_metric(
            "AWS/ApiGateway", "5XXError",
            [{"Name": "ApiName", "Value": API_GATEWAY_NAME}, {"Name": "Stage", "Value": API_GATEWAY_STAGE}],
            start, end,
        )
    except Exception as exc:
        return _response(502, {"error": f"Failed to read CloudWatch metrics: {exc}"})

    # Labels reflect what these metrics actually measure (Lambda/API Gateway
    # invocation and error counts), not business outcomes like successful
    # order creations/deletions, which these metrics cannot distinguish.
    return _response(200, {
        "windowHours": WINDOW_HOURS,
        "metrics": {
            "Create API Invocations": create_invocations,
            "Delete API Invocations": delete_invocations,
            "Lambda Errors": lambda_errors,
            "API 4XX Errors": api_4xx,
            "API 5XX Errors": api_5xx,
        },
    })
