import json
import logging
import os

import boto3
from boto3.dynamodb.types import TypeDeserializer

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
sns = boto3.client("sns")

BUCKET_NAME = os.environ["BUCKET_NAME"]
TOPIC_ARN = os.environ["TOPIC_ARN"]

_deserializer = TypeDeserializer()


def _deserialize(image):
    return {key: _deserializer.deserialize(value) for key, value in image.items()}


def lambda_handler(event, context):
    failures = []

    for record in event.get("Records", []):
        if record.get("eventName") != "REMOVE":
            continue

        old_image = record["dynamodb"].get("OldImage")
        if not old_image:
            logger.warning(json.dumps({
                "event": "missing_old_image",
                "message": (
                    "REMOVE record had no OldImage; the table's DynamoDB "
                    "Stream must use OLD_IMAGE or NEW_AND_OLD_IMAGES."
                ),
            }))
            continue

        order = _deserialize(old_image)
        order_id = order.get("orderId")

        # Each side effect is attempted independently - a failure in one
        # (e.g. S3 down) must never prevent attempting the other (e.g. SNS).
        backup_ok = _backup_to_s3(order, order_id)
        notify_ok = _notify_subscribers(order, order_id)

        if not backup_ok or not notify_ok:
            failures.append({
                "orderId": order_id,
                "backupOk": backup_ok,
                "notifyOk": notify_ok,
            })

    if failures:
        # Raising surfaces this invocation as a Lambda "Error" in CloudWatch
        # (the AWS/Lambda Errors metric that get_metrics.py reads) and lets
        # the DynamoDB Streams poller retry the batch, instead of the
        # failure being silently absorbed with no visibility or retry.
        logger.error(json.dumps({"event": "process_deleted_order_failed", "failures": failures}))
        raise RuntimeError(f"process_deleted_order had {len(failures)} failure(s): {failures}")

    return {"statusCode": 200}


def _backup_to_s3(order, order_id):
    try:
        content = "\n".join(f"{key}: {value}" for key, value in order.items())
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=f"backups/{order_id}.txt",
            Body=content.encode("utf-8"),
            ContentType="text/plain",
        )
        return True
    except Exception:
        logger.error(
            json.dumps({
                "event": "s3_backup_failed",
                "orderId": order_id,
                "bucket": BUCKET_NAME,
            }),
            exc_info=True,
        )
        return False


def _notify_subscribers(order, order_id):
    try:
        message = (
            f"Order {order_id} was deleted.\n\n"
            + "\n".join(f"{key}: {value}" for key, value in order.items())
        )
        sns.publish(
            TopicArn=TOPIC_ARN,
            Subject=f"Order {order_id} deleted",
            Message=message,
        )
        return True
    except Exception:
        logger.error(
            json.dumps({
                "event": "sns_notify_failed",
                "orderId": order_id,
                "topicArn": TOPIC_ARN,
            }),
            exc_info=True,
        )
        return False
