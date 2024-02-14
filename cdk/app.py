#!/usr/bin/env python3
import os
import subprocess

from aws_cdk import (
    aws_apigatewayv2,
    aws_apigatewayv2_integrations,
    aws_lambda,
    aws_iam,
    Stack,
    SecretValue,
    Tags,
    Environment,
    App,
)
from constructs import Construct

stack_name_short = "PrBot"
layer_path = "layers/prbot-layer.zip"
deployed_environments = ["dev", "prod"]


def create_layer_zip():
    """
    Create a zip file of the layer using the create-layer-docker.sh script.
    Saves a zip file to the layers directory.
    returns the path to the zip file.
    :return:
    """
    try:
        result = subprocess.run(
            ["/bin/bash", "./create-layer-docker.sh"],
            check=True,
            text=True,
            capture_output=True,
        )
        print("Script output:", result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error executing script:", e)
        print("Script output (if any):", e.output)


class PrBot(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        if "dev" in id:
            lambda_handler = "dev_review_pr.handler"
            stack_environment = "dev"
        elif "prod" in id:
            lambda_handler = "prod_review_pr.handler"
            stack_environment = "prod"
        else:
            lambda_handler = None
            stack_environment = None
            raise ValueError(f"Invalid environment value declared for stack {id}.")

        pypi_layer = aws_lambda.LayerVersion(
            self,
            id=f"{id}prReviewPypiLayer",
            code=aws_lambda.Code.from_asset(
                path=layer_path,
            ),
            compatible_runtimes=[aws_lambda.Runtime.PYTHON_3_11],
            description="LangChain dependency",
        )

        # Define the Lambda function
        review_pr = aws_lambda.Function(
            self,
            f"{id}reviewPr",
            code=aws_lambda.Code.from_asset(
                f"{stack_environment}-lambda",
            ),
            environment={
                "GITHUB_TOKEN": SecretValue.secrets_manager(
                    f"/{stack_environment}/{stack_name_short}/GITHUB_TOKEN",
                ).unsafe_unwrap(),
            },
            handler=lambda_handler,
            layers=[pypi_layer],
            runtime=aws_lambda.Runtime.PYTHON_3_11,
        )

        # Add policy allowing access to AWS bedrock
        review_pr.add_to_role_policy(
            statement=aws_iam.PolicyStatement(
                actions=[
                    "bedrock:*",
                ],
                resources=["*"],
            )
        )

        webhook_api = aws_apigatewayv2.HttpApi(
            self,
            f"{id}webhookApi",
            create_default_stage=True,
            description="Webhook API for PR review",
        )

        webhook_api.add_stage(
            f"{id}webhookApiStage",
            stage_name="live",
            auto_deploy=True,
        )

        pr_review_integration = aws_apigatewayv2_integrations.HttpLambdaIntegration(
            f"{id}webhookApiPrReviewIntegration", review_pr
        )

        webhook_api.add_routes(
            path="/pr-review",
            methods=[aws_apigatewayv2.HttpMethod.POST],
            integration=pr_review_integration,
        )


app = App()

for environment in deployed_environments:
    stack_name_l = f"{environment}{stack_name_short}"
    create_layer_zip()
    prbot_stack = PrBot(
        app,
        stack_name_l,
        # If you don't specify 'env', this stack will be environment-agnostic.
        # Account/Region-dependent features and context lookups will not work,
        # but a single synthesized template can be deployed anywhere.
        # Uncomment the next line to specialize this stack for the AWS Account
        # and Region that are implied by the current CLI configuration.
        # env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
        # Uncomment the next line if you know exactly what Account and Region you
        # want to deploy the stack to. */
        env=Environment(account=os.getenv("AWS_ACCOUNT_NUMBER"), region="us-west-2"),
        # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
    )
    Tags.of(prbot_stack).add("environment", environment)
    Tags.of(prbot_stack).add("stack", stack_name_l)
    Tags.of(prbot_stack).add("service", "pr-bot")
    Tags.of(prbot_stack).add("user", "tnielsen")
    Tags.of(prbot_stack).add("deployment_method", "CDK")

app.synth()
