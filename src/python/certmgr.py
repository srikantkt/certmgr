#!/usr/bin/env python3
"""
Certificate Manager - X509 Certificate Authority Management System
Provides CLI interface for CA operations using OpenSSL
"""

import os
import sys
import subprocess
import argparse
import json
import socket
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONF_DIR = BASE_DIR / "conf"
CA_DIR = BASE_DIR / "ca"
CSR_DIR = BASE_DIR / "csr"
PRIVATE_DIR = BASE_DIR / "private_keys"
ISSUED_DIR = BASE_DIR / "issued_certificates"
CRL_DIR = BASE_DIR / "crl"


class CertificateManager:
    """Main certificate management class"""
    
    def __init__(self):
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """Load or create default configuration"""
        config_file = CONF_DIR / "certmgr_config.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Generate default configuration"""
        fqdn = socket.getfqdn() if socket.getfqdn() != 'localhost' else 'localhost'
        return {
            "country": "US",
            "state": "California",
            "locality": "San Francisco",
            "organization": "Local Development CA",
            "root_ca_cn": f"Root CA {fqdn}",
            "inter_ca_cn": f"Intermediate CA {fqdn}",
            "root_ca_days": 3650,  # 10 years
            "inter_ca_days": 1825,  # 5 years
            "cert_days": 365,       # 1 year
            "fqdn": fqdn
        }
    
    def _save_config(self):
        """Save configuration to file"""
        config_file = CONF_DIR / "certmgr_config.json"
        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def _render_template(self, template_file: Path, output_file: Path, variables: Dict):
        """Render configuration template with variables"""
        with open(template_file, 'r') as f:
            content = f.read()
        
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))
        
        with open(output_file, 'w') as f:
            f.write(content)
        
        print(f"✓ Generated: {output_file}")
    
    def _run_openssl(self, args: list, env: Optional[Dict] = None) -> subprocess.CompletedProcess:
        """Execute openssl command"""
        cmd = ["openssl"] + args
        print(f"→ Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, env=env or os.environ)
        if result.returncode != 0:
            print(f"✗ Error: {result.stderr}", file=sys.stderr)
            sys.exit(1)
        return result
    
    def init(self, interactive: bool = True):
        """Initialize certificate management system"""
        print("🔧 Initializing Certificate Management System")
        
        # Create directories
        for dir_path in [CONF_DIR, CA_DIR, CSR_DIR, PRIVATE_DIR, ISSUED_DIR, CRL_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        (CA_DIR / "root").mkdir(exist_ok=True)
        (CA_DIR / "intermediate").mkdir(exist_ok=True)
        
        # Secure private key directory
        PRIVATE_DIR.chmod(0o700)
        
        # Interactive configuration
        if interactive:
            print("\n📝 Configuration (press Enter for defaults)")
            self.config["country"] = input(f"Country [{self.config['country']}]: ") or self.config["country"]
            self.config["state"] = input(f"State [{self.config['state']}]: ") or self.config["state"]
            self.config["locality"] = input(f"Locality [{self.config['locality']}]: ") or self.config["locality"]
            self.config["organization"] = input(f"Organization [{self.config['organization']}]: ") or self.config["organization"]
            self.config["root_ca_cn"] = input(f"Root CA CN [{self.config['root_ca_cn']}]: ") or self.config["root_ca_cn"]
            self.config["inter_ca_cn"] = input(f"Intermediate CA CN [{self.config['inter_ca_cn']}]: ") or self.config["inter_ca_cn"]
        
        self._save_config()
        
        # Generate configuration files from templates
        root_ca_dir = CA_DIR / "root"
        inter_ca_dir = CA_DIR / "intermediate"
        
        root_vars = {
            "ROOT_CA_DIR": str(root_ca_dir.resolve()),
            "ROOT_CA_CN": self.config["root_ca_cn"],
            "COUNTRY": self.config["country"],
            "STATE": self.config["state"],
            "ORG": self.config["organization"]
        }
        
        inter_vars = {
            "INTER_CA_DIR": str(inter_ca_dir.resolve()),
            "INTER_CA_CN": self.config["inter_ca_cn"],
            "COUNTRY": self.config["country"],
            "STATE": self.config["state"],
            "ORG": self.config["organization"]
        }
        
        self._render_template(
            CONF_DIR / "rootca.cnf.template",
            CONF_DIR / "rootca.cnf",
            root_vars
        )
        
        self._render_template(
            CONF_DIR / "intermediate.cnf.template",
            CONF_DIR / "intermediate.cnf",
            inter_vars
        )
        
        # Initialize CA directory structures
        for ca_type, ca_dir in [("root", root_ca_dir), ("intermediate", inter_ca_dir)]:
            (ca_dir / "certs").mkdir(exist_ok=True)
            (ca_dir / "crl").mkdir(exist_ok=True)
            (ca_dir / "newcerts").mkdir(exist_ok=True)
            (ca_dir / "private").mkdir(exist_ok=True)
            (ca_dir / "private").chmod(0o700)
            
            # Create index and serial files
            index_file = ca_dir / "index.txt"
            if not index_file.exists():
                index_file.touch()
            
            serial_file = ca_dir / "serial"
            if not serial_file.exists():
                serial_file.write_text("1000\n")
            
            crlnumber_file = ca_dir / "crlnumber"
            if not crlnumber_file.exists():
                crlnumber_file.write_text("1000\n")
        
        print("\n✓ Initialization complete")
        print(f"  Configuration: {CONF_DIR / 'certmgr_config.json'}")
    
    def create_root_ca(self):
        """Create Root CA certificate and key"""
        print("🔐 Creating Root CA")
        
        root_ca_dir = CA_DIR / "root"
        key_file = root_ca_dir / "private" / "ca.key.pem"
        cert_file = root_ca_dir / "certs" / "ca.cert.pem"
        
        if cert_file.exists():
            print(f"⚠ Root CA already exists: {cert_file}")
            response = input("Overwrite? (yes/no): ")
            if response.lower() != "yes":
                return
        
        # Generate private key
        self._run_openssl([
            "genrsa",
            "-aes256",
            "-out", str(key_file),
            "4096"
        ])
        key_file.chmod(0o400)
        
        # Generate self-signed certificate
        self._run_openssl([
            "req",
            "-config", str(CONF_DIR / "rootca.cnf"),
            "-key", str(key_file),
            "-new", "-x509",
            "-days", str(self.config["root_ca_days"]),
            "-sha256",
            "-extensions", "v3_ca",
            "-out", str(cert_file)
        ])
        
        cert_file.chmod(0o444)
        
        print(f"✓ Root CA created: {cert_file}")
        self._display_cert_info(cert_file)
    
    def create_intermediate_ca(self):
        """Create Intermediate CA signed by Root CA"""
        print("🔐 Creating Intermediate CA")
        
        root_ca_dir = CA_DIR / "root"
        inter_ca_dir = CA_DIR / "intermediate"
        
        key_file = inter_ca_dir / "private" / "intermediate.key.pem"
        csr_file = inter_ca_dir / "csr" / "intermediate.csr.pem"
        cert_file = inter_ca_dir / "certs" / "intermediate.cert.pem"
        chain_file = inter_ca_dir / "certs" / "ca-chain.cert.pem"
        
        if cert_file.exists():
            print(f"⚠ Intermediate CA already exists: {cert_file}")
            response = input("Overwrite? (yes/no): ")
            if response.lower() != "yes":
                return
        
        # Generate private key
        self._run_openssl([
            "genrsa",
            "-aes256",
            "-out", str(key_file),
            "4096"
        ])
        key_file.chmod(0o400)
        
        # Generate CSR
        (inter_ca_dir / "csr").mkdir(exist_ok=True)
        self._run_openssl([
            "req",
            "-config", str(CONF_DIR / "intermediate.cnf"),
            "-new", "-sha256",
            "-key", str(key_file),
            "-out", str(csr_file)
        ])
        
        # Sign with Root CA
        self._run_openssl([
            "ca",
            "-config", str(CONF_DIR / "rootca.cnf"),
            "-extensions", "v3_intermediate_ca",
            "-days", str(self.config["inter_ca_days"]),
            "-notext", "-md", "sha256",
            "-in", str(csr_file),
            "-out", str(cert_file),
            "-batch"
        ])
        
        cert_file.chmod(0o444)
        
        # Create certificate chain
        with open(chain_file, 'w') as chain:
            with open(cert_file, 'r') as inter:
                chain.write(inter.read())
            with open(root_ca_dir / "certs" / "ca.cert.pem", 'r') as root:
                chain.write(root.read())
        
        print(f"✓ Intermediate CA created: {cert_file}")
        print(f"✓ Certificate chain: {chain_file}")
        self._display_cert_info(cert_file)
    
    def create_csr(self, common_name: str, cert_type: str = "server"):
        """Create Certificate Signing Request"""
        print(f"📝 Creating CSR for: {common_name}")
        
        # Sanitize filename
        safe_name = common_name.replace("*", "wildcard").replace("/", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        key_file = PRIVATE_DIR / f"{safe_name}_{timestamp}.key.pem"
        csr_file = CSR_DIR / f"{safe_name}_{timestamp}.csr.pem"
        config_file = CONF_DIR / f"csr_{safe_name}_{timestamp}.cnf"
        
        # Get SANs
        san_dns = input(f"DNS SAN [{common_name}]: ") or common_name
        san_ip = input("IP SAN [127.0.0.1]: ") or "127.0.0.1"
        
        # Render CSR config
        csr_vars = {
            "CERT_CN": common_name,
            "COUNTRY": self.config["country"],
            "STATE": self.config["state"],
            "ORG": self.config["organization"],
            "SAN_DNS": san_dns,
            "SAN_IP": san_ip
        }
        
        self._render_template(
            CONF_DIR / "csr.cnf.template",
            config_file,
            csr_vars
        )
        
        # Generate private key
        self._run_openssl([
            "genrsa",
            "-out", str(key_file),
            "2048"
        ])
        key_file.chmod(0o400)
        
        # Generate CSR
        self._run_openssl([
            "req",
            "-config", str(config_file),
            "-key", str(key_file),
            "-new", "-sha256",
            "-out", str(csr_file)
        ])
        
        print(f"✓ CSR created: {csr_file}")
        print(f"✓ Private key: {key_file}")
        
        return str(csr_file), str(key_file)
    
    def sign_certificate(self, csr_file: str, cert_type: str = "server"):
        """Sign certificate using Intermediate CA"""
        print(f"✍ Signing certificate: {csr_file}")
        
        csr_path = Path(csr_file)
        if not csr_path.exists():
            print(f"✗ CSR not found: {csr_file}", file=sys.stderr)
            sys.exit(1)
        
        # Generate output cert filename
        cert_name = csr_path.stem.replace(".csr", "")
        cert_file = ISSUED_DIR / f"{cert_name}.cert.pem"
        
        # Choose extension based on cert type
        extension = "server_cert" if cert_type == "server" else "usr_cert"
        
        # Sign certificate
        self._run_openssl([
            "ca",
            "-config", str(CONF_DIR / "intermediate.cnf"),
            "-extensions", extension,
            "-days", str(self.config["cert_days"]),
            "-notext", "-md", "sha256",
            "-in", str(csr_path),
            "-out", str(cert_file),
            "-batch"
        ])
        
        cert_file.chmod(0o444)
        
        print(f"✓ Certificate issued: {cert_file}")
        self._display_cert_info(cert_file)
        
        return str(cert_file)
    
    def revoke_certificate(self, cert_file: str):
        """Revoke a certificate"""
        print(f"🚫 Revoking certificate: {cert_file}")
        
        cert_path = Path(cert_file)
        if not cert_path.exists():
            print(f"✗ Certificate not found: {cert_file}", file=sys.stderr)
            sys.exit(1)
        
        # Revoke using intermediate CA
        self._run_openssl([
            "ca",
            "-config", str(CONF_DIR / "intermediate.cnf"),
            "-revoke", str(cert_path)
        ])
        
        print(f"✓ Certificate revoked: {cert_file}")
        self.update_crl()
    
    def update_crl(self):
        """Update Certificate Revocation List"""
        print("📋 Updating CRL")
        
        inter_ca_dir = CA_DIR / "intermediate"
        crl_file = CRL_DIR / "intermediate.crl.pem"
        
        # Generate CRL
        self._run_openssl([
            "ca",
            "-config", str(CONF_DIR / "intermediate.cnf"),
            "-gencrl",
            "-out", str(crl_file)
        ])
        
        print(f"✓ CRL updated: {crl_file}")
        
        # Display CRL info
        result = self._run_openssl([
            "crl",
            "-in", str(crl_file),
            "-noout",
            "-text"
        ])
        print(result.stdout)
    
    def _display_cert_info(self, cert_file: Path):
        """Display certificate information"""
        result = self._run_openssl([
            "x509",
            "-in", str(cert_file),
            "-noout",
            "-text",
            "-certopt", "no_pubkey,no_sigdump"
        ])
        print("\n" + "=" * 60)
        print(result.stdout)
        print("=" * 60 + "\n")
    
    def list_certificates(self):
        """List all issued certificates"""
        print("📜 Issued Certificates")
        inter_ca_dir = CA_DIR / "intermediate"
        index_file = inter_ca_dir / "index.txt"
        
        if not index_file.exists():
            print("No certificates issued yet")
            return
        
        with open(index_file, 'r') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 6:
                    status, exp_date, rev_date, serial, _, subject = parts
                    status_icon = "✓" if status == "V" else "✗"
                    print(f"{status_icon} {serial}: {subject} (expires: {exp_date})")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="X509 Certificate Authority Management System",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Init command
    subparsers.add_parser('init', help='Initialize certificate management system')
    
    # Create Root CA
    subparsers.add_parser('createRootCA', help='Create Root CA')
    
    # Create Intermediate CA
    subparsers.add_parser('createInterCA', help='Create Intermediate CA')
    
    # Create CSR
    csr_parser = subparsers.add_parser('createCertReq', help='Create Certificate Signing Request')
    csr_parser.add_argument('common_name', help='Common Name for certificate')
    csr_parser.add_argument('--type', choices=['server', 'client'], default='server', help='Certificate type')
    
    # Sign certificate
    sign_parser = subparsers.add_parser('signCert', help='Sign certificate from CSR')
    sign_parser.add_argument('csr_file', help='Path to CSR file')
    sign_parser.add_argument('--type', choices=['server', 'client'], default='server', help='Certificate type')
    
    # Revoke certificate
    revoke_parser = subparsers.add_parser('revokeCert', help='Revoke a certificate')
    revoke_parser.add_argument('cert_file', help='Path to certificate file')
    
    # Update CRL
    subparsers.add_parser('updateCRL', help='Update Certificate Revocation List')
    
    # List certificates
    subparsers.add_parser('listCerts', help='List all issued certificates')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize manager
    mgr = CertificateManager()
    
    # Execute command
    if args.command == 'init':
        mgr.init()
    elif args.command == 'createRootCA':
        mgr.create_root_ca()
    elif args.command == 'createInterCA':
        mgr.create_intermediate_ca()
    elif args.command == 'createCertReq':
        mgr.create_csr(args.common_name, args.type)
    elif args.command == 'signCert':
        mgr.sign_certificate(args.csr_file, args.type)
    elif args.command == 'revokeCert':
        mgr.revoke_certificate(args.cert_file)
    elif args.command == 'updateCRL':
        mgr.update_crl()
    elif args.command == 'listCerts':
        mgr.list_certificates()


if __name__ == "__main__":
    main()
