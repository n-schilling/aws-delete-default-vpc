# AWS VPC Delete
AWS Serverless template to delete default VPCs in newly created AWS accounts as part of the account creation.

## Base architecture

![AWS VPC Delete base architecture](images/architecture.png "AWS VPC Delete base architecture")

### Used AWS Services

* AWS Lambda
* AWS API Gateway
* AWS Cloudwatch

## Implementation guide

Please follow all the steps below to deploy the solution.

### Requirements

* Serverless (tested with version 2.19.0)

### Deployment Requirements

1. Deploy the CloudFormation template "vpc_delete_orga_iam_role.yaml" in the AWS Organization main account
2. Deploy the CloudFormation template "vpc_delete_project_iam_role.yaml" in the newly created AWS project account

### Deployment

1. Clone this repository
2. Edit the parameters in the serverless.yml
  * organization_account_id: The AWS account it of the AWS Organization main account
3. run ```sls deploy``` to deploy the solution

The endpoint URL and the key can be found in the output of the serverless deploy. The account id for the account where the default VPC needs to be deleted must be provided via URL parameter "account_id".

### Undeploy

1. run ```sls remove``` to remove the solution
