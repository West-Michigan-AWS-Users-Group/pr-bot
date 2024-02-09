#!/usr/bin/env python3
import os

import aws_cdk as cdk
from aws_cdk import aws_apigatewayv2, aws_apigatewayv2_integrations, aws_lambda
from constructs import Construct

stack_name_short = 'PrBot'
deployed_environments = ['dev', 'prod']


class PrBot(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        if 'dev' in id:
            lambda_handler = 'dev_review_pr.handler'
            stack_environment = 'dev'
        elif 'prod' in id:
            lambda_handler = 'prod_review_pr.handler'
            stack_environment = 'prod'
        else:
            lambda_handler = None
            stack_environment = None
            raise ValueError(f'Invalid environment value declared for stack {id}.')

        # Define the Lambda function
        review_pr = aws_lambda.Function(
            self,
            f'{id}reviewPr',
            code=aws_lambda.Code.from_asset(
                f'{stack_environment}-lambda',
            ),
            handler=lambda_handler,
            runtime=aws_lambda.Runtime(
                'python3.12'
            ),  # Change the python version according to your requirement
            environment={
                'GITHUB_TOKEN': cdk.SecretValue.secrets_manager(
                    f'/{stack_environment}/{stack_name_short}/GITHUB_TOKEN',
                ).unsafe_unwrap(),
            },
        )

        webhook_api = aws_apigatewayv2.HttpApi(
            self,
            f'{id}webhookApi',
            create_default_stage=True,
            description='Webhook API for PR review'
        )

        webhook_api.add_stage(
            f'{id}webhookApiStage',
            stage_name='live',
            auto_deploy=True,
        )

        pr_review_integration = aws_apigatewayv2_integrations.HttpLambdaIntegration(
            f'{id}webhookApiPrReviewIntegration',
            review_pr
        )

        webhook_api.add_routes(
            path='/pr-review',
            methods=[aws_apigatewayv2.HttpMethod.POST],
            integration=pr_review_integration
        )


app = cdk.App()

for environment in deployed_environments:
    stack_name_l = f'{environment}{stack_name_short}'
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
            account=os.getenv('AWS_ACCOUNT_NUMBER'), region='us-west-2'
        ),
        # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
    )

app.synth()
