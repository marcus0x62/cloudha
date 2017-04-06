* S3 bucket and filename for config should be specified as part of the CFT and
  learned via a runtime parameter of some sort.

* Better error handling

* Host-down confirmation from within the Lambda service.  Essentially, the idea
  is to treat host-down messages as prospective HA events, confirm them via
  the Lambda service, and only then initiate a route-table failover.

* Configuration UI of some sort
