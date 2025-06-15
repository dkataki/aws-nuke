#!/bin/bash
#Author : Debajit Kataki
set -euo pipefail

echo "⚠️  This script will DELETE AWS resources in the configured profile/region!"
read -p "Are you sure? Type 'NUKE' to continue: " confirm

if [[ "$confirm" != "NUKE" ]]; then
  echo "Aborted."
  exit 1
fi

AWS_REGION="us-east-1"  # change this to your preferred region
export AWS_DEFAULT_REGION="$AWS_REGION"

echo "🔍 Using AWS Account:"
aws sts get-caller-identity

########################################
# 1. Delete EKS Node Groups and Clusters
########################################
eks_clusters=$(aws eks list-clusters --output text --query "clusters[]")
for cluster in $eks_clusters; do
  echo "📦 EKS Cluster: $cluster"

  # Delete managed node groups first
  ngs=$(aws eks list-nodegroups --cluster-name "$cluster" --query "nodegroups[]" --output text)
  for ng in $ngs; do
    echo "🧨 Deleting EKS Node Group: $ng"
    aws eks delete-nodegroup --cluster-name "$cluster" --nodegroup-name "$ng"
    echo "⏳ Waiting for node group $ng to delete..."
    aws eks wait nodegroup-deleted --cluster-name "$cluster" --nodegroup-name "$ng"
  done

  echo "🧨 Deleting EKS Cluster: $cluster"
  aws eks delete-cluster --name "$cluster"
done

########################################
# 2. Terminate EC2 Instances
########################################
instance_ids=$(aws ec2 describe-instances --query "Reservations[].Instances[].InstanceId" --output text)
if [[ -n "$instance_ids" ]]; then
  echo "🧨 Terminating EC2 instances: $instance_ids"
  aws ec2 terminate-instances --instance-ids $instance_ids
fi

########################################
# 3. Delete Security Groups (non-default)
########################################
sg_ids=$(aws ec2 describe-security-groups --query "SecurityGroups[?GroupName!='default'].GroupId" --output text)
for sg in $sg_ids; do
  echo "🧨 Deleting Security Group: $sg"
  aws ec2 delete-security-group --group-id "$sg" || true
done

########################################
# 4. Delete Key Pairs
########################################
#key_names=$(aws ec2 describe-key-pairs --query "KeyPairs[].KeyName" --output text)
#for key in $key_names; do
#  echo "🧨 Deleting key pair: $key"
#  aws ec2 delete-key-pair --key-name "$key"
#done

########################################
# 5. Release Elastic IPs
########################################
eip_allocs=$(aws ec2 describe-addresses --query "Addresses[].AllocationId" --output text)
for eip in $eip_allocs; do
  echo "🧨 Releasing Elastic IP: $eip"
  aws ec2 release-address --allocation-id "$eip"
done

########################################
# 6. Delete Internet Gateways
########################################
igws=$(aws ec2 describe-internet-gateways --query "InternetGateways[].InternetGatewayId" --output text)
for igw in $igws; do
  vpc_id=$(aws ec2 describe-internet-gateways --internet-gateway-ids "$igw" --query "InternetGateways[].Attachments[].VpcId" --output text)
  [[ -n "$vpc_id" ]] && aws ec2 detach-internet-gateway --internet-gateway-id "$igw" --vpc-id "$vpc_id"
  echo "🧨 Deleting IGW: $igw"
  aws ec2 delete-internet-gateway --internet-gateway-id "$igw"
done

########################################
# 7. Delete NAT Gateways
########################################
nat_ids=$(aws ec2 describe-nat-gateways --query "NatGateways[].NatGatewayId" --output text)
for nat in $nat_ids; do
  echo "🧨 Deleting NAT Gateway: $nat"
  aws ec2 delete-nat-gateway --nat-gateway-id "$nat"
done

########################################
# 8. Delete Route Tables (non-main)
########################################
route_table_ids=$(aws ec2 describe-route-tables --query "RouteTables[?Associations[?Main==\`false\`]].RouteTableId" --output text)
for rt in $route_table_ids; do
  echo "🧨 Deleting Route Table: $rt"
  aws ec2 delete-route-table --route-table-id "$rt"
done

########################################
# 9. Delete NACLs (non-default)
########################################
nacl_ids=$(aws ec2 describe-network-acls --query "NetworkAcls[?IsDefault==\`false\`].NetworkAclId" --output text)
for nacl in $nacl_ids; do
  echo "🧨 Deleting NACL: $nacl"
  aws ec2 delete-network-acl --network-acl-id "$nacl"
done

########################################
# 10. Delete Subnets
########################################
subnet_ids=$(aws ec2 describe-subnets --query "Subnets[].SubnetId" --output text)
for subnet in $subnet_ids; do
  echo "🧨 Deleting Subnet: $subnet"
  aws ec2 delete-subnet --subnet-id "$subnet"
done

########################################
# 11. Delete VPCs
########################################
vpc_ids=$(aws ec2 describe-vpcs --query "Vpcs[?IsDefault==\`false\`].VpcId" --output text)
for vpc in $vpc_ids; do
  echo "🧨 Deleting VPC: $vpc"
  aws ec2 delete-vpc --vpc-id "$vpc"
done

########################################
# 12. Delete Load Balancers
########################################
lbs=$(aws elb describe-load-balancers --query "LoadBalancerDescriptions[].LoadBalancerName" --output text 2>/dev/null || true)
for lb in $lbs; do
  echo "🧨 Deleting Classic Load Balancer: $lb"
  aws elb delete-load-balancer --load-balancer-name "$lb"
done

lbs_v2=$(aws elbv2 describe-load-balancers --query "LoadBalancers[].LoadBalancerArn" --output text 2>/dev/null || true)
for lb in $lbs_v2; do
  echo "🧨 Deleting ALB/NLB: $lb"
  aws elbv2 delete-load-balancer --load-balancer-arn "$lb"
done

########################################
# 13. Delete Target Groups
########################################
tgs=$(aws elbv2 describe-target-groups --query "TargetGroups[].TargetGroupArn" --output text 2>/dev/null || true)
for tg in $tgs; do
  echo "🧨 Deleting Target Group: $tg"
  aws elbv2 delete-target-group --target-group-arn "$tg"
done

echo "✅ AWS nuking complete in region: $AWS_REGION"

