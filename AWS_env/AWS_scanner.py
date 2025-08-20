import boto3
import subprocess
from botocore.exceptions import ClientError

# ----------- EC2 SCAN ----------
def scan_ec2_instances():
    ec2 = boto3.client("ec2")
    print("[+] Scanning EC2 Instances...")
    try:
        response = ec2.describe_instances()
        for res in response['Reservations']:
            for instance in res['Instances']:
                instance_id = instance['InstanceId']
                public_ip = instance.get('PublicIpAddress')
                sg_ids = [sg['GroupId'] for sg in instance.get('SecurityGroups', [])]

                print(f"  - Instance ID: {instance_id}")
                print(f"    Public IP: {public_ip}")
                if public_ip:
                    run_nmap(public_ip)

                check_security_groups(sg_ids)
    except ClientError as e:
        print(f"[!] EC2 Error: {e}")

# ----------- SG CHECK ----------
def check_security_groups(sg_ids):
    ec2 = boto3.client("ec2")
    for sg_id in sg_ids:
        response = ec2.describe_security_groups(GroupIds=[sg_id])
        for sg in response['SecurityGroups']:
            for perm in sg['IpPermissions']:
                for ip_range in perm.get('IpRanges', []):
                    cidr = ip_range.get('CidrIp')
                    if cidr == '0.0.0.0/0':
                        print(f"    ⚠️  Insecure SG: {sg['GroupName']} ({sg_id}) exposes port(s) {perm.get('FromPort')} to the world")

# ----------- S3 SCAN ----------
def scan_s3_buckets():
    s3 = boto3.client("s3")
    print("[+] Scanning S3 Buckets...")
    buckets = s3.list_buckets()
    for bucket in buckets['Buckets']:
        name = bucket['Name']
        try:
            acl = s3.get_bucket_acl(Bucket=name)
            for grant in acl['Grants']:
                if 'AllUsers' in str(grant.get('Grantee')):
                    print(f"  ⚠️  Public bucket found: {name}")
        except ClientError as e:
            print(f"  [!] Error accessing bucket {name}: {e}")

# ----------- IAM SCAN ----------
def scan_iam_users():
    iam = boto3.client('iam')
    print("[+] Scanning IAM Users...")
    users = iam.list_users()
    for user in users['Users']:
        username = user['UserName']
        attached = iam.list_attached_user_policies(UserName=username)
        for policy in attached['AttachedPolicies']:
            print(f"  - User: {username} has attached policy: {policy['PolicyName']}")

# ----------- NMAP ----------
def run_nmap(ip):
    print(f"    [NMAP] Scanning {ip} for open ports...")
    try:
        result = subprocess.run(['nmap', '-sS', '-Pn', '-T4', ip], capture_output=True, text=True, timeout=30)
        print(f"    {result.stdout.splitlines()[0]}")
    except Exception as e:
        print(f"    [!] Nmap failed: {e}")

# ----------- MAIN ----------
if __name__ == "__main__":
    print("=== AWS Pentest Scanner ===\n")
    scan_ec2_instances()
    scan_s3_buckets()
    scan_iam_users()
