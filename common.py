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
from os import getenv
from socket import socket, AF_INET, SOCK_STREAM, IPPROTO_TCP
import sys
import json
import ssl
import urllib2

DBG_ERROR = 0
DBG_INFO  = 1
DBG_TRACE = 10

def DEBUG(level, message):
    if getenv('DEBUG') and int(getenv('DEBUG')) >= level:
        print(message)

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

def modify_route(rtb, dest, eni):
    ec2 = client('ec2')
    try:
        ec2.replace_route(RouteTableId = rtb, DestinationCidrBlock = dest,
                          NetworkInterfaceId = eni)
    except ClientError as e:
        DEBUG(DBG_ERROR,
              "Unable to replace route %s on rtb %s to eni %s (error: %s)" %
              (dest, rtb, eni, repr(e.response)))
        return False
    return True

def get_config(bucket, file):
    s3 = client('s3')

    obj = s3.get_object(Bucket=bucket, Key=file)
    dict = json.loads(obj['Body'].read())

    return dict

def check_tcp_ping(ip, port):
    s = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
    s.settimeout(3)
    
    try:
        s.connect((ip, port))
    except:
        DEBUG(DBG_ERROR, "*** ERROR *** tcp_ping unable to connect to %s:%d" % (ip, port))
        s.close()
        return False

    s.close()
    return True

def check_ssl_ping(ip, port):
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.verify_mode = ssl.CERT_NONE # Do not attempt to validate certs

    s = context.wrap_socket(socket(AF_INET))
    s.settimeout(3)
    
    try:
        s.connect((ip, port))
    except:
        DEBUG(DBG_ERROR, "*** ERROR *** ssl_ping unable to connect to %s:%d" % (ip, port))
        s.close()
        return False

    s.close()
    return True

def check_http_ping(url):
    if type(url) not in (str, unicode):
        DEBUG(DBG_ERROR,
              "URL %s passed to check_http_ping not string!" % repr(url))
        return False

    ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    ctx.verify_mode = ssl.CERT_NONE

    try:
        file = urllib2.urlopen(url, timeout=3, context=ctx)
    except Exception as e:
        DEBUG(DBG_ERROR, "Unable to connect to %s: %s" % (url, e))
        return False

    if file.getcode() != 200:
        DEBUG(DBG_ERROR, "Received non-200 response code: %d" % file.getcode())
        file.close()
        return False

    file.close()
    return True

#
# check_availability -- Check the status of one or more failover groups.
# Arguments:
#   config -- Configuration dictionary as returned by get_config
#   group  -- Optional argument that specifies the group to check.  If set to
#             None, all groups in the config dictionary are checked.
#
# Return Value -- a list containing all groups that failed their test
#                 condition(s).
#
def check_availability(config, chk_group=None):
    if config is None:
        DEBUG(DBG_ERROR, 'Config not passed!')
        return False

    if not config.has_key('groups'):
        DEBUG(DBG_ERROR, 'Config does not have groups key!')
        return False

    failed_groups = []

    for group in config['groups']:
        if not chk_group or group == chk_group:
            if config['groups'][group].has_key('failover-mode'):
                group_failover_mode = config['groups'][group]['failover-mode']
            else:
                group_failover_mode = 'any'

            failed_devices = 0
            total_devices  = 0
            
            for device in config['groups'][group]['devices']:
                device_name = device.keys()[0]
                total_devices += 1

                if device[device_name].has_key('failover-mode'):
                    device_failover_mode = device[device_name]['failover-mode']
                else:
                    device_failover_mode = 'any'
                    
                DEBUG(DBG_INFO, "Checking group %s with failover mode %s" % (device_name, group_failover_mode))

                total_addresses = 0
                failed_addresses = 0
                
                for address in device[device_name]['addresses']:
                    total_addresses += 1
                    
                    if address.has_key('test'):
                        test = address['test']
                    else:
                        DEBUG(DBG_ERROR, "Unable to run test for %s" % repr(address))
                        continue

                    if test == 'http_ping':
                        if address.has_key('url'):
                            url = address['url']
                            host = url
                        else:
                            DEBUG(DBG_ERROR, "Cannot run http_ping test for %s: url not specified" % repr(address))
                            continue
                    else:
                        if address.has_key('ip') and address.has_key('port'):
                            ip  = address['ip']
                            port = address['port']
                            host = "%s:%s" % (ip, port)
                        else:
                            DEBUG(DBG_ERROR, "Cannot run test %s on %s: IP or port not specified" % (test, repr(address)))
                            continue
                        
                    if address.has_key('count'):
                        count = address['count']
                    else:
                        count = 1

                    if address.has_key('failure'):
                        failure = address['failure']
                    else:
                        failure = 1

                    DEBUG(DBG_TRACE, "Testing %s with test %s count %d/fail %d" %
                              (host, test, count, failure))

                    if test == 'tcp_ping':
                        DEBUG(DBG_TRACE, 'Running tcp_ping for %s' % ip)

                        failures = 0
                        for i in range(count):
                            if check_tcp_ping(ip, int(port)) == False:
                                DEBUG(DBG_TRACE, 'tcp_ping FAILED for %s:%s' % (ip, port))
                                failures += 1
                            else:
                                DEBUG(DBG_TRACE, 'tcp_ping SUCCEEDED for %s:%s' % (ip, port))

                        if failures >= failure:
                            failed_addresses += 1
                    elif test == 'ssl_ping':
                        DEBUG(DBG_TRACE, 'Running ssl_ping for %s' % ip)

                        failures = 0
                        for i in range(count):
                            if check_ssl_ping(ip, int(port)) == False:
                                DEBUG(DBG_TRACE, 'ssl_ping FAILED for %s:%s' % (ip, port))
                                failures += 1
                            else:
                                DEBUG(DBG_TRACE, 'ssl_ping SUCCEEDED for %s: %s' % (ip, port))

                        if failures >= failure:
                            failed_addresses += 1
                    elif test == 'http_ping':
                        DEBUG(DBG_TRACE, 'Running http_ping for %s' % url)

                        failures = 0
                        for i in range(count):
                            if check_http_ping(url) == False:
                                DEBUG(DBG_TRACE, 'http_ping FAILED for %s' % url)
                                failures += 1
                            else:
                                DEBUG(DBG_TRACE, 'http_ping SUCCEEDED for %s' % url)

                        if failures >= failure:
                            failed_addresses += 1
                    else:
                        DEBUG(DBG_ERROR, '*** ERROR *** Unsupported test %s specified' % ip)

            if device_failover_mode == 'all' and failed_addresses == total_addresses:
                failed_devices += 1
                DEBUG(DBG_TRACE, '*** ERROR *** All tests FAILED for device %s' % device_name)
            elif device_failover_mode == 'any' and failed_addresses > 0:
                failed_devices += 1
                DEBUG(DBG_TRACE, '*** ERROR *** Some tests FAILED for device %s' % device_name)
            else:
                DEBUG(DBG_TRACE, 'ALL TESTS for device %s PASSED' % device.keys()[0])

        if group_failover_mode == 'all' and failed_devices == total_devices:
            DEBUG(DBG_TRACE, "Setting failure for group %s in mode all (%d:%d)" % (group, failed_devices, total_devices))
            failed_groups.append(group)
        elif failed_devices > 0:
            DEBUG(DBG_TRACE, "Setting failure for group %s in mode any" % group)
            failed_groups.append(group)
            
    return failed_groups

def fatal_error(errmsg):
    return {
            'statusCode': 500,
            'headers': { 'Content-Type': 'application/json' },
            'body': json.dumps({'errorMessage': errmsg})
    }
