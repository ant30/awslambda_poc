#!/usr/bin/env python

from pprint import pprint
import sys
import argparse

from awslambda import AwsLambdaManager, ConfigYamlReader


class LambdaInvokeFunction:
    def __init__(self, configfile, options):
        self.config = ConfigYamlReader(options.configfile)
        self.options = options
        self.aws_lambda = AwsLambdaManager(self.config.config)

    def __call__(self):
        if not self.aws_lambda.function_exists():
            print("Lambda function does not exists")
            sys.exit(1)


        qualifier = (self.options.version
                    if self.options.version
                    else self.options.alias)


        func = (self.aws_lambda_invoke_async
                if self.options.async
                else self.aws_lambda.invoke_sync)

        return func(str(qualifier), self.options.payload)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Create release operation')
    parser.add_argument('configfile')
    parser.add_argument('--payload', type=argparse.FileType('r'))

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--alias', default='$LATEST')
    group.add_argument('--version', type=int)

    parser.add_argument('--async', type=bool, default=False)
    args = parser.parse_args()

    pprint(LambdaInvokeFunction(args.configfile, args)())

