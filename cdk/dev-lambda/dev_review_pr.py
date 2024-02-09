import json

def handler(event, context):
    # Your Lambda function logic here
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }