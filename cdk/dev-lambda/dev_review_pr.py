import json
import logging
import os
import urllib.request

import boto3
from botocore.config import Config
from github import Auth, Github, PullRequest
from langchain.llms.bedrock import Bedrock
from langchain.prompts import PromptTemplate

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get environment variable
env_var_value = os.environ.get("GITHUB_TOKEN")
env_var_dict = json.loads(env_var_value)
github_token = env_var_dict.get("GITHUB_TOKEN")


def get_bedrock_client():
    """
    Set up the boto3 bedrock client
    """
    retry_config = Config(
        region_name="us-west-2",
        retries={
            "max_attempts": 20,
            "mode": "standard",
        },
    )
    client_kwargs = {"region_name": "us-west-2"}
    session = boto3.Session(**client_kwargs)
    bedrock_client = session.client(
        service_name="bedrock-runtime", config=retry_config, **client_kwargs
    )
    logger.info("bedrock client created successfully")
    return bedrock_client


def format_diff(diff: str) -> str:
    """
    Format the diff to be used in the prompt by stripping out problematic strings such as Human, Assistant, Diff, etc.
    diff: str: Multi-line GitHub diff output from a pull request.

    """
    # Remove exact strings
    for removal in ["```", "Human", "Assistant", "diff", "</diff>", "<diff>", "```"]:
        diff = diff.replace(removal, "")
    # Strip leading and trailing whitespace
    diff = diff.strip()
    # Parse lines for the diff that are problematic
    lines = diff.split("\n")
    # Remove json serialized string in the diff, or else the LLM hangs
    filtered_lines = [line for line in lines if not line.startswith('+    "body": "{')]
    diff = "\n".join(filtered_lines)
    logger.info("diff formatted successfully")
    return diff


def prompt_bedrock(diff_code: str, source_ref: str, target_ref: str) -> str:
    """
    Generate a prompt for the Bedrock API
    diff_code: str: Multi-line GitHub diff output from a pull request.
    source_ref: str: The source branch of the pull request.
    target_ref: str: The target branch of the pull request.
    """

    # Bedrock configuration values
    inference_modifier = {
        "max_tokens_to_sample": 4096,
        "temperature": 0.5,
        "top_k": 250,
        "top_p": 1,
        "stop_sequences": ["\n\nHuman"],
    }

    textgen_llm = Bedrock(
        model_id="anthropic.claude-v2:1",
        client=get_bedrock_client(),
        model_kwargs=inference_modifier,
    )

    pr_review_prompt = PromptTemplate(
        input_variables=["diff", "source_branch", "target_branch"],
        template="""

Human: You are being provided a diff of code changes in a PR. The diff needs to be reviewed for any potential issues.

The diff is provided below between the diff tags.

<diff>
{diff}
</diff>

The diff needs to be summarized in 10 bullet points or less. Do not put a blank line between
each bullet point.
The summary should include the following:
- What is being changed and try to infer why
- Any code formatting issues. If the language is Python, be sure to mention any PEP8 violations or other style guide violations
- Any potential issues with the code changes that are identified

If there are less than 10 bullet points, that is okay. If there are more than 10 bullet points, please summarize the 
most important points. Post this message in markdown formatting. At the start of the response, please include source
branch and target branch of the PR in the following format:
 
"## `{source_branch}` --> `{target_branch}` "

Be sure to include the arrow between the source and target branches and make this a Heading2 in markdown.

At the bottom of your response, be sure to indicate this is an auto-generated comment using the exact phrase below, 
without quotes and ensure it is italicised.

"This is an automated comment from PrBot."


Assistant:""",
    )

    prompt = pr_review_prompt.format(
        diff=diff_code, source_branch=source_ref, target_branch=target_ref
    )
    logger.info("prompt generated successfully")
    logger.debug("prompt: %s", prompt)
    response = textgen_llm(prompt)

    return response


def authenticate_github(auth_token: str) -> Github:
    logger.info("attempting to authenticate: %s")
    auth = Auth.Token(auth_token)
    try:
        g = Github(auth=auth)
        logger.info("authenticated successfully")
    except Exception as e:
        message = f"Error authenticating with Github: {e}"
        logger.error(message)
        raise Exception(message)
    return g


def get_diff_from_pr(pr_diff_url: str, gh_token: str) -> str:
    """
    Get the diff from a pull request using the GitHub API
    :param pr_diff_url:
    :param gh_token:
    :return:
    """
    headers = {
        "Accept": "application/vnd.github.v3.diff",
        "Authorization": f"Bearer {gh_token}",
    }
    request = urllib.request.Request(pr_diff_url, headers=headers)
    response = urllib.request.urlopen(request)
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
        if github_webhook["action"] == "opened":
            logger.info("action: %s", github_webhook["action"])
            try:
                pr_number = github_webhook["number"]
                logger.info("pr_number: %s", pr_number)
                repo_name = github_webhook["repository"]["full_name"]
                logger.info("repo: %s", repo_name)
                pr_diff_url = github_webhook["pull_request"]["url"] + ".diff"
                source_ref = github_webhook["pull_request"]["head"]["ref"]
                target_ref = github_webhook["pull_request"]["base"]["ref"]
                logger.info("pr_diff_url: %s", pr_diff_url)
            except Exception as e:
                message = f"Error assigning required values to python variables: {e}"
                logger.error(message)
                return {"statusCode": 500, "body": message}

            # fetch diff url contents
            try:
                diff = get_diff_from_pr(pr_diff_url, github_token)
                # replace the exact string Human and Assistant with empty string to prevent LLM confusion
                logger.info("diff fetched successfully")
                diff = format_diff(diff)
                logger.info("diff formatted output: \n%s", diff)
            except Exception as e:
                message = f"Error fetching diff url: {e}"
                logger.error(message)
                return {"statusCode": 500, "body": message}

            try:
                logger.info("Prompting bedrock with diff.")
                bedrock_response = prompt_bedrock(diff, source_ref, target_ref)
                logger.info("bedrock response: %s", bedrock_response)
            except Exception as e:
                message = f"Error generating bedrock response: {e}"
                logger.error(message)
                return {"statusCode": 500, "body": message}

            # auth with github and post comment to pr
            try:
                g_session = authenticate_github(github_token)
                repo = g_session.get_repo(repo_name)
                pr = repo.get_pull(pr_number)
                logger.info("pr: %s", pr)
                post_comment_to_pr(
                    pr,
                    bedrock_response,
                )
            except Exception as e:
                message = f"Error posting comment to pr: {e}"
                logger.error(message)
                return {"statusCode": 500, "body": message}

            logger.info("Comment posted to PR successfully.")
            return {"statusCode": 200, "body": "Comment posted to PR successfully."}
        else:
            logger.info("pull_request action != opened, so no further action is taken.")
            return {"statusCode": 200, "body": json.dumps(event)}
    else:
        logger.info("No pull_request action found in the webhook")
        return {"statusCode": 200, "body": json.dumps(event)}
