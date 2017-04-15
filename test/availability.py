#!/usr/bin/env python

import common

dict = common.get_config('mbutler-cloudha-config', 'new-config.json')
hosts = common.check_availability(dict, None)

for host in hosts:
    print "%s failed!" % host

