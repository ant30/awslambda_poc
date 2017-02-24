#!/usr/bin/env python

from pprint import pprint
import sys

from awslambda import AwsLambdaManager, ConfigYamlReader


class ListAliases:
    def __init__(self, configfile):
        self.config = ConfigYamlReader(configfile)
        self.aws_lambda = AwsLambdaManager(self.config.config)

    def __call__(self):
        if not self.aws_lambda.function_exists():
            print("The function doesn't exist")
            sys.exit(1)

        aliases = self.aws_lambda.list_aliases()
        for item in aliases['Aliases']:
            print("{Name} -> {FunctionVersion}".format(**item))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: {0} <config.yml>".format(sys.argv[0]))
        sys.exit(1)
    config = sys.argv[1]
    ListAliases(config)()
