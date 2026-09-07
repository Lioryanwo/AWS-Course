import json
import os
from datetime import datetime, timezone
from io import BytesIO

import boto3
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

s3 = boto3.client("s3")
BUCKET_NAME = os.environ["BUCKET_NAME"]
PRESIGNED_URL_EXPIRY_SECONDS = 900


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


def _list_backup_keys():
    keys = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix="backups/"):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys


def _read_backup(key):
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
    return obj["Body"].read().decode("utf-8")


def _build_pdf(entries):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 50

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "Deleted Orders Summary")
    y -= 30
    pdf.setFont("Helvetica", 10)

    if not entries:
        pdf.drawString(50, y, "No deleted orders found.")
    else:
        for entry in entries:
            for line in entry.splitlines():
                if y < 50:
                    pdf.showPage()
                    pdf.setFont("Helvetica", 10)
                    y = height - 50
                pdf.drawString(50, y, line)
                y -= 14
            y -= 14

    pdf.save()
    buffer.seek(0)
    return buffer.read()


def lambda_handler(event, context):
    keys = _list_backup_keys()
    entries = [_read_backup(key) for key in keys]

    pdf_bytes = _build_pdf(entries)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    summary_key = f"summaries/{timestamp}-summary.pdf"

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=summary_key,
        Body=pdf_bytes,
        ContentType="application/pdf",
    )

    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET_NAME, "Key": summary_key},
        ExpiresIn=PRESIGNED_URL_EXPIRY_SECONDS,
    )

    return _response(200, {"url": url, "deletedOrderCount": len(entries)})
