#!/usr/bin/env python3
import os
import subprocess

from aws_cdk import App, Environment, Tags

from cdk import prbot

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


app = App()

for environment in deployed_environments:
    stack_name_l = f"{environment}{prbot.stack_name_short}"
    create_layer_zip()
    prbot_stack = prbot.PrBot(
        app,
        stack_name_l,
        env=Environment(account=os.getenv("AWS_ACCOUNT_NUMBER"), region="us-west-2"),
    )
    Tags.of(prbot_stack).add("environment", environment)
    Tags.of(prbot_stack).add("stack", stack_name_l)
    Tags.of(prbot_stack).add("service", "pr-bot")
    Tags.of(prbot_stack).add("user", "tnielsen")
    Tags.of(prbot_stack).add("deployment_method", "CDK")
    Tags.of(prbot_stack).add("quote_diff_test", "True")

app.synth()
