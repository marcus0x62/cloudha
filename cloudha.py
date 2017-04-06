#!/usr/bin/env python
#
# cloudha.py -- Lambda service that provides stateless failover for Palo Alto
#               Networks firewalls deployed in AWS.  The firewall pair must be
#               deployed within a single region and VPC, but can span
#               availability zones.  It works by modifying the route table(s)
#               associated with one or more subnets.
#
# Created: Marcus Butler <marcusb@marcusb.org>, 05-April-2017.
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
import json

CONFIG_BUCKET='mbutler-cloudha-config'
CONFIG_FILE='config.json'

def up(config, serial):
    status = ""

    for subnet in config['firewalls'][serial]:
        subnet_id = subnet['subnet']
        rtb       = subnet['healthyRouteTable']
        rtb_assoc = get_rtb_assoc(subnet_id)

        change_rtb(rtb_assoc, rtb)
        status = status + "Changed route table for " + subnet_id + " " + \
                 "to " + rtb + "\n"

    return {
            'statusCode': 200,
            'headers': { 'Content-Type': 'application/json' },
            'body': json.dumps({'status': status})
    }

def down(config, serial):
    status = ""

    for subnet in config['firewalls'][serial]:
        subnet_id = subnet['subnet']
        rtb       = subnet['sickRouteTable']
        rtb_assoc = get_rtb_assoc(subnet_id)

        change_rtb(rtb_assoc, rtb)
        status = status + "Changed route table for " + subnet_id + " " + \
                 "to " + rtb + "\n"

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
