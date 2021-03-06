import base64
import logging
import os
from os import path
import zipfile

from git import Repo
import boto3
import yaml

# Global INFO for all loggers, including boto
logging.basicConfig(level=os.environ.get('LOG_LEVEL', logging.INFO))
logger = logging.getLogger('LambdaManager')


def _get_git_release(repo_dir='.'):
    repo = Repo(repo_dir)
    hash_name = repo.head.commit.hexsha
    if len(repo.index.diff(None)) > 0:
        # Changes not stashed
        hash_name += 'm'
    try:
        if len(repo.index.diff(HEAD)) > 0:
            # Changes added to next commit
            hash_name += 'h'
    except:
        pass

    return hash_name



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
                Variables:
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

    def __init__(self, package_name, release, source_directory,
                 target_directory='.'):
        self.package_name = package_name
        self.release = release
        self.source_directory = source_directory
        self.target_directory = target_directory

        self.filename = "{package_name}-{release}.zip".format(
            target_directory=target_directory,
            package_name=package_name,
            release=release)

        self.zipf = zipfile.PyZipFile(
            path.join(target_directory, self.filename),
            'w',
            zipfile.ZIP_DEFLATED)
        self.zipf.writestr('PACKAGE_NAME', package_name)
        self.zipf.writestr('RELEASE', release)

    def add_pyfiles(self):
        oldpwd = os.getcwd()
        os.chdir(path.basename(self.source_directory))
        self.zipf.writepy('.')
        os.chdir(oldpwd)

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
                    'Variables': {
                        'KEY1': 'VALUE1',
                        'KEY2': 'VALUE2',
                        'KEY3': 'VALUE3',
                    }
                },
            }
        """
        self.config = config
        self.aws_lambda = boto3.client('lambda')

    def get_function_configuration(self):
        """
            Return a dict with the basic function properties valid for aws
        """
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

        return function_definition

    def create_package(self, directory, package_name, release_tag=''):
        """ Create a temporary zip package"""

        hash_release = _get_git_release()
        logger.info("Creating package with git release {0}".format(hash_release))

        lp = LambdaPackage(package_name,
                           hash_release + release_tag,
                           directory,
                           target_directory='.')
        lp.add_pyfiles()
        lp.save()
        self.hash_release = hash_release
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

        function_definition = self.get_function_configuration()

        # Set the first release Code block
        function_definition['Code'] = {
            'S3Bucket': self.config['Code']['S3Bucket'],
            'S3Key': self.s3_filename,
        }

        function_definition['Publish'] = True

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
        except self.aws_lambda.exceptions.ResourceNotFoundException:
            return False

    def create_release(self, alias="devel"):
        """
            publish version in lambda with alias "tag"
        """
        self.create_package(
            self.config['Code']['Directory'],
            self.config['FunctionName']
        )

        self.upload_package()

        logger.info("Creating release {0}".format(self.hash_release))

        response_code = self.aws_lambda.update_function_code(
            FunctionName=self.config['FunctionName'],
            S3Bucket=self.config['Code']['S3Bucket'],
            S3Key=self.s3_filename,
            Publish=True
        )

        logger.info("Created revision {0}".format(response_code['Version']))

        self.update_or_create_alias(response_code['Version'], self.hash_release)
        self.update_or_create_alias(response_code['Version'], alias)

        logger.info("If config wash changed, remember to update function "
                    "configuration")


    def update_or_create_alias(self, version, alias):
        try:
            self.aws_lambda.update_alias(
                FunctionName=self.config['FunctionName'],
                FunctionVersion=version,
                Name=alias)
            logger.info("Alias '{0}' updated for version '{1}'".format(
                alias, version
            ))
        except self.aws_lambda.exceptions.ResourceNotFoundException:
            self.aws_lambda.create_alias(
                FunctionName=self.config['FunctionName'],
                FunctionVersion=version,
                Name=alias
            )
            logger.info("Alias '{0}' created for version '{1}'".format(
                alias, version
            ))

    def update_function_configuration(self):
        """
            update function configuration without code update
        """

        logger.info("Update function config")
        function_definition = self.get_function_configuration()

        self.aws_lambda.update_function_configuration(
            **function_definition
        )

    def list_aliases(self):
        logger.info("Listing aliases")
        response = self.aws_lambda.list_aliases(
            FunctionName=self.config['FunctionName'],
            MaxItems=500

        )
        return response

    def promote_release(self, release):
        """
            update alias "production" to "release"
        """
        logger.info("Updating production alias with revision '{0}'".format(
                    release))
        if release.isdigit() or release == '$LATEST':
            version = release
        else:
            try:
                response = self.aws_lambda.get_alias(
                    FunctionName=self.config['FunctionName'],
                    Name=release
                )
                version = response['FunctionVersion']
            except self.aws_lambda.exceptions.ResourceNotFoundException:
                logger.error("Can't found the qualifier {0} for {1}".format(
                    release,
                    self.config['FunctionName']
                ))
                return

        self.update_or_create_alias(version, 'production')

    def invoke_sync(self, qualifier, payload):
        """
            Call in sync mode to the function
                payload is a file.
        """
        response =  self.aws_lambda.invoke(
            FunctionName=self.config['FunctionName'],
            InvocationType='RequestResponse',
            LogType='Tail',
            Payload=payload or bytes(''),
            Qualifier=qualifier
        )
        response['LogResultDecoded'] = base64.decodestring(
            response['LogResult'])
        return response

    def invoke_async(self, revision, payload):
        """
            Call in sync mode to the function
                payload is a file.
        """
        raise NotImplementedError()

