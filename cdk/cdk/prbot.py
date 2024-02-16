#!/usr/bin/env python3
from aws_cdk import (
    Duration,
    SecretValue,
    Stack,
    aws_apigatewayv2,
    aws_apigatewayv2_integrations,
    aws_iam,
    aws_lambda,
)
from constructs import Construct

stack_name_short = "PrBot"
layer_path = "layers/prbot-layer.zip"


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
            timeout=Duration.minutes(15),
            memory_size=256,
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
