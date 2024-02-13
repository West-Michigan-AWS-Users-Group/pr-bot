import json
import logging
import os
import urllib.request

from github import Auth, Github, PullRequest

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get environment variable
env_var_value = os.environ.get("GITHUB_TOKEN")
env_var_dict = json.loads(env_var_value)
github_token = env_var_dict.get("GITHUB_TOKEN")


def authenticate_github(auth_token: str) -> Github:
    auth = Auth.Token(auth_token)
    logger.info("auth: %s", auth)
    try:
        g = Github(auth=auth)
    except Exception as e:
        message = f"Error authenticating with Github: {e}"
        logger.error(message)
        raise Exception(message)
    return g


def get_diff_from_pr(pr_diff_url: str) -> str:
    response = urllib.request.urlopen(pr_diff_url)
    content = response.read()
    decoded_content = content.decode("utf-8")
    return decoded_content


def post_comment_to_pr(pr: PullRequest, comment: str) -> None:
    pr.create_issue_comment(comment)


def handler(event, context):
    try:
        github_webhook = json.loads(event["body"])
        logger.info("event: %s", json.dumps(event))
        logger.info('event["body"]: %s', json.dumps(github_webhook))
    except Exception as e:
        message = f"Error parsing webhook body: {e}"
        logger.error(message)
        return {"statusCode": 500, "body": message}

    if pull_request_event := github_webhook.get("pull_request"):
        logger.info("pull_request_event: %s", pull_request_event)
        # assign required values to python variables
        try:
            pr_number = github_webhook["number"]
            logger.info("pr_number: %s", pr_number)
            repo_name = github_webhook["repository"]["full_name"]
            logger.info("repo: %s", repo_name)
            pr_diff_url = github_webhook["pull_request"]["diff_url"]
            logger.info("pr_diff_url: %s", pr_diff_url)
        except Exception as e:
            message = f"Error assigning required values to python variables: {e}"
            logger.error(message)
            return {"statusCode": 500, "body": message}

        # fetch diff url
        try:
            diff = get_diff_from_pr(pr_diff_url)
            logger.info("diff: %s", diff)
        except Exception as e:
            message = f"Error fetching diff url: {e}"
            logger.error(message)
            return {"statusCode": 500, "body": message}

        # auth with github and post comment to pr
        try:
            g_session = authenticate_github(github_token)
            pr = g_session.get_pull(pr_number)
            post_comment_to_pr(pr, "Test comment from pr-bot development environment")
        except Exception as e:
            message = f"Error posting comment to pr: {e}"
            logger.error(message)
            return {"statusCode": 500, "body": message}

        logger.info("Comment posted to PR successfully.")
        return {"statusCode": 200, "body": "Comment posted to PR successfully."}
    else:
        logger.info("No pull_request event found in the webhook")
        return {"statusCode": 200, "body": json.dumps(event)}
