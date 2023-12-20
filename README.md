# pr-bot
A repo containing AWS resources used to provide feedbacks on GitHub pull requests


# CDK Setup

```bash
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
```