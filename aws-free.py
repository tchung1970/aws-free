#!/usr/bin/env python3
# aws-free.py
# by Thomas Chung
# on 2025-08-22
#
# AWS Free Tier Instance Manager - Complete lifecycle management for EC2 free tier instances
#
# What this script does step by step:
# 1. Checks and auto-installs dependencies (boto3, python-dotenv, awscli)
# 2. Validates AWS credentials from ~/.env file
# 3. Provides command-line interface for:
#    - Creating t3.micro instances with Ubuntu Server 24.04 LTS
#    - Listing all running instances in formatted table
#    - Deleting instances with confirmation prompts
#    - SSH access to running instances with automatic key management
#    - Opening AWS console pages (instances and key pairs) in browser
# 4. Enforces free tier limits (max 1 t3.micro instance at a time)
# 5. Generates SSH key pairs locally and imports public keys to AWS
# 6. Creates security groups with SSH access automatically
# 7. Handles all AWS API interactions with proper error handling
#
# Key features:
# - Free tier enforcement to prevent accidental charges
# - Local SSH key generation for better security
# - Smart dependency management with user consent
# - Clean command interface with backward compatibility
# - Comprehensive error handling and user guidance

"""
EC2 Free Tier Instance Launcher

This script creates an AWS EC2 instance using the free tier eligible configuration:
- Free tier instance type (750 hours/month free)
- Ubuntu Server 24.04 LTS AMI
- Default VPC and security group
- Basic monitoring enabled

Requirements:
- boto3 library: pip install boto3
- AWS credentials configured (AWS CLI, environment variables, or IAM role)
"""

import sys
import subprocess
import os
import webbrowser

def check_dependencies():
    """Check if required dependencies are installed and prompt user to install if missing"""
    missing_deps = []
    missing_display = []
    missing_tools = []
    
    # Check for boto3
    try:
        import boto3
    except ImportError:
        missing_deps.append('boto3')
        missing_display.append('boto3 (AWS SDK for Python)')
    
    # Check for python-dotenv
    try:
        import dotenv
    except ImportError:
        missing_deps.append('python-dotenv')
        missing_display.append('python-dotenv')
    
    # Check for AWS CLI
    try:
        subprocess.check_output(['aws', '--version'], stderr=subprocess.STDOUT)
    except (subprocess.CalledProcessError, FileNotFoundError):
        missing_deps.append('awscli')
        missing_display.append('awscli (AWS Command Line Interface)')
        missing_tools.append('AWS CLI')
    
    # Check for GitHub CLI
    gh_missing = False
    try:
        subprocess.check_output(['gh', '--version'], stderr=subprocess.STDOUT)
    except (subprocess.CalledProcessError, FileNotFoundError):
        gh_missing = True
        missing_tools.append('GitHub CLI')
    
    if missing_deps:
        print("❌ Missing required dependencies:")
        for dep in missing_display:
            print(f"   - {dep}")
        
        print("\n📦 To install missing dependencies, run:")
        print(f"   pip install {' '.join(missing_deps)}")
        print("\n   Or install from requirements.txt:")
        print("   pip install -r requirements.txt")
        
        response = input("\n🤔 Would you like me to install them now? (Y/n): ").strip().lower()
        
        if response in ['y', 'yes', '']:
            try:
                print("📥 Installing dependencies...")
                subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing_deps)
                print("✅ Dependencies installed successfully!")
                
                # Try importing again to verify installation
                try:
                    import boto3
                    import dotenv
                    print("✅ Python dependencies imported successfully")
                    
                    # Check AWS CLI again
                    try:
                        subprocess.check_output(['aws', '--version'], stderr=subprocess.STDOUT)
                        print("✅ AWS CLI is now available")
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        print("✅ AWS CLI installed but may need PATH refresh")
                        
                    # Check GitHub CLI again
                    try:
                        subprocess.check_output(['gh', '--version'], stderr=subprocess.STDOUT)
                        print("✅ GitHub CLI is available")
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        print("💡 GitHub CLI not found - install with: brew install gh")
                        
                except ImportError as e:
                    print(f"❌ Failed to import dependencies after installation: {e}")
                    sys.exit(1)
                    
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install dependencies: {e}")
                print("Please install manually using: pip install boto3 python-dotenv awscli")
                sys.exit(1)
        else:
            print("Please install the required dependencies and run the script again.")
            sys.exit(1)
    
    # Handle GitHub CLI separately since it's not a pip package
    if gh_missing:
        print("\n❌ Missing required tool:")
        print("   - GitHub CLI (gh)")
        print("\n📦 To install GitHub CLI:")
        print("   macOS: brew install gh")
        print("   Linux: https://cli.github.com/")
        print("   Windows: https://cli.github.com/")
        
        print("\n💡 GitHub CLI is required for repository management features")
        sys.exit(1)

# Check dependencies before importing AWS modules
check_dependencies()

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(os.path.expanduser('~/.env'))

def check_aws_credentials():
    """Check if AWS credentials are available and guide user if missing"""
    access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
    secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    missing_vars = []
    if not access_key_id:
        missing_vars.append('AWS_ACCESS_KEY_ID')
    if not secret_access_key:
        missing_vars.append('AWS_SECRET_ACCESS_KEY')
    
    if missing_vars:
        print("❌ Missing AWS credentials in environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        
        print("\n📝 To add missing credentials to your ~/.env file, run:")
        if 'AWS_ACCESS_KEY_ID' in missing_vars:
            print('   echo "AWS_ACCESS_KEY_ID=your_access_key_id_here" >> ~/.env')
        if 'AWS_SECRET_ACCESS_KEY' in missing_vars:
            print('   echo "AWS_SECRET_ACCESS_KEY=your_secret_access_key_here" >> ~/.env')
        
        print("\n💡 Or create ~/.env file manually with:")
        print("   AWS_ACCESS_KEY_ID=AKIA...")
        print("   AWS_SECRET_ACCESS_KEY=wJalr...")
        
        print("\n🔗 Get your AWS credentials from:")
        print("   AWS Console → IAM → Users → Your User → Security Credentials → Access Keys")
        
        sys.exit(1)

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


def get_latest_ubuntu_ami(ec2_client):
    """Get the latest Ubuntu Server 24.04 LTS AMI ID"""
    try:
        # Try multiple common patterns for Ubuntu 24.04 LTS
        patterns = [
            'ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*',
            'ubuntu/images/hvm-ssd/ubuntu-noble-24.04-amd64-server-*',
            'ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*'  # Fallback to 22.04 LTS
        ]
        
        for pattern in patterns:
            response = ec2_client.describe_images(
                Owners=['099720109477'],  # Canonical's AWS account ID
                Filters=[
                    {'Name': 'name', 'Values': [pattern]},
                    {'Name': 'architecture', 'Values': ['x86_64']},
                    {'Name': 'virtualization-type', 'Values': ['hvm']},
                    {'Name': 'state', 'Values': ['available']}
                ]
            )
            
            # Sort by creation date and get the latest
            images = sorted(response['Images'], key=lambda x: x['CreationDate'], reverse=True)
            if images:
                return images[0]['ImageId'], images[0]['Name']
        
        raise Exception("No Ubuntu Server LTS AMI found")
            
    except ClientError as e:
        raise Exception(f"Error fetching AMI: {e}")


def create_key_pair(ec2_client, key_name):
    """Create a new SSH key pair locally and import public key to AWS"""
    try:
        # Set up paths
        ssh_dir = os.path.expanduser('~/.ssh')
        os.makedirs(ssh_dir, exist_ok=True)
        
        key_file_path = os.path.join(ssh_dir, f'{key_name}')
        pub_key_file_path = os.path.join(ssh_dir, f'{key_name}.pub')
        
        # Generate SSH key pair locally using ssh-keygen
        try:
            # Generate RSA key pair (2048 bits for compatibility)
            subprocess.run([
                'ssh-keygen', '-t', 'rsa', '-b', '2048',
                '-f', key_file_path,
                '-N', '',  # No passphrase
                '-C', f'{key_name}@aws-free-script'
            ], check=True, capture_output=True)
            
            print(f"✅ Generated SSH key pair locally")
            print(f"   Private key: {key_file_path}")
            print(f"   Public key: {pub_key_file_path}")
            
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise Exception(f"Failed to generate SSH key pair. Please install ssh-keygen: {e}")
        
        # Read the public key
        with open(pub_key_file_path, 'r') as pub_file:
            public_key_material = pub_file.read().strip()
        
        # Import public key to AWS
        try:
            ec2_client.import_key_pair(
                KeyName=key_name,
                PublicKeyMaterial=public_key_material
            )
            print(f"✅ Imported public key to AWS as: {key_name}")
            
        except ClientError as e:
            if 'InvalidKeyPair.Duplicate' in str(e):
                print(f"⚠️  Key pair '{key_name}' already exists in AWS")
                print(f"   Using existing AWS key pair with local keys")
            else:
                raise Exception(f"Failed to import key pair to AWS: {e}")
        
        # Set proper permissions (read-only for owner)
        os.chmod(key_file_path, 0o600)
        os.chmod(pub_key_file_path, 0o644)
        
        return key_name
        
    except Exception as e:
        # Clean up partial files if creation failed
        for path in [key_file_path, pub_key_file_path]:
            if 'path' in locals() and os.path.exists(path):
                os.remove(path)
        raise e


def create_security_group(ec2_client):
    """Create a basic security group allowing SSH access"""
    try:
        # Check if security group already exists
        try:
            response = ec2_client.describe_security_groups(
                GroupNames=['ec2-free-tier-sg']
            )
            print(f"Using existing security group: {response['SecurityGroups'][0]['GroupId']}")
            return response['SecurityGroups'][0]['GroupId']
        except ClientError as e:
            if 'InvalidGroup.NotFound' not in str(e):
                raise
        
        # Create new security group
        response = ec2_client.create_security_group(
            GroupName='ec2-free-tier-sg',
            Description='Security group for free tier EC2 instance'
        )
        
        security_group_id = response['GroupId']
        
        # Add SSH inbound rule
        ec2_client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'SSH access'}]
                }
            ]
        )
        
        print(f"Created security group: {security_group_id}")
        return security_group_id
        
    except ClientError as e:
        raise Exception(f"Error creating security group: {e}")


def list_instances(region='us-west-2'):
    """List all EC2 instances"""
    try:
        ec2_client = boto3.client('ec2', region_name=region)
        
        response = ec2_client.describe_instances(
            Filters=[
                {'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'stopped']}
            ]
        )
        
        instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instances.append(instance)
        
        if not instances:
            print(f"\nNo running instances found in region {region}")
            print()
            return
        
        print(f"{'Instance ID':<20} {'Type':<12} {'State':<12} {'Public IP':<15} {'Name':<20}")
        print("=" * 85)
        
        for instance in instances:
            instance_id = instance['InstanceId']
            instance_type = instance['InstanceType']
            state = instance['State']['Name']
            public_ip = instance.get('PublicIpAddress', 'N/A')
            
            # Get Name tag
            name = 'N/A'
            for tag in instance.get('Tags', []):
                if tag['Key'] == 'Name':
                    name = tag['Value']
                    break
            
            print(f"{instance_id:<20} {instance_type:<12} {state:<12} {public_ip:<15} {name:<20}")
        
        print()
    
    except ClientError as e:
        print(f"AWS Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def ssh_to_instance(instance_id=None, region='us-west-2'):
    """SSH to an instance, with option to create key pair if needed"""
    try:
        ec2_client = boto3.client('ec2', region_name=region)
        
        # If no instance ID provided, find the running instance automatically
        if not instance_id:
            response = ec2_client.describe_instances(
                Filters=[
                    {'Name': 'instance-state-name', 'Values': ['running']}
                ]
            )
            
            running_instances = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    running_instances.append(instance)
            
            if not running_instances:
                print("\nNo running instances found in region", region)
                print()
                return
            
            # Show the running instance in same format as list command
            print(f"{'Instance ID':<20} {'Type':<12} {'State':<12} {'Public IP':<15} {'Name':<20}")
            print("=" * 85)
            
            for instance in running_instances:
                instance_id = instance['InstanceId']
                instance_type = instance['InstanceType']
                state = instance['State']['Name']
                public_ip = instance.get('PublicIpAddress', 'N/A')
                
                # Get Name tag
                name = 'N/A'
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        name = tag['Value']
                        break
                
                print(f"{instance_id:<20} {instance_type:<12} {state:<12} {public_ip:<15} {name:<20}")
            
            print()
            
            # Use the first (and only) instance
            instance_id = running_instances[0]['InstanceId']
        
        # Get instance details
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]
        
        if instance['State']['Name'] != 'running':
            print(f"Instance {instance_id} is not running (current state: {instance['State']['Name']})")
            return
        
        public_ip = instance.get('PublicIpAddress')
        if not public_ip:
            print(f"Instance {instance_id} doesn't have a public IP address")
            return
        
        key_name = instance.get('KeyName')
        if not key_name:
            print(f"Instance {instance_id} was launched without a key pair")
            create_key = input("🔑 Would you like me to create a key pair for future instances? (Y/n): ").strip().lower()
            
            if create_key in ['y', 'yes', '']:
                new_key_name = f"ec2-free-key-{int(__import__('time').time())}"
                try:
                    create_key_pair(ec2_client, new_key_name)
                    print(f"✅ Key pair '{new_key_name}' created for future instances")
                    print("Note: This won't help with the current instance, but will be available for new ones")
                except Exception as e:
                    print(f"⚠️  Failed to create key pair: {e}")
            
            print("❌ Cannot SSH to this instance - no key pair associated")
            return
        
        # Check if key file exists locally
        key_file_path = os.path.expanduser(f'~/.ssh/{key_name}')
        if not os.path.exists(key_file_path):
            print(f"⚠️  Key file not found: {key_file_path}")
            print("You may need to:")
            print(f"1. Download the {key_name} file from AWS Console")
            print(f"2. Place it in ~/.ssh/{key_name}")
            print(f"3. Set permissions: chmod 600 ~/.ssh/{key_name}")
            return
        
        # Show SSH command and execute it
        ssh_command = f"ssh -i ~/.ssh/{key_name} ubuntu@{public_ip}"
        print(f"\n🔗 SSH Command:")
        print(f"{ssh_command}")
        
        try:
            print("\n🚀 Opening SSH connection...")
            subprocess.run(['ssh', '-i', key_file_path, f'ubuntu@{public_ip}'])
        except KeyboardInterrupt:
            print("\nSSH connection interrupted")
        except FileNotFoundError:
            print("SSH command not found. Please install SSH client.")
        except Exception as e:
            print(f"Error executing SSH: {e}")
        
    except ClientError as e:
        if 'InvalidInstanceID.NotFound' in str(e):
            print(f"Instance {instance_id} not found")
        else:
            print(f"AWS Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def open_console(region='us-west-2'):
    """Open AWS EC2 console in browser"""
    console_url = f"https://{region}.console.aws.amazon.com/ec2/home?region={region}#Instances:instanceState=running"
    
    print(f"🌐 Opening AWS EC2 console for region {region}...")
    print(f"URL: {console_url}")
    
    try:
        webbrowser.open(console_url)
        print("✅ Console opened in your default browser")
        print()
    except Exception as e:
        print(f"⚠️  Could not open browser automatically: {e}")
        print(f"Please copy and paste this URL into your browser:")
        print(f"{console_url}")
        print()


def open_key_pairs(region='us-west-2'):
    """Open AWS Key Pairs console in browser"""
    key_pairs_url = f"https://{region}.console.aws.amazon.com/ec2/home?region={region}#KeyPairs:"
    
    print(f"🔑 Opening AWS Key Pairs console for region {region}...")
    print(f"URL: {key_pairs_url}")
    
    try:
        webbrowser.open(key_pairs_url)
        print("✅ Key Pairs console opened in your default browser")
        print()
    except Exception as e:
        print(f"⚠️  Could not open browser automatically: {e}")
        print(f"Please copy and paste this URL into your browser:")
        print(f"{key_pairs_url}")
        print()


def delete_instance(instance_id, region='us-west-2'):
    """Delete (terminate) an EC2 instance"""
    try:
        ec2_client = boto3.client('ec2', region_name=region)
        
        # Get instance details first
        try:
            response = ec2_client.describe_instances(InstanceIds=[instance_id])
            instance = response['Reservations'][0]['Instances'][0]
            state = instance['State']['Name']
            
            if state == 'terminated':
                print(f"Instance {instance_id} is already terminated")
                print("Note: 'Terminated' means the instance has been permanently deleted and cannot be recovered.")
                print("Terminated instances don't consume resources or incur charges.")
                print("They will disappear from the AWS console within ~1 hour after termination.")
                return
            
            # Get Name tag
            name = 'N/A'
            for tag in instance.get('Tags', []):
                if tag['Key'] == 'Name':
                    name = tag['Value']
                    break
            
            print(f"Instance details:")
            print()
            print(f"{'Instance ID':<20} {'Type':<12} {'State':<12} {'Public IP':<15} {'Name':<20}")
            print("=" * 85)
            
            public_ip = instance.get('PublicIpAddress', 'N/A')
            print(f"{instance_id:<20} {instance['InstanceType']:<12} {state:<12} {public_ip:<15} {name:<20}")
            print()
            
        except ClientError as e:
            if 'InvalidInstanceID.NotFound' in str(e):
                print(f"Instance {instance_id} not found")
                return
            raise
        
        # Confirm deletion
        confirm = input(f"⚠️  Are you sure you want to delete (terminate) instance {instance_id}? (Y/n): ").strip().lower()
        
        if confirm in ['n', 'no']:
            print("Deletion cancelled")
            return
        
        # Terminate instance
        print("Terminating instance...")
        ec2_client.terminate_instances(InstanceIds=[instance_id])
        
        print(f"✅ Instance {instance_id} termination initiated")
        print("Note: It may take a few minutes for the instance to fully terminate")
        print()
        
    except ClientError as e:
        print(f"AWS Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def launch_instance(region='us-west-2', key_name=None):
    """Launch a free tier EC2 instance"""
    try:
        # Create EC2 client
        ec2_client = boto3.client('ec2', region_name=region)
        
        # Check if there's already a free tier instance running
        print("Checking existing instances...")
        response = ec2_client.describe_instances(
            Filters=[
                {'Name': 'instance-type', 'Values': ['t3.micro']},
                {'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'stopped']}
            ]
        )
        
        existing_instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                existing_instances.append(instance)
        
        if existing_instances:
            print("❌ Free tier limit reached!")
            print("You already have the following free tier instance(s):")
            print()
            print(f"{'Instance ID':<20} {'Type':<12} {'State':<12} {'Public IP':<15} {'Name':<20}")
            print("=" * 85)
            
            for instance in existing_instances:
                instance_id = instance['InstanceId']
                instance_type = instance['InstanceType']
                state = instance['State']['Name']
                public_ip = instance.get('PublicIpAddress', 'N/A')
                
                # Get Name tag
                name = 'N/A'
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        name = tag['Value']
                        break
                
                print(f"{instance_id:<20} {instance_type:<12} {state:<12} {public_ip:<15} {name:<20}")
            
            print(f"\n💡 AWS Free Tier allows only ONE free tier instance at a time.")
            print("To create a new instance, you must first delete (terminate) the existing one.")
            print()
            
            return None
        
        # Check if we need to create a key pair first
        if not key_name:
            # Check if aws_ec2_free key pair already exists
            private_key_path = os.path.expanduser('~/.ssh/aws_ec2_free')
            public_key_path = os.path.expanduser('~/.ssh/aws_ec2_free.pub')
            
            if os.path.exists(private_key_path) and os.path.exists(public_key_path):
                print(f"\n✅ Found existing SSH key pair: aws_ec2_free")
                key_name = "aws_ec2_free"
            else:
                create_key = input("\n🔑 SSH key pair (aws_ec2_free) not found. Create it now? (Y/n): ").strip().lower()
                
                if create_key in ['y', 'yes', '']:
                    key_name = "aws_ec2_free"
                    try:
                        key_name = create_key_pair(ec2_client, key_name)
                        print(f"✅ Key pair '{key_name}' will be used for SSH access")
                    except Exception as e:
                        print(f"⚠️  Failed to create key pair: {e}")
                        print("Continuing without key pair - SSH access won't be available")
                        key_name = None
                else:
                    print("Continuing without key pair - SSH access won't be available")

        # Get latest Ubuntu Server 24.04 LTS AMI
        print("\nFinding latest Ubuntu Server 24.04 LTS AMI...")
        ami_id, ami_name = get_latest_ubuntu_ami(ec2_client)
        print(f"Using AMI: {ami_id}")
        print(f"AMI Name: {ami_name}")
        
        # Create security group
        print("Setting up security group...")
        security_group_id = create_security_group(ec2_client)
        
        # Instance configuration
        instance_config = {
            'ImageId': ami_id,
            'MinCount': 1,
            'MaxCount': 1,
            'InstanceType': 't3.micro',  # Free tier eligible
            'SecurityGroupIds': [security_group_id],
            'Monitoring': {'Enabled': False},  # Detailed monitoring costs extra
            'TagSpecifications': [
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': 'free-tier'},
                        {'Key': 'Purpose', 'Value': 'FreeTier'},
                        {'Key': 'CreatedBy', 'Value': 'aws-free-script'}
                    ]
                }
            ]
        }
        
        # Add key pair if specified
        if key_name:
            instance_config['KeyName'] = key_name
            print(f"Using key pair: {key_name}")
        else:
            print("No key pair specified - use 'ssh' command later to connect with a key pair")
        
        # Launch instance
        print("Launching EC2 instance...")
        response = ec2_client.run_instances(**instance_config)
        
        instance_id = response['Instances'][0]['InstanceId']
        print(f"Instance launched successfully!")
        print(f"Instance ID: {instance_id}")
        print(f"Region: {region}")
        
        # Wait for instance to be running
        print("Waiting for instance to be running...")
        waiter = ec2_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id])
        
        # Get instance details
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]
        
        print("\n=== Instance Details ===")
        print(f"Instance ID: {instance['InstanceId']}")
        print(f"Instance Type: {instance['InstanceType']}")
        print(f"State: {instance['State']['Name']}")
        print(f"Public IP: {instance.get('PublicIpAddress', 'N/A')}")
        print(f"Private IP: {instance.get('PrivateIpAddress', 'N/A')}")
        print(f"Launch Time: {instance['LaunchTime']}")
        
        
        return instance_id
        
    except NoCredentialsError:
        print("Error: AWS credentials not found. Please configure your credentials using:")
        print("- AWS CLI: aws configure")
        print("- Environment variables: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        print("- IAM role (if running on EC2)")
        sys.exit(1)
        
    except ClientError as e:
        print(f"AWS Error: {e}")
        sys.exit(1)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    """Main function"""
    print("AWS EC2 Free Tier Instance Manager")
    print("===================================")
    
    # Check AWS credentials first
    check_aws_credentials()
    
    # Get the actual AMI name for display
    try:
        import boto3
        ec2_client = boto3.client('ec2', region_name='us-west-2')
        _, ami_name = get_latest_ubuntu_ami(ec2_client)
        actual_image = ami_name
    except:
        # Fallback if we can't get the actual AMI
        actual_image = "ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server (latest)"
    
    print("Default Settings:")
    print("  AWS Region: us-west-2")
    print("  Instance Name: free-tier")
    print("  Instance Type: t3.micro (2 vCPU, 1 GB Memory) - Free tier eligible")
    print(f"  AMI Image: {actual_image}")
    print("  Operating System: Ubuntu Server 24.04 LTS (amd64)")
    print("  SSH User: ubuntu")
    print()
    
    # Default configuration
    region = 'us-west-2'  # Free tier is available in all regions
    
    # Command line argument parsing
    if len(sys.argv) > 1:
        # Check for multiple commands (invalid usage)
        commands = ['list', 'create', 'delete', 'ssh', 'key', 'web', 'instances', 'console', 'dashboard', 'help', '-h', '--help']
        provided_commands = [arg for arg in sys.argv[1:] if arg.lower() in commands]
        
        if len(provided_commands) > 1:
            # Show help for invalid usage
            print("\nUsage:")
            print("  python aws-free.py [command]")
            print("\nCommands:")
            print("  list      # List running instances")
            print("  create    # Create free-tier instance")
            print("  delete    # Delete free-tier instance")
            print("  ssh       # SSH to free-tier instance")
            print("  key       # Open AWS Key Pairs console")
            print("  web       # Open AWS Instances console")
            print("  help      # Show this help")
            print("\nNote: All instances will be free tier eligible")
            print("      Key pair created during instance creation")
            print()
            return
        
        command = sys.argv[1].lower()
        
        if command in ['-h', '--help', 'help']:
            print("\nUsage:")
            print("  python aws-free.py [command]")
            print("\nCommands:")
            print("  list      # List running instances")
            print("  create    # Create a new instance (default)")
            print("  delete    # Delete free-tier instance")
            print("  ssh       # SSH to free-tier instance")
            print("  key       # Open AWS Key Pairs console")
            print("  web       # Open AWS Instances console")
            print("  help      # Show this help")
            print("\nNote: All instances will be free tier eligible")
            print("      Key pair created during instance creation")
            return
        
        elif command == 'list':
            list_instances(region)
            return
        
        elif command == 'delete':
            # Find the single running instance to delete
            print()
            try:
                ec2_client = boto3.client('ec2', region_name=region)
                response = ec2_client.describe_instances(
                    Filters=[
                        {'Name': 'instance-type', 'Values': ['t3.micro']},
                        {'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'stopped']}
                    ]
                )
                
                instances = []
                for reservation in response['Reservations']:
                    for instance in reservation['Instances']:
                        instances.append(instance)
                
                if not instances:
                    print("No free tier instances found to delete")
                    print()
                    return
                
                if len(instances) == 1:
                    instance_id = instances[0]['InstanceId']
                    delete_instance(instance_id, region)
                else:
                    print("Multiple instances found. Please specify which one to delete:")
                    for i, instance in enumerate(instances, 1):
                        name = 'N/A'
                        for tag in instance.get('Tags', []):
                            if tag['Key'] == 'Name':
                                name = tag['Value']
                                break
                        print(f"{i}. {instance['InstanceId']} - {name} ({instance['State']['Name']})")
                    
                    try:
                        choice = int(input(f"\nSelect instance to delete (1-{len(instances)}): ")) - 1
                        if 0 <= choice < len(instances):
                            instance_id = instances[choice]['InstanceId']
                            delete_instance(instance_id, region)
                        else:
                            print("Invalid choice")
                            return
                    except ValueError:
                        print("Invalid choice")
                        return
                        
            except Exception as e:
                print(f"Error finding instance: {e}")
                sys.exit(1)
            return
        
        elif command == 'ssh':
            instance_id = None
            if len(sys.argv) > 2:
                instance_id = sys.argv[2]
            ssh_to_instance(instance_id, region)
            return
        
        elif command == 'key':
            open_key_pairs(region)
            return
        
        elif command in ['dashboard', 'console', 'instances', 'web']:
            open_console(region)
            return
        
        elif command == 'create':
            key_name = None
            if len(sys.argv) > 2:
                key_name = sys.argv[2]
            
            # Launch instance
            instance_id = launch_instance(region=region, key_name=key_name)
            
            if instance_id:
                print(f"\n✅ Free tier EC2 instance created successfully!")
                print(f"Remember: You get 750 hours per month of free tier usage for free.")
                print(f"Don't forget to stop/terminate the instance when not in use to avoid charges.")
                print()
            return
        
        else:
            # Backward compatibility - treat first arg as key_name for create
            key_name = sys.argv[1]
            
            # Launch instance (backward compatibility)
            instance_id = launch_instance(region=region, key_name=key_name)
            
            if instance_id:
                print(f"\n✅ Free tier EC2 instance created successfully!")
                print(f"Remember: You get 750 hours per month of free tier usage for free.")
                print(f"Don't forget to stop/terminate the instance when not in use to avoid charges.")
                print()
            return
    else:
        # No arguments - show help
        print("\nUsage:")
        print("  python aws-free.py [command]")
        print("\nCommands:")
        print("  list      # List running instances")
        print("  create    # Create free-tier instance")
        print("  delete    # Delete free-tier instance")
        print("  ssh       # SSH to free-tier instance")
        print("  key       # Open AWS Key Pairs console")
        print("  web       # Open AWS Instances console")
        print("  help      # Show this help")
        print("\nNote: All instances will be free tier eligible")
        print("      Key pair created if needed during create")
        print()
        return


if __name__ == "__main__":
    main()