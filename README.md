# pr-bot
A repo containing AWS resources used to provide feedback on GitHub pull requests


# CDK Setup

```bash
https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html
python -m ensurepip --upgrade
python -m pip install --upgrade pip
python -m pip install --upgrade virtualenv

mkdir cdk
cd cdk
cdk init app --language python

# Populate .cdk.env file with AWS account number
AWS_ACCOUNT_NUMBER="1234567890"
# Use heredoc to write to the file in the root of the repo
cat << EOF > ../.cdk.env
export AWS_ACCOUNT_NUMBER=${AWS_ACCOUNT_NUMBER}
EOF

# Init environment variables
source ../.cdk.env


pip install --upgrade -r requirements.txt

# Repeat for each region desired
cdk bootstrap aws://${AWS_ACCOUNT_NUMBER}/us-east-1

# ensure it synthesises
cdk synth
```

#### Create your Lambda secrets and store them in SSM as plaintext, as secure SSM is not supported in Lambda env vars
Format is `<environment>/StackName/GITHUB_TOKEN`.
Examples: 
- `/dev/PrBot/GITHUB_TOKEN`
- `/prod/PrBot/GITHUB_TOKEN`

#### Deploy
Below all stacks will be deployed with no prompts.
```bash
AWS_DEFAULT_PROFILE=yam-pxg-sandbox-sre AWS_REGION=us-east-1 cdk deploy --all --require-approval never
```


# Lambda local development
https://docs.aws.amazon.com/toolkit-for-jetbrains/latest/userguide/invoke-lambda.html

I am using a JetBrains IDE to develop and test the Lambda function locally.  
As per the above document, template.yaml is used to configure the IDE to run the Lambda function locally.  
The template.yaml file is also used to deploy the Lambda function to AWS.
`template.yaml` is stored in the `cdk/lambda` directory.

Values in `template.yaml` should match the stack lambda configured and deployed in the CDK stack.

# CI Deployment
The CDK stack is deployed using GitHub Actions. It requires access keys to be stored in GitHub secrets to execute
CDK commands. The account this is deployed into should have the necessary permissions to assume the CDK bootstrap role.

Example user and policy deployed with vanilla CFN that is permitted to assume the CDK bootstrap role:
```
    "cdkDeployUser": {
      "Properties": {
        "UserName": "sa-cdkDeployUser"
      },
      "Type": "AWS::IAM::User"
    },
    "cdkDeployPolicyAssignment": {
      "Properties": {
        "PolicyDocument": {
          "Statement": [
            {
              "Action": [
                "sts:AssumeRole"
              ],
              "Effect": "Allow",
              "Resource": "arn:aws:iam::*:role/cdk-*"
            }
          ]
        },
        "PolicyName": "production-a-iam-cdk-deploy-user-and-readonly",
        "Users": [
          {
            "Ref": "cdkDeployUser"
          }
        ]
      },
      "Type": "AWS::IAM::Policy"
    },
```