# pr-bot
A repo containing AWS resources used to provide feedback on GitHub pull requests

# Architecture
![architecture-diagram.png](architecture-diagram.png)

# Branch strategy
`develop` --- deploys the devPrBot stack
`main` -- deploys the prodPrBot stack

Testing the URL:
```bash
curl -X POST -d '{"foo": "bar"}' -H 'Content-Type: application/json' https://<placeholder>.execute-api.us-west-2.amazonaws.com/live/pr-review

```