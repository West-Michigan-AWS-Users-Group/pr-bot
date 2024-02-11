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


def install_and_create_lambda_layer(module_name):
    # Create a temporary directory to store the layer files
    temp_dir = "temp_layer"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        subprocess.run(["pip", "install", module_name, "-t", temp_dir])
        # Create a zip file for the Lambda layer
        zip_file_name = f"{module_name}_layer.zip"
        zip_file_path = os.path.join(os.getcwd(), zip_file_name)
        with zipfile.ZipFile(zip_file_path, "w") as zipf:
            # Add all files from the temporary directory to the zip file
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)

        print(f"Lambda layer package '{zip_file_name}' created successfully.")
        return zip_file_path
    except Exception as e:
        print(f"Error creating Lambda layer package: {e}")
        return None

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

        layer_filename = install_and_create_lambda_layer("langchain")

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
