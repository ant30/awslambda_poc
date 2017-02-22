#!/usr/bin/env python
# This a simple lambda function writting timestamp in a concrete file in S3
# Required env vars (filled with examples values):
#   S3_BUCKET=the-example-bucket
#   S3_FILENAME="example/lasttimestamp"
#
# Reminder: If the bucket doesn't exists is going to be created

from datetime import datetime
import logging
import os
import sys

import boto3


logger = logging.getLogger('TimestampWritter')


class S3BucketHandler:

    def __init__(self, bucket):
        self.client = boto3.client('s3')
        self.bucket = bucket
        if not any(
            item['Name'] == bucket
            for item in self.client.list_buckets().get('Buckets', [])
        ):
            logger.debug('Creating bucket s3://{0}'.format(self.bucket))
            self.client.create_bucket(
                ACL='private',
                Bucket=bucket
            )

    def put(self, filename, content):
        logger.debug('writting file {0} into {1}'.format(filename, self.bucket))

        self.client.put_object(
            ACL='private',
            Key=filename,
            Bucket=self.bucket,
            Body=bytes(content)
        )


class TimestampWritterHandler:

    def __init__(self, event, context):
        self.context = context
        self.event = event

        self.s3_bucket = os.environ.get('S3_BUCKET')
        self.s3_filename = os.environ.get('S3_FILENAME')

        if not (self.s3_bucket and self.s3_filename):
            logger.critical('S3_BUCKET and S3_FILENAME env vars are required')
            sys.exit(1)
        logger.debug('TimestampWritterHandler was initialized')

    def _get_timestamp(self):
        return datetime.now().utcnow().strftime('%Y%m%d%H%M%S')

    def lambda_handler(self):
        logger.debug('lambda_handler was called')
        s3 = S3BucketHandler(self.s3_bucket)
        content = self._get_timestamp()
        s3.put(self.s3_filename, content)
        return content

    __call__ = lambda_handler


def lambda_handler(event, context):
    return TimestampWritterHandler(event, context)()


if __name__ == "__main__":
    """This emulate a lambda handler call in a local system"""
    print TimestampWritterHandler(object(), {})()
