#!/usr/bin/env python
#
# common.py -- Methods used by the cloud-ha scripts.
# Created: Marcus Butler, 05-April-2017.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

from boto3 import client
from botocore.exceptions import ClientError
import sys
import json

def get_rtb_assoc(subnet):
    ec2 = client('ec2')
    res = ec2.describe_route_tables()

    for table in res['RouteTables']:
        for assoc in table['Associations']:
            if assoc.has_key('SubnetId') and assoc['SubnetId'] == subnet:
                return assoc['RouteTableAssociationId']

    return None

def change_rtb(old_assoc, rtb):
    ec2 = client('ec2')
    res = ec2.replace_route_table_association(AssociationId = old_assoc,
                                              RouteTableId = rtb)

    return True

def get_config(bucket, file):
    s3 = client('s3')

    obj = s3.get_object(Bucket=bucket, Key=file)
    dict = json.loads(obj['Body'].read())

    return dict

def fatal_error(errmsg):
    return {
            'statusCode': 500,
            'headers': { 'Content-Type': 'application/json' },
            'body': json.dumps({'errorMessage': errmsg})
    }
