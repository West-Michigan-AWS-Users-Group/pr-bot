#!/usr/bin/env python3
import os

import aws_cdk as cdk
from aws_cdk import aws_lambda as _lambda
from constructs import Construct

stack_name_short = "PrBot"
deployed_environments = ["dev", "prod"]


class PrBot(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        if "dev" in id:
            lambda_handler = "dev_review_pr.lambda_handler"
            stack_environment = "dev"
        elif "prod" in id:
            lambda_handler = "prod_review_pr.lambda_handler"
            stack_environment = "prod"
        else:
            lambda_handler = None
            stack_environment = None
            raise ValueError(f"Invalid environment value declared for stack {id}.")

        # Define the Lambda function
        review_pr = _lambda.Function(
            self,
            f"{id}reviewPr",
            code=_lambda.Code.from_asset(
                f"{stack_environment}-lambda",
            ),  # Fetch code from 'lambda' directory
            handler=lambda_handler,  # the function lambda_handler inside review_pr.py
            runtime=_lambda.Runtime(
                "python3.12"
            ),  # Change the python version according to your requirement
            environment={
                "GITHUB_TOKEN": cdk.SecretValue.secrets_manager(
                    f"/{stack_environment}/{stack_name_short}/GITHUB_TOKEN",
                ).unsafe_unwrap(),
            },
        )

        # Create the API Gateway with the Lambda integration
        # webhook_api = apigw.HttpApi(
        #     self,
        #     f"{id}webhookApi",
        #     create_default_stage=True,
        #     description="Webhook API for processing GitHub webhooks",
        # )

        # stage
        # webhook_api.add_stage(
        #     stage_name="live",
        #     auto_deploy=True,
        #     description="Live stage",
        # )

        # route
        # webhook_api.add_routes(
        #     path="/review-pr",
        #     methods=[apigw.HttpMethod.POST],
        #     integration=apiintegrations.LambdaProxyIntegration(
        # )

        # integration

        # permission


app = cdk.App()

for environment in deployed_environments:
    stack_name_l = f"{environment}{stack_name_short}"
    PrBot(
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

app.synth()
