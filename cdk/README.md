
# DevPRBot
Repo containing CDK and app code for a simple PR bot, powered by AWS Bedrock.

When running CDK, layers are built and pushed with each commit.

Activate the virtualenv.

```
$ source .venv/bin/activate
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ AWD_DEFAULT_PROFILE=<profile-name> cdk synth devPrBot
```
