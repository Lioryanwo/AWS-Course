import datetime


class PaymentProcessingError(Exception):
    """Raised to simulate a downstream payment processing failure."""


def lambda_handler(event, context):
    if event.get("simulatePaymentFailure"):
        raise PaymentProcessingError("Simulated payment processing failure")

    result = dict(event)
    result["status"] = "payment_approved"
    result["processedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    return result
