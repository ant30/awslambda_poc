# awslambda-poc

This a Proof of concept of aws lambda handler.

This repo include some scripts that helps in managing the release in aws lambda
functions with python.

 1. [X] Create a example function, something writting into s3. Remember to
    customize the env var `S3_BUCKET` in `local_simulation.sh` script.
 1. [X] Function description with YAML.
 1. [X] Create a lambda function.
 1. [X] Manage the upload of new revisions and production.
 1. [ ] Be able to launch a test event on a named version (aka devel,
    production, 0.1.1).
 1. [X] Create a script to launch sync and async tests.
 1. [ ] Docker environment to test the lambda handler instead of own PC.
 1. [ ] Allow the same codebase for multiple functions.
 1. [ ] Embedded python requirements with functions zip.
