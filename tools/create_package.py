#!/usr/bin/env python
# This script creates the package.zip with the code ready to be uploaded.
#
# You can import the class LambdaPackage from other python scripts
#
from os import path
import sys

from awslambda import LambdaPackage


def _get_args():
    if len(sys.argv) != 4:
        print("Usage: {0} <package-name> <release> <source_directory>".format(
              sys.argv[0]))
        sys.exit(1)

    return sys.argv[1:]


if __name__ == "__main__":

    package_name, release, directory = _get_args()

    package = LambdaPackage(
        package_name,
        release,
        directory
    )

    package.add_pyfiles()

    package.save()

    print("Created file {}".format(package.filename))
