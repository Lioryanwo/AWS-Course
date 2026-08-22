def lambda_handler(event, context):
    quantity = event.get("quantity")

    is_valid = (
        isinstance(quantity, (int, float))
        and not isinstance(quantity, bool)
        and quantity >= 1
    )

    result = dict(event)
    result["isValid"] = is_valid
    result["reason"] = (
        None if is_valid else "Quantity must be greater than or equal to 1"
    )
    return result
