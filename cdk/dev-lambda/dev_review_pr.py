import json
from github import Auth, Github, PullRequest
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    try:
        github_webhook = json.loads(event["body"])
        logger.info("event: %s", json.dumps(event))
        logger.info('event["body"]: %s', json.dumps(github_webhook))
    except Exception as e:
        message = f"Lambda function execution failed: {e}"
        logger.error(message)
        return {"statusCode": 500, "body": message}

    auth = Auth.Token("placeholder")
    g = Github(auth=auth)
    pr_number = 2
    repo = g.get_repo("West-Michigan-AWS-Users-Group/pr-bot")
    pr = repo.get_pull(pr_number)
    pr.create_issue_comment("Test comment from pr-bot development environment")
    
    return {"statusCode": 200, "body": json.dumps(event)}
