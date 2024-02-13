#!/usr/bin/env python3
import os
import shutil
import zipfile
import subprocess

import aws_cdk as cdk
from aws_cdk import (
    aws_apigatewayv2,
    aws_apigatewayv2_integrations,
    aws_lambda,
    aws_s3,
    Duration,
)
from constructs import Construct

stack_name_short = "PrBot"
deployed_environments = ["dev", "prod"]
lambda_pip_deps = ["langchain", "PyGithub", "Cryptography"]


def install_and_create_lambda_layer(modules: list[str]) -> str:
    """
    Install the specified Python modules and create a Lambda layer package.
    :param modules: List of Python modules to install
    :return: Path to the created Lambda layer package
    """
    temp_dir = "temp_layer"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        layer_dir = os.path.join(temp_dir, "python/lib/python3.11/site-packages/")
        os.makedirs(layer_dir, exist_ok=True)

        for module in modules:
            # Install the module in the layer directory
            subprocess.run(["pip", "install", module, "-t", layer_dir])

        zip_file_name = f"{stack_name_short}_layer.zip"
        zip_file_path = os.path.join(os.getcwd(), zip_file_name)

        # Use shutil.make_archive to create the ZIP file
        shutil.make_archive(zip_file_path[:-4], 'zip', temp_dir)

        print(f"Lambda layer package '{zip_file_name}' created successfully.")
        return zip_file_path
    except Exception as e:
        print(f"Error creating Lambda layer package: {e}")
    finally:
        # Clean up: remove the temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)


class PrBot(cdk.Stack):
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

        layer_filename = install_and_create_lambda_layer(lambda_pip_deps)

        pypi_layer = aws_lambda.LayerVersion(
            self,
            id=f"{id}prReviewPypiLayer",
            code=aws_lambda.Code.from_asset(
                path=layer_filename,
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
                "GITHUB_TOKEN": cdk.SecretValue.secrets_manager(
                    f"/{stack_environment}/{stack_name_short}/GITHUB_TOKEN",
                ).unsafe_unwrap(),
            },
            handler=lambda_handler,
            layers=[pypi_layer],
            runtime=aws_lambda.Runtime.PYTHON_3_11,
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


app = cdk.App()

for environment in deployed_environments:
    stack_name_l = f"{environment}{stack_name_short}"
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
        env=cdk.Environment(
            account=os.getenv("AWS_ACCOUNT_NUMBER"), region="us-west-2"
        ),
        # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
    )
    cdk.Tags.of(prbot_stack).add("environment", environment)
    cdk.Tags.of(prbot_stack).add("stack", stack_name_l)
    cdk.Tags.of(prbot_stack).add("service", "pr-bot")
    cdk.Tags.of(prbot_stack).add("user", "tnielsen")
    cdk.Tags.of(prbot_stack).add("deployment_method", "CDK")

app.synth()
