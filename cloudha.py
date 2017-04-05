#!/usr/bin/python
#
# cloudha.py -- Lambda service that provides stateless failover for Palo Alto
#               Networks firewalls deployed in AWS.  The firewall pair must be
#               deployed within a single region and VPC, but can span
#               availability zones.  It works by modifying the route table(s)
#               associated with one or more subnets.
#
# Created: Marcus Butler <marcusb@marcusb.org>, 05-April-2017.
#

from common import fatal_error, get_rtb_assoc, change_rtb
import json

config_data = """
{
    "firewalls": {
        "007955000014636": [
            {
                "subnet": "subnet-e5462982",
                "healthyRouteTable": "rtb-2e788348",
                "sickRouteTable": "rtb-75dd1913"
            }
        ],

        "007955000014636": [
            {
                "subnet": "subnet-e5462982",
                "healthyRouteTable": "rtb-2e788348",
                "sickRouteTable": "rtb-75dd1913"
            }
        ]
    }   
}
"""

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

    config = json.loads(config_data)

    if not config['firewalls'].has_key(serial):
        return fatal_error("Firewall serial number not found in configuration")

    if action == "up":
        res = up(config, serial)
    elif action == "down":
        res = down(config, serial)
    else:
        return fatal_error("Invalid action specified")

    return res
