#!/usr/bin/env python
#
# cloudha.py -- Lambda service that provides stateless failover for devices
#               deployed in AWS.  The devices be deployed within a single VPC,
#               but may span availability zones.  This service works by
#               modifying one or more route table entries, as specified in a
#               configuration file stored in S3.
#
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

from common import fatal_error, get_rtb_assoc, change_rtb, get_config
from common import check_availability, modify_route
import json

CONFIG_BUCKET='mbutler-cloudha-config'
CONFIG_FILE='config.json'

def up(config, group):
    status = ""
    # Logic:
    # 1) Verify group in config file
    # 2) Verify group is up
    # 3) Modify routes if group is up

    if not config['groups'].has_key(group):
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'status': 'Group %s does not exist' % group})
        }

    if group not in check_availability(config, group):
        for table in config['groups'][group]['route-tables']:
            rtb = table['route-table']
            print "Changing %s to UP ROUTES" % table
            for route in table['routes']:
                print "Modifying %s:%s to %s" % (rtb, route['route'], route['healthyENI'])
                if not modify_route(rtb, route['route'], route['healthyENI']):
                    return {
                        'statusCode': 500,
                        'headers': {'Content-Type': 'application/json'},
                        'body': json.dumps({'status': 'Unable to change route %s:%s to %s' % ( rtb, route['route'], route['sickENI'])})
                    }

    return {
            'statusCode': 200,
            'headers': { 'Content-Type': 'application/json' },
            'body': json.dumps({'status': status})
    }

def down(config, group):
    status = ""

    # Logic:
    # 1) Verify group in config file
    # 2) Verify group is down
    # 3) Verify peer device is up
    # 3) Modify routes if group is down and peer device is up

    if not config['groups'].has_key(group):
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'status': 'Group %s does not exist' % group})
        }

    if group in check_availability(config, group):
        if config['groups'][group].has_key('peer-group'):
            peer_group = config['groups'][group]['peer-group']

            if not config['groups'].has_key(peer_group):
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'status': 'Peer group %s for group %s does not exist' % (peer_group, group)})
                }

        if peer_group in check_availability(config, peer_group):
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'status': 'Cannot switch routes for %s: peer group %s down' % (group, peer_group)})
            }
        
        for table in config['groups'][group]['route-tables']:
            rtb = table['route-table']
            print "Changing %s to DOWN ROUTES" % table
            for route in table['routes']:
                print "Modifying %s:%s to %s" % (rtb, route['route'], route['sickENI'])
                if not modify_route(rtb, route['route'], route['sickENI']):
                    return {
                        'statusCode': 500,
                        'headers': {'Content-Type': 'application/json'},
                        'body': json.dumps({'status': 'Unable to change route %s:%s to %s' % ( rtb, route['route'], route['sickENI'])})
                    }

    return {
            'statusCode': 200,
            'headers': { 'Content-Type': 'application/json' },
            'body': json.dumps({'status': status})
    }


def lambda_handler(event, context):
    serial = ""
    action = ""
    res    = None

    if not event['queryStringParameters'].has_key('serial'):
        return fatal_error("Firewall serial number not passed")
    else:
        serial = event['queryStringParameters']['serial']
    
    if not event['queryStringParameters'].has_key('action'):
        return fatal_error("Action (up or down) parameter not passed")
    else:
        action = event['queryStringParameters']['action']

    config = get_config(CONFIG_BUCKET, CONFIG_FILE)

    if not config['firewalls'].has_key(serial):
        return fatal_error("Firewall serial number not found in configuration")

    if action == "up":
        res = up(config, serial)
    elif action == "down":
        res = down(config, serial)
    else:
        return fatal_error("Invalid action specified")

    return res
