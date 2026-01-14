#!/usr/bin/env python3
"""
Certificate Management REST API
FastAPI server for certificate operations with OpenAPI documentation
"""

from fastapi import FastAPI, HTTPException, File, UploadFile, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import sys
import os
from pathlib import Path

# Add src/python to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from certmgr import CertificateManager

# Environment detection
ENVIRONMENT = os.getenv("ENV", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

# FastAPI app
app = FastAPI(
    title="X509 Certificate Management API",
    description="REST API for managing X.509 certificates with a local CA hierarchy",
    version="1.0.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json"
)

# Initialize certificate manager
cert_mgr = CertificateManager()


# Pydantic models
class InitRequest(BaseModel):
    """Initialization request parameters"""
    country: Optional[str] = Field("US", description="Two-letter country code")
    state: Optional[str] = Field("California", description="State or province")
    locality: Optional[str] = Field("San Francisco", description="City or locality")
    organization: Optional[str] = Field("Local Development CA", description="Organization name")
    root_ca_cn: Optional[str] = Field(None, description="Root CA Common Name")
    inter_ca_cn: Optional[str] = Field(None, description="Intermediate CA Common Name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "country": "US",
                "state": "California",
                "organization": "My Company CA"
            }
        }


class CSRRequest(BaseModel):
    """Certificate Signing Request parameters"""
    common_name: str = Field(..., description="Common Name (CN) for certificate")
    cert_type: str = Field("server", description="Certificate type: server or client")
    san_dns: Optional[str] = Field(None, description="Subject Alternative Name - DNS")
    san_ip: Optional[str] = Field("127.0.0.1", description="Subject Alternative Name - IP")
    
    class Config:
        json_schema_extra = {
            "example": {
                "common_name": "example.local",
                "cert_type": "server",
                "san_dns": "*.example.local",
                "san_ip": "192.168.1.100"
            }
        }


class SignRequest(BaseModel):
    """Certificate signing request"""
    csr_filename: str = Field(..., description="CSR filename in csr/ directory")
    cert_type: str = Field("server", description="Certificate type: server or client")
    
    class Config:
        json_schema_extra = {
            "example": {
                "csr_filename": "example.local_20240115_120000.csr.pem",
                "cert_type": "server"
            }
        }


class RevokeRequest(BaseModel):
    """Certificate revocation request"""
    cert_filename: str = Field(..., description="Certificate filename in issued_certificates/ directory")
    
    class Config:
        json_schema_extra = {
            "example": {
                "cert_filename": "example.local_20240115_120000.cert.pem"
            }
        }


class StatusResponse(BaseModel):
    """Generic status response"""
    success: bool
    message: str
    data: Optional[dict] = None


# API Endpoints

@app.get("/", tags=["Status"])
async def root():
    """Health check endpoint"""
    return {
        "service": "X509 Certificate Management API",
        "version": "1.0.0",
        "status": "operational",
        "environment": ENVIRONMENT
    }


@app.post("/api/v1/init", response_model=StatusResponse, tags=["Setup"])
async def initialize_ca(request: InitRequest = Body(...)):
    """
    Initialize the certificate management system
    
    Creates directory structure, generates configuration files,
    and prepares the CA environment for operation.
    """
    try:
        # Update config with provided values
        if request.country:
            cert_mgr.config["country"] = request.country
        if request.state:
            cert_mgr.config["state"] = request.state
        if request.locality:
            cert_mgr.config["locality"] = request.locality
        if request.organization:
            cert_mgr.config["organization"] = request.organization
        if request.root_ca_cn:
            cert_mgr.config["root_ca_cn"] = request.root_ca_cn
        if request.inter_ca_cn:
            cert_mgr.config["inter_ca_cn"] = request.inter_ca_cn
        
        # Run init without interactive prompts
        cert_mgr.init(interactive=False)
        
        return StatusResponse(
            success=True,
            message="Certificate management system initialized successfully",
            data={"config": cert_mgr.config}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/ca/root", response_model=StatusResponse, tags=["Certificate Authority"])
async def create_root_ca():
    """
    Create Root Certificate Authority
    
    Generates a self-signed Root CA certificate with a 10-year validity.
    This should be the first CA operation after initialization.
    
    ⚠️ This operation requires interactive password input via OpenSSL
    """
    try:
        cert_mgr.create_root_ca()
        
        root_ca_cert = cert_mgr.CA_DIR / "root" / "certs" / "ca.cert.pem"
        
        return StatusResponse(
            success=True,
            message="Root CA created successfully",
            data={
                "certificate": str(root_ca_cert),
                "validity_days": cert_mgr.config["root_ca_days"]
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/ca/intermediate", response_model=StatusResponse, tags=["Certificate Authority"])
async def create_intermediate_ca():
    """
    Create Intermediate Certificate Authority
    
    Generates an Intermediate CA signed by the Root CA with 5-year validity.
    Root CA must exist before creating Intermediate CA.
    
    ⚠️ This operation requires interactive password input via OpenSSL
    """
    try:
        cert_mgr.create_intermediate_ca()
        
        inter_ca_cert = cert_mgr.CA_DIR / "intermediate" / "certs" / "intermediate.cert.pem"
        chain_cert = cert_mgr.CA_DIR / "intermediate" / "certs" / "ca-chain.cert.pem"
        
        return StatusResponse(
            success=True,
            message="Intermediate CA created successfully",
            data={
                "certificate": str(inter_ca_cert),
                "chain": str(chain_cert),
                "validity_days": cert_mgr.config["inter_ca_days"]
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/csr", response_model=StatusResponse, tags=["Certificates"])
async def create_csr(request: CSRRequest):
    """
    Create Certificate Signing Request (CSR)
    
    Generates a private key and CSR for a new certificate.
    Supports both server and client certificate types with SANs.
    """
    try:
        # Mock interactive inputs for CSR creation
        import io
        import sys
        
        # Temporarily replace stdin for non-interactive operation
        old_stdin = sys.stdin
        sys.stdin = io.StringIO(f"{request.san_dns or request.common_name}\n{request.san_ip}\n")
        
        csr_file, key_file = cert_mgr.create_csr(request.common_name, request.cert_type)
        
        sys.stdin = old_stdin
        
        return StatusResponse(
            success=True,
            message="CSR created successfully",
            data={
                "csr_file": csr_file,
                "private_key": key_file,
                "common_name": request.common_name,
                "type": request.cert_type
            }
        )
    except Exception as e:
        sys.stdin = old_stdin  # Restore stdin
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/certificates/sign", response_model=StatusResponse, tags=["Certificates"])
async def sign_certificate(request: SignRequest):
    """
    Sign certificate from CSR
    
    Uses Intermediate CA to sign a CSR and issue a certificate
    with 1-year validity (configurable).
    
    ⚠️ This operation requires interactive password input via OpenSSL
    """
    try:
        csr_path = cert_mgr.CSR_DIR / request.csr_filename
        if not csr_path.exists():
            raise HTTPException(status_code=404, detail=f"CSR not found: {request.csr_filename}")
        
        cert_file = cert_mgr.sign_certificate(str(csr_path), request.cert_type)
        
        return StatusResponse(
            success=True,
            message="Certificate signed successfully",
            data={
                "certificate": cert_file,
                "validity_days": cert_mgr.config["cert_days"]
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/certificates/revoke", response_model=StatusResponse, tags=["Certificates"])
async def revoke_certificate(request: RevokeRequest):
    """
    Revoke a certificate
    
    Revokes a certificate and updates the Certificate Revocation List (CRL).
    
    ⚠️ This operation requires interactive password input via OpenSSL
    """
    try:
        cert_path = cert_mgr.ISSUED_DIR / request.cert_filename
        if not cert_path.exists():
            raise HTTPException(status_code=404, detail=f"Certificate not found: {request.cert_filename}")
        
        cert_mgr.revoke_certificate(str(cert_path))
        
        return StatusResponse(
            success=True,
            message="Certificate revoked successfully",
            data={"certificate": str(cert_path)}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/crl/update", response_model=StatusResponse, tags=["CRL"])
async def update_crl():
    """
    Update Certificate Revocation List
    
    Generates an updated CRL containing all revoked certificates.
    CRL should be published to a location accessible by certificate validators.
    
    ⚠️ This operation requires interactive password input via OpenSSL
    """
    try:
        cert_mgr.update_crl()
        
        crl_file = cert_mgr.CRL_DIR / "intermediate.crl.pem"
        
        return StatusResponse(
            success=True,
            message="CRL updated successfully",
            data={"crl_file": str(crl_file)}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/certificates/list", tags=["Certificates"])
async def list_certificates():
    """
    List all issued certificates
    
    Returns a list of all certificates issued by the Intermediate CA,
    including status (valid/revoked), serial number, subject, and expiration.
    """
    try:
        inter_ca_dir = cert_mgr.CA_DIR / "intermediate"
        index_file = inter_ca_dir / "index.txt"
        
        if not index_file.exists():
            return {"certificates": []}
        
        certificates = []
        with open(index_file, 'r') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 6:
                    status, exp_date, rev_date, serial, _, subject = parts
                    certificates.append({
                        "status": "valid" if status == "V" else "revoked",
                        "serial": serial,
                        "subject": subject,
                        "expiration": exp_date,
                        "revocation_date": rev_date if rev_date else None
                    })
        
        return {"certificates": certificates, "count": len(certificates)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/certificates/download/{filename}", tags=["Certificates"])
async def download_certificate(filename: str):
    """
    Download a certificate file
    
    Downloads issued certificate, CSR, or CRL files.
    Specify the filename from the appropriate directory.
    """
    # Check in multiple locations
    for base_dir in [cert_mgr.ISSUED_DIR, cert_mgr.CSR_DIR, cert_mgr.CRL_DIR]:
        file_path = base_dir / filename
        if file_path.exists():
            return FileResponse(
                path=str(file_path),
                filename=filename,
                media_type="application/x-pem-file"
            )
    
    raise HTTPException(status_code=404, detail=f"File not found: {filename}")


@app.get("/api/v1/config", tags=["Configuration"])
async def get_config():
    """
    Get current configuration
    
    Returns the active certificate management configuration.
    """
    return cert_mgr.config


if __name__ == "__main__":
    import uvicorn
    
    # Run server
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True if not IS_PRODUCTION else False
    )
