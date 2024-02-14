import json
from botocore.config import Config
import boto3
import logging
import os
import urllib.request

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
            "max_attempts": 10,
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


def prompt_bedrock(diff_code: str) -> str:
    """
    Generate a prompt for the Bedrock API
    diff_code: str: Multi-line GitHub diff output from a pull request.

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
        model_id="anthropic.claude-v2",
        client=get_bedrock_client(),
        model_kwargs=inference_modifier,
    )

    pr_review_prompt = PromptTemplate(
        input_variables=["diff"],
        template="""


Human: You are being provided a diff of code changes in a PR. The diff needs to be reviewed for any potential issues.
The diff needs to be summarized in 10 bullet points or less. The summary should include the following:
- What is being changed and try to infer why
- Any code formatting issues. If the language is Python, be sure to mention any PEP8 violations
- Any potential issues with the code changes that are identified

If there are less than 10 bullet points, that is okay. If there are more than 10 bullet points, please summarize the 
most important points. Post this message in markdown formatting. At the start of the respsonse, please include source
 branch and target branch of the PR in the following format:
 
" <source_branch> --> <target_branch> "

Be sure to include the arrow between the source and target branches and make this a Heading2 in markdown.

At the bottom of your response, be sure to indicate
that this is an auto-generated comment using the exact phrase below, without quotes and ensure it is italicised.

"This is an automated comment from PrBot."

<diff>
{diff}
</diff>


Assistant: """,
    )

    prompt = pr_review_prompt.format(diff=diff_code)
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

        # fetch diff url contents
        try:
            diff = get_diff_from_pr(pr_diff_url)
            logger.info("diff fetched successfully: %s", diff)
        except Exception as e:
            message = f"Error fetching diff url: {e}"
            logger.error(message)
            return {"statusCode": 500, "body": message}

        try:
            logger.info("Prompting bedrock with diff.")
            bedrock_response = prompt_bedrock(diff)
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
        logger.info("No pull_request event found in the webhook")
        return {"statusCode": 200, "body": json.dumps(event)}
