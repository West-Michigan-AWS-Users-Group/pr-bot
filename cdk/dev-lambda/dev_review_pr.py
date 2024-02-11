import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    try:
        event_body = json.loads(event["body"])
        logger.info("event: %s", json.dumps(event))
        logger.info('event["body"]: %s', json.dumps(event_body))
    except Exception as e:
        message = f"Lambda function execution failed: {e}"
        logger.error(message)
        return {"statusCode": 500, "body": message}
    return {"statusCode": 200, "body": json.dumps(event)}
