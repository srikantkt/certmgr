#!/bin/bash
# init_structure.sh - Initialize certificate management directory structure

set -euo pipefail

# Create directory structure
mkdir -p conf ca/{root,intermediate} csr private_keys issued_certificates crl
#mkdir -p src/{python,scripts,tests,testconfig}

# Set secure permissions
chmod 700 private_keys
chmod 755 ca csr issued_certificates crl conf

echo "Directory structure created successfully"
tree -L 2 . || ls -la
