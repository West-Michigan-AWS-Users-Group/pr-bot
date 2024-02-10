import json
import logging

logger = logging.getLogger()
logger.setLevel('INFO')


def handler(event, context):
    try:
        logger.info('Event data: ' + json.dumps(event))
    except Exception as e:
        message = f'Lambda function execution failed: {e}'
        logger.error(message)
        return {
            'statusCode': 500,
            'body': message
        }
    return {
        'statusCode': 200,
        'body': json.dumps(event)
    }