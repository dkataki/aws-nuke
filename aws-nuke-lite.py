#pip install boto3 botocore

#!/usr/bin/env python3
# Author: Debajit Kataki (Python version)

import boto3
import botocore
import sys

AWS_REGION = "us-east-1"

def confirm():
    print("⚠️  This script will DELETE AWS resources in the configured AWS profile/region!")
    confirm = input("Are you sure? Type 'NUKE' to continue: ")
    if confirm != "NUKE":
        print("Aborted.")
        sys.exit(0)

def get_account():
    sts = boto3.client("sts")
    identity = sts.get_caller_identity()
    print(f"🔍 Using AWS Account: {identity['Account']} ({identity['Arn']})")

def safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except botocore.exceptions.ClientError as e:
        print(f"❌ Skipping due to error: {e}")
        return None

def delete_eks():
    eks = boto3.client("eks", region_name=AWS_REGION)
    clusters = eks.list_clusters().get("clusters", [])
    for cluster in clusters:
        print(f"📦 EKS Cluster: {cluster}")
        ngs = eks.list_nodegroups(clusterName=cluster).get("nodegroups", [])
        for ng in ngs:
            print(f"🧨 Deleting EKS Node Group: {ng}")
            safe_call(eks.delete_nodegroup, clusterName=cluster, nodegroupName=ng)
            eks.get_waiter('nodegroup_deleted').wait(clusterName=cluster, nodegroupName=ng)
        print(f"🧨 Deleting EKS Cluster: {cluster}")
        safe_call(eks.delete_cluster, name=cluster)

def terminate_ec2():
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    res = ec2.describe_instances()
    ids = [i["InstanceId"] for r in res["Reservations"] for i in r["Instances"]]
    if ids:
        print(f"🧨 Terminating EC2 instances: {' '.join(ids)}")
        safe_call(ec2.terminate_instances, InstanceIds=ids)

def delete_security_groups():
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    for sg in ec2.describe_security_groups()["SecurityGroups"]:
        if sg["GroupName"] != "default":
            print(f"🧨 Deleting Security Group: {sg['GroupId']}")
            safe_call(ec2.delete_security_group, GroupId=sg["GroupId"])

def delete_key_pairs():
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    keys = ec2.describe_key_pairs().get("KeyPairs", [])
    for key in keys:
        print(f"🧨 Deleting Key Pair: {key['KeyName']}")
        safe_call(ec2.delete_key_pair, KeyName=key["KeyName"])

def release_eips():
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    for eip in ec2.describe_addresses().get("Addresses", []):
        print(f"🧨 Releasing Elastic IP: {eip['AllocationId']}")
        safe_call(ec2.release_address, AllocationId=eip["AllocationId"])

def delete_internet_gateways():
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    for igw in ec2.describe_internet_gateways()["InternetGateways"]:
        for att in igw.get("Attachments", []):
            safe_call(ec2.detach_internet_gateway, InternetGatewayId=igw["InternetGatewayId"], VpcId=att["VpcId"])
        print(f"🧨 Deleting IGW: {igw['InternetGatewayId']}")
        safe_call(ec2.delete_internet_gateway, InternetGatewayId=igw["InternetGatewayId"])

def delete_nat_gateways():
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    for nat in ec2.describe_nat_gateways().get("NatGateways", []):
        print(f"🧨 Deleting NAT Gateway: {nat['NatGatewayId']}")
        safe_call(ec2.delete_nat_gateway, NatGatewayId=nat["NatGatewayId"])

def delete_route_tables():
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    for rt in ec2.describe_route_tables()["RouteTables"]:
        if not any(assoc.get("Main") for assoc in rt["Associations"]):
            print(f"🧨 Deleting Route Table: {rt['RouteTableId']}")
            safe_call(ec2.delete_route_table, RouteTableId=rt["RouteTableId"])

def delete_nacls():
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    for nacl in ec2.describe_network_acls()["NetworkAcls"]:
        if not nacl["IsDefault"]:
            print(f"�� Deleting NACL: {nacl['NetworkAclId']}")
            safe_call(ec2.delete_network_acl, NetworkAclId=nacl["NetworkAclId"])

def delete_subnets():
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    for sn in ec2.describe_subnets()["Subnets"]:
        print(f"🧨 Deleting Subnet: {sn['SubnetId']}")
        safe_call(ec2.delete_subnet, SubnetId=sn["SubnetId"])

def delete_vpcs():
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    for vpc in ec2.describe_vpcs()["Vpcs"]:
        if not vpc["IsDefault"]:
            print(f"🧨 Deleting VPC: {vpc['VpcId']}")
            safe_call(ec2.delete_vpc, VpcId=vpc["VpcId"])

def delete_load_balancers():
    elb = boto3.client("elb", region_name=AWS_REGION)
    try:
        for lb in elb.describe_load_balancers()["LoadBalancerDescriptions"]:
            print(f"🧨 Deleting Classic Load Balancer: {lb['LoadBalancerName']}")
            safe_call(elb.delete_load_balancer, LoadBalancerName=lb["LoadBalancerName"])
    except:
        pass
    elbv2 = boto3.client("elbv2", region_name=AWS_REGION)
    try:
        for lb in elbv2.describe_load_balancers()["LoadBalancers"]:
            print(f"🧨 Deleting ALB/NLB: {lb['LoadBalancerArn']}")
            safe_call(elbv2.delete_load_balancer, LoadBalancerArn=lb["LoadBalancerArn"])
    except:
        pass

def delete_target_groups():
    elbv2 = boto3.client("elbv2", region_name=AWS_REGION)
    try:
        for tg in elbv2.describe_target_groups()["TargetGroups"]:
            print(f"🧨 Deleting Target Group: {tg['TargetGroupArn']}")
            safe_call(elbv2.delete_target_group, TargetGroupArn=tg["TargetGroupArn"])
    except:
        pass

def main():
    confirm()
    get_account()

    delete_eks()
    terminate_ec2()
    delete_security_groups()
    release_eips()
    delete_internet_gateways()
    delete_nat_gateways()
    delete_route_tables()
    delete_nacls()
    delete_subnets()
    delete_vpcs()
    delete_load_balancers()
    delete_target_groups()

    print(f"✅ AWS nuking complete in region: {AWS_REGION}")

if __name__ == "__main__":
    main()

