#!/usr/bin/env python
# This script creates the package.zip with the code ready to be uploaded.
#
# You can import the class LambdaPackage from other python scripts
#
from os import path
import sys
from zipfile import PyZipFile



class LambdaPackage:

    def __init__(self, package_name, release, source_directory, target_directory='.'):
        self.package_name = package_name
        self.release = release
        self.source_directory = source_directory
        self.target_directory = target_directory

        self.filename = "{package_name}-{release}.zip".format(
            target_directory=target_directory,
            package_name=package_name,
            release=release)

        self.zipf = PyZipFile(path.join(target_directory, self.filename), 'w')
        self.zipf.writestr('PACKAGE_NAME', package_name)
        self.zipf.writestr('RELEASE', release)

    def add_pyfiles(self):
        self.zipf.writepy(self.source_directory)

    def add_otherfiles(self, files):
        for filename in files:
            self.zipf.write(filename)

    def save(self):
        self.zipf.close()


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
