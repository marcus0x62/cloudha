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

Installation
------------
0. Prerequisites
 * AWS CLI tools
 * Git client
 * At least two firewalls in AWS running PAN-OS 8.0 or later
1. Clone the git repository -- 'git clone https://github.com/marcus0x62/cloudha'
2. Create an S3 bucket with 'aws s3 cb [bucket_name]'
3. Edit cloudha.py and modify the CLOUDHA_BUCKET variable with the name of the
   S3 bucket you created.
4. Edit the example-config.json file and enter your firewall serial numbers,
   and the healthy and sick route tables for those firewalls.
5. Build the cloudha.zip file either by running 'make', or
   'zip cloudha.zip clouldha.py common.py'
6. Copy the config file and deployment package to S3 with
   'aws s3 cp config.json s3://[bucket-name]/config.json' and
   'aws s3 cp cloudha.zip s3://[bucket-name]/cloudha.zip'
7. Deploy the CFT with 'aws cloudformation create-stack --stack-name cloudha --template-body file://cloudha-cft.json --parameters ParameterKey=S3Bucket,ParameterValue=[bucket-name] ParameterKey=S3Key,ParameterValue=cloudha.zip --capabilities CAPABILITY_IAM'.  This is going to create a Lambda service, an API
   Gateway endpoint, an IAM role for the Lambda service, as well as a few other
   things.  Please be sure to review the Cloudformation Template to ensure you
   are comfortable with the resources being created, the costs from AWS of
   those resources, and the security specified in the CFT.
8. After the stack is deployed, you can retrieve the API endpoint and key:
   aws cloudformation describe-stacks --stack-name cloudha (look for "Outputs")

   The API key can be retrieved with:

   aws apigateway get-api-key --api-key [api-key-id] --include-value
9. Configure your firewalls to monitor the appropriate IP address(s) and
   trigger the Lambda service when a failure occurs (see example-firewall-config for config details.)

