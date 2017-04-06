#!/usr/bin/python
#
# common.py -- Methods used by the cloud-ha scripts.
# Created: Marcus Butler <marcusb@marcusb.org>, 05-April-2017.
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
