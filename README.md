*** WARNING *** -- this code is highly experimental and is not intended for
production use.  There are many failure cases it does not cover, and it may be
prone to false-positives.  Use at your own risk. *** /WARNING ***

Overview
--------

 This project provides a simple stateless failover mechanism, intended for use
with Palo Alto Networks firewalls in AWS.  Each firewall pair must be deployed
within a single VPC, but can span availability zones.  Each firewall has a
floating static route with a path monitoring object configured.  The path
monitoring targets are the IP address(es) of the peer firewall.  If one or more
of those peer IP addresses becomes unreachable for a specified period of time,
the path monitoring object goes down, generating a log message that triggers
a call to an AWS Lambda service that changes the route table association(s) for
the subnets the peer firewall services.  Once the peer firewall recovers,
the path monitoring object recovers and another log message is generated,
triggering another Lambda call to switch the route table associations to their
normal values.  The configuration for each firewall, its subnets, and the
sick/healthy route tables, are configured in a JSON-formatted file stored in
S3.
