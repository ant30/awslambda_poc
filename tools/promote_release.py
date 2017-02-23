#!/usr/bin/env python

from pprint import pprint
import sys
import argparse

from awslambda import AwsLambdaManager, ConfigYamlReader


class PromoteRelease:
    def __init__(self, configfile, alias=None, version=None):
        self.config = ConfigYamlReader(configfile)
        self.alias = alias
        self.aws_lambda = AwsLambdaManager(self.config.config)

    def __call__(self):
        if self.aws_lambda.function_exists():
            return(self.aws_lambda.promote_release(self.alias))
        else:
            print("Lambda function not found")
            sys.exit(1)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Create release operation')
    parser.add_argument('configfile')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--alias', default='devel')
    group.add_argument('--version', default='devel')
    args = parser.parse_args()

    PromoteRelease(args.configfile, args.alias)()
