import logging
import os
import sys

import boto3
from boto3.session import Session

logger = logging.getLogger()
logger.setLevel(logging.INFO)

error_response = {
    "statusCode": 500,
    "headers": {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Credentials': True,
    },
    "body": "An error occurred. Please contact the Administrator."
}


def checkAccountIdInOrg(account_id_to_check, organization_account_id):
    sts_client = boto3.client('sts')
    assume_role_response = sts_client.assume_role(
        RoleArn='arn:aws:iam::' + organization_account_id + ':role/AwsVpcDeleteOrgaRole',
        RoleSessionName='orgSession',
    )

    org_session = Session(aws_access_key_id=assume_role_response['Credentials']['AccessKeyId'],
                          aws_secret_access_key=assume_role_response['Credentials']['SecretAccessKey'],
                          aws_session_token=assume_role_response['Credentials']['SessionToken'])

    org_sts_client = org_session.client('sts')
    account_id = org_sts_client.get_caller_identity()["Account"]
    logger.info(f"Switched to account id {account_id}")
    org_org_client = org_session.client('organizations')
    logger.info(f"Try to describe data for project account {account_id_to_check}")
    try:
        describe_account_response = org_org_client.describe_account(
            AccountId=account_id_to_check
        )
        logger.info(f"Found account {describe_account_response['Account']['Name']} in organization")
        return True
    except:
        logger.error("Provided account id was not found in the organization")
        return False


def deleteDefaultVpcs(account_id_to_delete_vpc, regions_to_delete_default_vpc):
    sts_client = boto3.client('sts')
    assume_role_response = sts_client.assume_role(
        RoleArn='arn:aws:iam::' + account_id_to_delete_vpc + ':role/AwsVpcDeleteProjectRole',
        RoleSessionName='vpcSession',
    )

    org_session = Session(aws_access_key_id=assume_role_response['Credentials']['AccessKeyId'],
                          aws_secret_access_key=assume_role_response['Credentials']['SecretAccessKey'],
                          aws_session_token=assume_role_response['Credentials']['SessionToken'])

    org_sts_client = org_session.client('sts')
    account_id = org_sts_client.get_caller_identity()["Account"]
    logger.info(f"Switched to account id {account_id}")
    for region in regions_to_delete_default_vpc.split(","):
        logger.info(f"Working on region {region}")
        region_ec2_org_client = org_session.client('ec2', region_name = region)
        describe_vpcs_response = region_ec2_org_client.describe_vpcs(
            Filters=[
            {
                'Name' : 'isDefault',
                'Values' : [
                    'true',
                ],
            },
            ]
        )
        if len(describe_vpcs_response['Vpcs']) == 0:
            logger.warn(f"No default VPC found in this region")
            continue
        else:
            for vpc in describe_vpcs_response['Vpcs']:
                vpc_id = vpc['VpcId']
                describe_internet_gateways_response = region_ec2_org_client.describe_internet_gateways(
                    Filters=[
                        {
                            'Name': 'attachment.vpc-id',
                            'Values': [
                                vpc_id,
                            ]
                        },
                    ]
                )
                if len(describe_internet_gateways_response['InternetGateways']) == 0:
                    logger.warn(f"No internet gateways found in vpc {vpc_id}")
                else:
                    igw_id = describe_internet_gateways_response['InternetGateways'][0]['InternetGatewayId']
                    region_ec2_org_client.detach_internet_gateway(
                        InternetGatewayId=igw_id,
                        VpcId=vpc_id
                    )
                    logger.info(f"Internet gateway {igw_id} is detached")
                    region_ec2_org_client.delete_internet_gateway(
                        InternetGatewayId=igw_id
                    )
                    logger.info(f"Internet gateway {igw_id} is deleted")

                describe_subnets_response = region_ec2_org_client.describe_subnets(
                    Filters=[
                        {
                            'Name': 'vpc-id',
                            'Values': [
                                vpc_id,
                            ]
                        },
                    ]
                )
                if len(describe_subnets_response['Subnets']) == 0:
                    logger.warn(f"No subnets found in this VPC")
                else:
                    for subnet in describe_subnets_response['Subnets']:
                        subnet_id = subnet['SubnetId']
                        region_ec2_org_client.delete_subnet(
                            SubnetId=subnet_id
                        )
                        logger.info(f"Subnet {subnet_id} is deleted")
                region_ec2_org_client.delete_vpc(
                    VpcId=vpc_id
                )
                logger.info(f"VPC {vpc_id} is deleted")


def main(event, context):
    try:
        account_id = event['multiValueQueryStringParameters']['account_id'][0]
    except:
        logger.error("The parameter account_id was not provided. Provided parameters: " + str(event['multiValueQueryStringParameters']))
        return error_response
    logger.info('Provided account id: ' + account_id)

    try:
        organization_account_id = os.environ['Organization_Account_Id']
        regions_to_delete_default_vpc = os.environ['Regions_To_Delete_Default_Vpc']
    except:
        logger.error("Could not read env variable Organization_Account_Id")
        raise

    if checkAccountIdInOrg(account_id, organization_account_id):
        logger.info("Going to delete the default VPCs")
        deleteDefaultVpcs(account_id,regions_to_delete_default_vpc)
        response = {
            "statusCode": 200,
            "headers": {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True,
            },
            "body": "The default VPC in the AWS account " + account_id + " was deleted"
        }
        logger.info('Success response will be send')
        return response
    return error_response


if __name__ == "__main__":
    main(0, 0)
