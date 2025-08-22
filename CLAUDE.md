# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains a comprehensive Python CLI tool for managing AWS EC2 free tier instances. The main script is `aws-free.py` which provides full lifecycle management including creation, listing, deletion, SSH access, and console opening for t2.micro instances.

## Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Create ~/.env file with AWS credentials (note: uses home directory)
echo "AWS_ACCESS_KEY_ID=your_access_key_id" > ~/.env
echo "AWS_SECRET_ACCESS_KEY=your_secret_access_key" >> ~/.env

# Or create ~/.env file manually with:
# AWS_ACCESS_KEY_ID=AKIA...
# AWS_SECRET_ACCESS_KEY=wJalr...
```

## Available Commands

```bash
# Show all available commands (default behavior)
python aws-free.py

# Instance management
python aws-free.py create [key_name] [region]    # Create new instance
python aws-free.py list [region]                 # List all instances
python aws-free.py delete <instance_id> [region] # Delete instance
python aws-free.py ssh [instance_id] [region]    # SSH to instance
python aws-free.py web [region]                  # Open AWS web console in browser

# Examples
python aws-free.py create my-key us-east-1       # Create with key pair in specific region
python aws-free.py ssh                           # Interactive SSH - lists running instances
python aws-free.py delete i-1234567890           # Delete specific instance
python aws-free.py web                           # Open AWS EC2 console
```

## Architecture & Key Functions

### Command Flow
- **Default behavior**: Shows help/command list (changed from auto-creating instance)
- **Command routing**: `main()` function handles all command parsing and routing
- **Error handling**: Comprehensive AWS error handling with user-friendly messages

### Core Functions
- **`check_dependencies()`**: Auto-installs missing packages (boto3, python-dotenv, awscli) and checks for GitHub CLI
- **`check_aws_credentials()`**: Validates ~/.env file and provides setup instructions
- **`launch_instance()`**: Creates t3.micro instances with free tier limit enforcement (max 1 instance)
- **`list_instances()`**: Shows formatted table with instance details and terminated instance explanations
- **`delete_instance()`**: Safe deletion with confirmation and detailed instance info
- **`ssh_to_instance()`**: Interactive SSH with automatic instance selection using local keys
- **`create_key_pair()`**: Generates SSH key pairs locally and imports public key to AWS
- **`create_security_group()`**: Creates/reuses security groups with SSH access
- **`get_latest_ubuntu_ami()`**: Finds latest Ubuntu Server 24.04 LTS AMI
- **`open_console()`**: Opens AWS EC2 console in browser for specified region

### Free Tier Enforcement
- **Single instance limit**: Prevents creation of multiple t3.micro instances
- **State checking**: Monitors pending, running, stopping, and stopped instances
- **Clear guidance**: Shows existing instances and provides exact delete commands when limit reached

### Key Pair Management
- **Local generation**: Creates SSH key pairs locally using ssh-keygen for better security
- **AWS import**: Imports only public key to AWS, keeping private key secure locally
- **Proper permissions**: Sets secure permissions (0o600 for private, 0o644 for public)
- **RSA 2048-bit**: Uses standard RSA keys with 2048-bit encryption for compatibility

### User Experience Features
- **Interactive prompts**: Default "Y" responses for common actions (dependency install, key creation, SSH execution)
- **Informative messaging**: Explains AWS concepts like "terminated" state and cleanup timing
- **Backward compatibility**: Supports old command format while encouraging new explicit commands
- **Consistent terminology**: Uses "web" for AWS console access (accepts legacy "console" and "dashboard" commands)