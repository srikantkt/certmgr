# X509 Certificate Management System

A robust, local X.509 certificate management system implementing a two-tier Certificate Authority (CA) hierarchy using OpenSSL. Provides both CLI and REST API interfaces for certificate lifecycle management.

## 🏗️ System Architecture

### Design Overview

```
┌─────────────────────────────────────────────────────────┐
│                 Certificate Management System           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐         ┌──────────────┐              │
│  │   CLI Tool   │◄───────►│  REST API    │              │
│  │  (certmgr)   │         │  (FastAPI)   │              │
│  └──────┬───────┘         └──────┬───────┘              │
│         │                        │                      │
│         └────────┬───────────────┘                      │
│                  │                                      │
│         ┌────────▼────────┐                             │
│         │  Core Manager   │                             │
│         │   (Python)      │                             │
│         └────────┬────────┘                             │
│                  │                                      │
│         ┌────────▼────────┐                             │
│         │    OpenSSL      │                             │
│         │   (Subprocess)  │                             │
│         └─────────────────┘                             │
│                                                         │
└─────────────────────────────────────────────────────────┘

         ┌──────────────────────────────┐
         │   CA Hierarchy               │
         ├──────────────────────────────┤
         │                              │
         │   ┌──────────────────┐       │
         │   │   Root CA        │       │
         │   │  (10 years)      │       │
         │   └────────┬─────────┘       │
         │            │                 │
         │            │ signs           │
         │            ▼                 │
         │   ┌──────────────────┐       │
         │   │ Intermediate CA  │       │
         │   │   (5 years)      │       │
         │   └────────┬─────────┘       │
         │            │                 │
         │            │ issues          │
         │            ▼                 │
         │   ┌──────────────────┐       │
         │   │  End Certificates│       │
         │   │   (1 year)       │       │
         │   └──────────────────┘       │
         │                              │
         └──────────────────────────────┘
```

### Components

1. **Certificate Manager Core** (`src/python/certmgr.py`)
   - Configuration management
   - OpenSSL command orchestration
   - Template rendering
   - File system operations

2. **CLI Interface** (`src/python/certmgr.py`)
   - Command-line operations
   - Interactive prompts
   - Direct programmatic access

3. **REST API** (`src/python/api_server.py`)
   - FastAPI-based web service
   - OpenAPI documentation
   - Swagger UI for testing

4. **Configuration Templates** (`conf/*.template`)
   - OpenSSL configuration files
   - Variable substitution
   - Customizable parameters

## 📁 Directory Structure

```
.
├── conf/                          # Configuration files
│   ├── rootca.cnf.template       # Root CA OpenSSL config template
│   ├── intermediate.cnf.template # Intermediate CA config template
│   ├── csr.cnf.template          # CSR config template
│   ├── rootca.cnf                # Generated Root CA config
│   ├── intermediate.cnf          # Generated Intermediate config
│   └── certmgr_config.json       # System configuration
│
├── ca/                           # Certificate Authority files
│   ├── root/                     # Root CA
│   │   ├── certs/               # Root CA certificate
│   │   ├── crl/                 # Certificate Revocation Lists
│   │   ├── newcerts/            # Newly issued certificates
│   │   ├── private/             # Root CA private key (secure)
│   │   ├── index.txt            # Certificate database
│   │   ├── serial               # Serial number tracking
│   │   └── crlnumber            # CRL number tracking
│   │
│   └── intermediate/             # Intermediate CA
│       ├── certs/               # Intermediate CA certificate
│       ├── crl/                 # Certificate Revocation Lists
│       ├── newcerts/            # Newly issued certificates
│       ├── private/             # Intermediate CA private key (secure)
│       ├── csr/                 # Intermediate CA CSR
│       ├── index.txt            # Certificate database
│       ├── serial               # Serial number tracking
│       └── crlnumber            # CRL number tracking
│
├── csr/                          # Certificate Signing Requests
├── private_keys/                 # End-entity private keys (700 perms)
├── issued_certificates/          # Issued certificates
├── crl/                          # Published Certificate Revocation Lists
│
└── src/
    ├── python/                   # Python source
    │   ├── certmgr.py           # Core manager & CLI
    │   └── api_server.py        # REST API server
    │
    ├── scripts/                  # Utility scripts
    │   └── init_structure.sh    # Directory initialization
    │
    ├── tests/                    # Test suite
    │   ├── test_certmgr.py      # Unit tests
    │   └── test_api.py          # API integration tests
    │
    └── testconfig/               # Test configurations
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **OpenSSL 1.1.1+** (usually pre-installed on Linux/macOS)
- **pip** (Python package manager)

### Installation

1. **Clone/Download the repository**

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

3. **Place configuration templates**

Copy the configuration templates to the `conf/` directory:
- `rootca.cnf.template`
- `intermediate.cnf.template`
- `csr.cnf.template`

4. **Initialize the system**

```bash
# Using CLI
python src/python/certmgr.py init

# Using scripts
bash src/scripts/init_structure.sh
python src/python/certmgr.py init
```

Follow interactive prompts or press Enter to accept defaults:
- Country: US
- State: California
- Organization: Local Development CA
- Root CA validity: 10 years
- Intermediate CA validity: 5 years
- Certificate validity: 1 year

### Basic Workflow

```bash
# 1. Initialize system
python src/python/certmgr.py init

# 2. Create Root CA (requires password for private key)
python src/python/certmgr.py createRootCA

# 3. Create Intermediate CA (requires Root CA password)
python src/python/certmgr.py createInterCA

# 4. Create CSR and private key
python src/python/certmgr.py createCertReq example.local

# 5. Sign certificate (requires Intermediate CA password)
python src/python/certmgr.py signCert csr/example.local_*.csr.pem

# 6. List all certificates
python src/python/certmgr.py listCerts

# 7. Revoke certificate if needed
python src/python/certmgr.py revokeCert issued_certificates/example.local_*.cert.pem

# 8. Update CRL
python src/python/certmgr.py updateCRL
```

## 🔧 CLI Reference

### Commands

#### `init`
Initialize certificate management system
```bash
python src/python/certmgr.py init
```

#### `createRootCA`
Create Root Certificate Authority
```bash
python src/python/certmgr.py createRootCA
```
**Note**: Will prompt for password to encrypt Root CA private key

#### `createInterCA`
Create Intermediate Certificate Authority
```bash
python src/python/certmgr.py createInterCA
```
**Note**: Requires Root CA password

#### `createCertReq <common_name> [--type server|client]`
Create Certificate Signing Request
```bash
python src/python/certmgr.py createCertReq example.local
python src/python/certmgr.py createCertReq user@example.com --type client
```

Prompts for:
- DNS SAN (Subject Alternative Name)
- IP SAN

#### `signCert <csr_file> [--type server|client]`
Sign certificate from CSR
```bash
python src/python/certmgr.py signCert csr/example.local_20240115_120000.csr.pem
```
**Note**: Requires Intermediate CA password

#### `revokeCert <cert_file>`
Revoke a certificate
```bash
python src/python/certmgr.py revokeCert issued_certificates/example.local_20240115_120000.cert.pem
```
**Note**: Automatically updates CRL

#### `updateCRL`
Update Certificate Revocation List
```bash
python src/python/certmgr.py updateCRL
```

#### `listCerts`
List all issued certificates
```bash
python src/python/certmgr.py listCerts
```

Output format:
```
✓ 1000: /CN=example.local (expires: 20250115120000Z)
✗ 1001: /CN=revoked.local (expires: 20250115120000Z)
```

## 🌐 REST API

### Starting the API Server

**Development Mode** (with Swagger UI):
```bash
python src/python/api_server.py
# Or
uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
```

**Production Mode** (Swagger disabled):
```bash
ENV=production uvicorn api_server:app --host 0.0.0.0 --port 8000
```

Access points:
- **API**: `http://localhost:8000`
- **Swagger UI**: `http://localhost:8000/docs` (development only)
- **ReDoc**: `http://localhost:8000/redoc` (development only)
- **OpenAPI JSON**: `http://localhost:8000/openapi.json` (development only)

### API Endpoints

#### Health Check
```
GET /
```
Returns service status and version

#### Initialize System
```
POST /api/v1/init
```
**Request Body**:
```json
{
  "country": "US",
  "state": "California",
  "locality": "San Francisco",
  "organization": "My Company CA",
  "root_ca_cn": "My Root CA",
  "inter_ca_cn": "My Intermediate CA"
}
```

#### Create Root CA
```
POST /api/v1/ca/root
```
⚠️ **Requires interactive password input** - Use CLI for initial setup

#### Create Intermediate CA
```
POST /api/v1/ca/intermediate
```
⚠️ **Requires Root CA password** - Use CLI for initial setup

#### Create CSR
```
POST /api/v1/csr
```
**Request Body**:
```json
{
  "common_name": "example.local",
  "cert_type": "server",
  "san_dns": "*.example.local",
  "san_ip": "192.168.1.100"
}
```

#### Sign Certificate
```
POST /api/v1/certificates/sign
```
**Request Body**:
```json
{
  "csr_filename": "example.local_20240115_120000.csr.pem",
  "cert_type": "server"
}
```
⚠️ **Requires Intermediate CA password**

#### Revoke Certificate
```
POST /api/v1/certificates/revoke
```
**Request Body**:
```json
{
  "cert_filename": "example.local_20240115_120000.cert.pem"
}
```

#### Update CRL
```
POST /api/v1/crl/update
```

#### List Certificates
```
GET /api/v1/certificates/list
```

**Response**:
```json
{
  "certificates": [
    {
      "status": "valid",
      "serial": "1000",
      "subject": "/C=US/ST=California/O=My Org/CN=example.local",
      "expiration": "20250115120000Z",
      "revocation_date": null
    }
  ],
  "count": 1
}
```

#### Download Certificate
```
GET /api/v1/certificates/download/{filename}
```

#### Get Configuration
```
GET /api/v1/config
```

### Example API Usage

**Using curl**:
```bash
# Initialize system
curl -X POST http://localhost:8000/api/v1/init \
  -H "Content-Type: application/json" \
  -d '{
    "country": "US",
    "state": "California",
    "organization": "My CA"
  }'

# Create CSR
curl -X POST http://localhost:8000/api/v1/csr \
  -H "Content-Type: application/json" \
  -d '{
    "common_name": "api.example.com",
    "cert_type": "server",
    "san_dns": "*.api.example.com",
    "san_ip": "10.0.0.10"
  }'

# List certificates
curl http://localhost:8000/api/v1/certificates/list

# Download certificate
curl -O http://localhost:8000/api/v1/certificates/download/api.example.com_20240115_120000.cert.pem
```

**Using Python requests**:
```python
import requests

base_url = "http://localhost:8000"

# Initialize
response = requests.post(f"{base_url}/api/v1/init", json={
    "country": "US",
    "organization": "My CA"
})
print(response.json())

# Create CSR
response = requests.post(f"{base_url}/api/v1/csr", json={
    "common_name": "api.example.com",
    "cert_type": "server"
})
print(response.json())

# List certificates
response = requests.get(f"{base_url}/api/v1/certificates/list")
print(response.json())
```

## 🧪 Testing

### Running Unit Tests

```bash
# Run all tests
pytest src/tests/ -v

# Run specific test file
pytest src/tests/test_certmgr.py -v
pytest src/tests/test_api.py -v

# Run with coverage
pytest src/tests/ --cov=src/python --cov-report=html
```

### Test Categories

**Unit Tests** (`test_certmgr.py`):
- Configuration management
- Template rendering
- Directory initialization
- File permissions
- Serial number handling

**Integration Tests** (`test_api.py`):
- API endpoint validation
- Request/response handling
- Error conditions
- Concurrent requests
- OpenAPI documentation

### Manual Testing

1. **Certificate Creation Flow**:
```bash
# Complete workflow test
./src/scripts/init_structure.sh
python src/python/certmgr.py init
python src/python/certmgr.py createRootCA
python src/python/certmgr.py createInterCA
python src/python/certmgr.py createCertReq test.local
python src/python/certmgr.py signCert csr/test.local_*.csr.pem
```

2. **Certificate Validation**:
```bash
# Verify certificate
openssl x509 -in issued_certificates/test.local_*.cert.pem -text -noout

# Verify certificate chain
openssl verify -CAfile ca/intermediate/certs/ca-chain.cert.pem \
  issued_certificates/test.local_*.cert.pem
```

3. **API Testing via Swagger**:
- Start API server: `python src/python/api_server.py`
- Open browser: `http://localhost:8000/docs`
- Test endpoints interactively

## 🔒 Security Considerations

### Private Key Protection

1. **Directory Permissions**:
   - `private_keys/`: 700 (owner only)
   - `ca/*/private/`: 700 (owner only)

2. **Key Encryption**:
   - Root CA: AES-256 encrypted
   - Intermediate CA: AES-256 encrypted
   - End-entity keys: Unencrypted (configurable)

3. **Password Management**:
   - Use strong passwords for CA keys
   - Store passwords securely (password manager)
   - Never commit passwords to version control

### Best Practices

1. **Certificate Lifecycle**:
   - Regular certificate rotation
   - CRL updates after revocations
   - Monitor certificate expiration

2. **CA Hierarchy**:
   - Keep Root CA offline for production
   - Use Intermediate CA for daily operations
   - Separate CAs for different purposes

3. **Access Control**:
   - Restrict file system access
   - Use API authentication (implement for production)
   - Audit certificate operations

4. **Backup Strategy**:
   - Regularly backup `ca/` directory
   - Secure backup storage
   - Test restoration procedures

## 🛠️ Configuration

### System Configuration File

Location: `conf/certmgr_config.json`

```json
{
  "country": "US",
  "state": "California",
  "locality": "San Francisco",
  "organization": "Local Development CA",
  "root_ca_cn": "Root CA localhost",
  "inter_ca_cn": "Intermediate CA localhost",
  "root_ca_days": 3650,
  "inter_ca_days": 1825,
  "cert_days": 365,
  "fqdn": "localhost"
}
```

### Customizing Validity Periods

Edit `conf/certmgr_config.json`:
```json
{
  "root_ca_days": 7300,    # 20 years
  "inter_ca_days": 3650,   # 10 years
  "cert_days": 730         # 2 years
}
```

### OpenSSL Configuration

Templates support variable substitution:
- `{{ROOT_CA_DIR}}`: Root CA directory path
- `{{INTER_CA_DIR}}`: Intermediate CA directory path
- `{{COUNTRY}}`: Country code
- `{{STATE}}`: State/Province
- `{{ORG}}`: Organization name
- `{{ROOT_CA_CN}}`: Root CA Common Name
- `{{INTER_CA_CN}}`: Intermediate CA Common Name

## 📊 OpenAPI Specification

The REST API provides a complete OpenAPI 3.0 specification accessible at `/openapi.json` (development mode only).

### Key Features

- **Request Validation**: Pydantic models ensure data integrity
- **Response Models**: Typed responses with StatusResponse wrapper
- **Error Handling**: Proper HTTP status codes and error messages
- **Interactive Testing**: Swagger UI for endpoint exploration
- **Documentation**: Auto-generated from code annotations

### Example OpenAPI Output

```yaml
paths:
  /api/v1/csr:
    post:
      summary: Create Certificate Signing Request (CSR)
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CSRRequest'
      responses:
        200:
          description: Successful Response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/StatusResponse'
```

## 🐛 Troubleshooting

### Common Issues

**1. OpenSSL not found**
```
Error: openssl: command not found
```
**Solution**: Install OpenSSL
```bash
# macOS
brew install openssl

# Ubuntu/Debian
sudo apt-get install openssl

# RHEL/CentOS
sudo yum install openssl
```

**2. Permission denied on private_keys/**
```
Error: Permission denied: 'private_keys/example.key.pem'
```
**Solution**: Fix permissions
```bash
chmod 700 private_keys/
chmod 700 ca/*/private/
```

**3. Root CA already exists**
```
⚠ Root CA already exists: ca/root/certs/ca.cert.pem
```
**Solution**: Either:
- Use existing Root CA
- Backup and remove: `mv ca/root ca/root.backup`

**4. Certificate verification failed**
```
Error: unable to get local issuer certificate
```
**Solution**: Verify with correct CA chain
```bash
openssl verify -CAfile ca/intermediate/certs/ca-chain.cert.pem \
  issued_certificates/cert.pem
```

**5. API password prompts**
```
⚠️ This operation requires interactive password input via OpenSSL
```
**Solution**: Use CLI for password-protected operations:
```bash
python src/python/certmgr.py createRootCA
python src/python/certmgr.py createInterCA
```

## 📚 Additional Resources

### OpenSSL Documentation
- [OpenSSL CA Documentation](https://www.openssl.org/docs/man1.1.1/man1/ca.html)
- [OpenSSL x509 Certificate Documentation](https://www.openssl.org/docs/man1.1.1/man1/x509.html)

### X.509 Standards
- [RFC 5280 - X.509 PKI Certificate and CRL Profile](https://tools.ietf.org/html/rfc5280)
- [RFC 6818 - X.509 Updates](https://tools.ietf.org/html/rfc6818)

### FastAPI
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAPI Specification](https://swagger.io/specification/)

## 🤝 Contributing

This is a learning/development tool. Contributions welcome:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/enhancement`)
3. Commit changes (`git commit -am 'Add enhancement'`)
4. Push to branch (`git push origin feature/enhancement`)
5. Open Pull Request

## 📝 License

This project is provided as-is for educational and development purposes.

## ⚠️ Disclaimer

This certificate management system is designed for **local development and testing only**. For production use:

- Implement proper key management (HSM, KMS)
- Add authentication and authorization
- Conduct security audit
- Follow organizational security policies
- Consider commercial CA solutions

---

**Version**: 1.0.0  
**Last Updated**: 2024-01-15
