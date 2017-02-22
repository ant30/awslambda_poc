#!/usr/bin/env python

from pprint import pprint
import sys

from awslambda import AwsLambdaManager, ConfigYamlReader


class UpdateLambdaFunctionConfiguration:
    def __init__(self, configfile):
        self.config = ConfigYamlReader(configfile)
        self.aws_lambda = AwsLambdaManager(self.config.config)

    def __call__(self):
        if not self.aws_lambda.function_exists():
            print("The function doesn't exists")
            sys.exit(1)
        else:
            self.aws_lambda.update_function_configuration()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: {0} <config.yml>".format(sys.argv[0]))
        sys.exit(1)
    config = sys.argv[1]
    UpdateLambdaFunctionConfiguration(config)()
