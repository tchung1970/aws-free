# AWS Free Tier Instance Manager

A comprehensive Python CLI tool for managing AWS EC2 free tier instances with full lifecycle management including creation, listing, deletion, SSH access, and console opening for t2.micro/t3.micro instances.

## Features

- 🚀 **Instance Management**: Create, list, delete EC2 instances
- 🔑 **SSH Key Management**: Automatic key pair generation and AWS import
- 🌐 **Web Console Access**: Quick access to AWS EC2 and Key Pairs consoles
- 🛡️ **Free Tier Enforcement**: Prevents creation of multiple instances to stay within limits
- 📦 **Dependency Management**: Auto-installs missing packages with user consent
- ⚙️ **Smart Configuration**: Uses ~/.env for AWS credentials

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd aws-free

# Install dependencies
pip install -r requirements.txt

# Setup AWS credentials
echo "AWS_ACCESS_KEY_ID=your_access_key_id" > ~/.env
echo "AWS_SECRET_ACCESS_KEY=your_secret_access_key" >> ~/.env
```

### Usage

```bash
# Show help and available commands
python aws-free.py

# Create a new free tier instance
python aws-free.py create

# List all instances
python aws-free.py list

# SSH to running instance
python aws-free.py ssh

# Delete an instance
python aws-free.py delete

# Open AWS Key Pairs console
python aws-free.py key

# Open AWS Web Console
python aws-free.py web
```

## Commands

| Command | Description |
|---------|-------------|
| `list` | List running instances |
| `create` | Create free-tier instance |
| `delete` | Delete free-tier instance |
| `ssh` | SSH to free-tier instance |
| `key` | Open AWS Key Pairs console |
| `web` | Open AWS Web Console |
| `help` | Show help |

## Default Configuration

- **AWS Region**: us-west-2
- **Instance Name**: free-tier
- **Instance Type**: t3.micro (2 vCPU, 1 GB Memory) - Free tier eligible
- **Operating System**: Ubuntu Server 24.04 LTS (amd64)
- **SSH User**: ubuntu

## Recent Changes

### Key Management Improvements
- **Local Key Generation**: SSH key pairs are now generated locally using `ssh-keygen` instead of AWS
- **Both Keys Available**: Creates both private (`~/.ssh/aws_ec2_free`) and public (`~/.ssh/aws_ec2_free.pub`) keys locally
- **Public Key Import**: Only imports the public key to AWS for enhanced security
- **RSA 2048-bit**: Uses RSA 2048-bit keys for maximum compatibility

### Command Interface Updates
- **Streamlined Commands**: Removed unnecessary `key` command since keys are managed locally
- **Consistent Naming**: `web` command opens AWS Web Console (replaces `console`)
- **Backward Compatibility**: Old commands (`console`, `dashboard`, `instances`) still work
- **Improved Help**: Better formatted help messages with consistent spacing
- **Focused Interface**: Clean command set focusing on essential instance management

### Dependency Management
- **AWS CLI Support**: Added automatic AWS CLI installation and checking
- **GitHub CLI Requirement**: GitHub CLI (gh) is now required for repository management
- **Updated Requirements**: Added `awscli>=1.27.0` to requirements.txt
- **Platform-Specific Guidance**: Provides installation instructions for different operating systems
- **Better Error Handling**: Improved dependency installation feedback

### User Experience Enhancements
- **Cleaner Output**: Removed SSH command display from instance creation (use `ssh` command instead)
- **Better Formatting**: Improved spacing in command help display
- **Accurate Descriptions**: Updated help text to reflect when key pairs are created (during `create`, not `ssh`)

## Architecture

### Core Functions
- **`check_dependencies()`**: Auto-installs missing packages (boto3, python-dotenv, awscli)
- **`check_aws_credentials()`**: Validates ~/.env file and provides setup instructions
- **`launch_instance()`**: Creates t3.micro instances with free tier limit enforcement
- **`list_instances()`**: Shows formatted table with instance details
- **`delete_instance()`**: Safe deletion with confirmation
- **`ssh_to_instance()`**: Interactive SSH with automatic instance selection
- **`create_key_pair()`**: Generates SSH keys locally and imports public key to AWS
- **`open_console()`**: Opens AWS EC2 console in browser

### Free Tier Enforcement
- **Single Instance Limit**: Prevents creation of multiple t3.micro instances
- **State Monitoring**: Checks pending, running, stopping, and stopped instances
- **Clear Guidance**: Shows existing instances and provides exact delete commands when limit reached

### Security Best Practices
- **Local Key Generation**: Keys generated locally for better security control
- **Proper Permissions**: Sets correct file permissions (0o600 for private, 0o644 for public)
- **Credential Isolation**: Uses ~/.env file for AWS credentials
- **No Hardcoded Secrets**: All sensitive data externalized

## Requirements

- Python 3.6+
- boto3 (AWS SDK for Python)
- python-dotenv (environment variable management)
- awscli (AWS Command Line Interface)
- gh (GitHub CLI) - required for repository management
- ssh-keygen (for key pair generation)

## AWS Permissions Required

Your AWS user needs the following permissions:
- EC2: DescribeInstances, RunInstances, TerminateInstances
- EC2: CreateKeyPair, ImportKeyPair, DescribeKeyPairs
- EC2: CreateSecurityGroup, DescribeSecurityGroups, AuthorizeSecurityGroupIngress
- EC2: DescribeImages

## Troubleshooting

### Missing Dependencies
The script automatically detects and offers to install missing dependencies. If automatic installation fails, manually install:

```bash
pip install boto3 python-dotenv awscli
```

### AWS Credentials
If you get credential errors, ensure your ~/.env file exists and contains:

```
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
```

### SSH Key Issues
- Keys are automatically generated during instance creation
- Use `python aws-free.py key` to manage key pairs via AWS console
- Use `python aws-free.py web` to view instances in AWS console
- Keys are stored locally in ~/.ssh/ for better security
- Ensure ssh-keygen is installed on your system

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Author

Thomas Chung  
Created: August 22, 2025

## License

This project is open source and available under the MIT License.