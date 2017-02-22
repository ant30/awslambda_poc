#!/usr/bin/env python

from pprint import pprint
import sys
import argparse

from awslambda import AwsLambdaManager, ConfigYamlReader


class CreateFunctionRelease:
    def __init__(self, configfile, alias):
        self.config = ConfigYamlReader(configfile)
        self.alias = alias
        self.aws_lambda = AwsLambdaManager(self.config.config)

    def __call__(self):
        if self.aws_lambda.function_exists():
            return(self.aws_lambda.create_release())
        else:
            print("Lambda function not found")
            sys.exit(1)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Create release operation')
    parser.add_argument('configfile')
    parser.add_argument('--alias', default='devel')
    args = parser.parse_args()

    CreateFunctionRelease(args.configfile, args.alias)()
