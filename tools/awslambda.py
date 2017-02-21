import logging
from os import path
from zipfile import PyZipFile

import boto3
import yaml


logger = logging.getLogger('LambdaManager')


class ConfigYamlReader:
    # Config is in yaml format
    def __init__(self, configfile):
        """
            FunctionName: the_visible_lambda_function_name
            Runtime: python2.7
            Role: a-iam-role
            Handler: module_name.lambda_handler
            Description: A function description  # optional
            Code:
               S3Bucket: the-bucket-name-to-upload-releases
               S3KeyPath: route/to/releases/directory
               Directory: path/to/code/directory
            MemorySize: 128
            Timeout: 120  # optional
            VpcConfig:  # optional
                SubnetIds:
                    - string
                SecurityGroupIds:
                    - string
            Environment:  # optional
                KEY1: VALUE1
                KEY2: VALUE2
                KEY3: VALUE3
        """
        self.configfile = configfile
        with open(self.configfile, 'r') as f:
            self.config = yaml.load(f)

    def function_properties_check(self):
        """
        Check the schema
        """
        raise NotImplementedError()


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


class S3FunctionUploader:

    def __init__(self, bucket_name):
        self.s3_client = boto3.client('s3')
        self.bucket = bucket_name

        if not any(
            item['Name'] == self.bucket
            for item in self.s3_client.list_buckets().get('Buckets', [])
        ):
            logger.debug('Creating bucket s3://{0}'.format(self.bucket))
            self.s3_client.create_bucket(
                ACL='private',
                Bucket=self.bucket
            )

    def upload(self, local_filename, s3_filename):
        """ Stream the zip called local_filename to s3://bucket/s3_filename """

        logger.debug('writting file {0} into {1}/'.format(
            local_filename,
            self.bucket,
            s3_filename)
        )

        self.s3_client.upload_file(
            local_filename,
            self.bucket,
            s3_filename)


class AwsLambdaManager:

    def __init__(self, config):
        """
            config = {
                'FunctionName': 'the_visible_lambda_function_name',
                'Runtime': 'python2.7',
                'Role': 'a-iam-role',
                'Handler': 'module_name.lambda_handler',
                'Description': 'A function description',  # optional
                'Code': {
                   'S3Bucket': 'the-bucket-name-to-upload-releases',
                   'S3KeyPath': 'route/to/releases/directory',
                   'Directory': 'path/to/code/directory',
                },
                'MemorySize': 128,
                'Timeout': 120,  # optional
                'VpcConfig': {  # optional
                    'SubnetIds': [
                        'string',
                    ],
                    'SecurityGroupIds': [
                        'string',
                    ],
                },
                'Environment': {  # optional
                    'KEY1': 'VALUE1',
                    'KEY2': 'VALUE2',
                    'KEY3': 'VALUE3',
                },
            }
        """
        self.config = config
        self.aws_lambda = boto3.client('lambda')

    def create_package(self, directory, package_name, release_tag):
        """ Create a temporary zip package"""
        logger.info("Creating zip package")
        lp = LambdaPackage(package_name,
                           release_tag,
                           directory,
                           target_directory='.')
        lp.add_pyfiles()
        lp.save()
        self.local_filename = lp.filename

    def upload_package(self, filename=None):
        """ Upload the package to S3 """
        logger.info("Uploading the package to S3")
        s3f = S3FunctionUploader(self.config['Code']['S3Bucket'])
        self.s3_filename = path.join(
            self.config['Code']['S3KeyPath'],
            path.basename(filename or self.local_filename)
        )
        s3f.upload(filename or self.local_filename,
                   self.s3_filename)


    def create_function(self):
        """ Create a function in aws lambda """
        logger.info("Preparing stuf to create function")
        self.create_package(
            self.config['Code']['Directory'],
            self.config['FunctionName'],
            'devel'
        )

        self.upload_package()

        # Set required properties
        function_definition = {
            key: self.config[key]
            for key in (
                'FunctionName',
                'Runtime',
                'Role',
                'Handler',
                'MemorySize',
            )
        }

        # Set optional properties
        function_definition.update({
            key: self.config[key]
            for key in (
                'Environment',
                'Description',
                'Timeout',
                'VpcConfig',
            )
            if self.config.get(key)
        })

        # Set the first release Code block
        function_definition['Code'] = {
            'S3Bucket': self.config['Code']['S3Bucket'],
            'S3Key': self.s3_filename,
        }

        function_definition['Publish'] = False

        logger.info("Creating function")
        return self.aws_lambda.create_function(**function_definition)

    def function_exists(self):
        """
            Check if the function is already created in aws
        """
        try:
            self.aws_lambda.get_function(
                FunctionName=self.config['FunctionName']
            )
            return True
        except:  # Change this to handler the correct exception
            return False

    def generate_release(self, tag="devel"):
        """
            publish version in lambda with alias "tag"
        """
        raise NotImplementedError()

    def promote_revision(self, revision):
        """
            update alias "production" to "revision"
        """
        raise NotImplementedError()

    def invoke_sync(self, revision, payload):
        """
            Call in sync mode to the function
                payload is a file.
        """
        raise NotImplementedError()

    def invoke_async(self, revision, payload):
        """
            Call in sync mode to the function
                payload is a file.
        """
        raise NotImplementedError()


