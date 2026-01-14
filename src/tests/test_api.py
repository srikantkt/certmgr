#!/usr/bin/env python3
"""
Integration tests for Certificate Management REST API
Tests API endpoints and request/response handling
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path
import tempfile
import shutil
import os

# Setup path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))
from api_server import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for testing"""
    temp_dir = tempfile.mkdtemp()
    original_dir = os.getcwd()
    os.chdir(temp_dir)
    
    # Create directory structure
    for dir_name in ['conf', 'ca', 'csr', 'private_keys', 'issued_certificates', 'crl']:
        Path(dir_name).mkdir(exist_ok=True)
    
    Path('ca/root').mkdir(parents=True, exist_ok=True)
    Path('ca/intermediate').mkdir(parents=True, exist_ok=True)
    
    # Copy templates
    template_dir = Path(original_dir) / "conf"
    if template_dir.exists():
        for template in ['rootca.cnf.template', 'intermediate.cnf.template', 'csr.cnf.template']:
            src = template_dir / template
            if src.exists():
                shutil.copy(src, Path('conf') / template)
    
    yield temp_dir
    
    # Cleanup
    os.chdir(original_dir)
    shutil.rmtree(temp_dir)


def test_root_endpoint(client):
    """Test root health check endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    
    data = response.json()
    assert data["service"] == "X509 Certificate Management API"
    assert data["status"] == "operational"


def test_get_config(client):
    """Test configuration retrieval"""
    response = client.get("/api/v1/config")
    assert response.status_code == 200
    
    config = response.json()
    assert "country" in config
    assert "state" in config
    assert "organization" in config


def test_init_endpoint(client, temp_workspace):
    """Test initialization endpoint"""
    init_data = {
        "country": "US",
        "state": "California",
        "organization": "Test CA"
    }
    
    response = client.post("/api/v1/init", json=init_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "initialized successfully" in data["message"].lower()


def test_list_certificates_empty(client, temp_workspace):
    """Test listing certificates when none exist"""
    # Initialize first
    client.post("/api/v1/init", json={})
    
    response = client.get("/api/v1/certificates/list")
    assert response.status_code == 200
    
    data = response.json()
    assert "certificates" in data
    assert len(data["certificates"]) == 0


def test_csr_request_validation(client):
    """Test CSR request validation"""
    # Missing required field
    invalid_data = {
        "cert_type": "server"
    }
    
    response = client.post("/api/v1/csr", json=invalid_data)
    assert response.status_code == 422  # Validation error


def test_sign_request_validation(client):
    """Test sign request validation"""
    # Missing required field
    invalid_data = {
        "cert_type": "server"
    }
    
    response = client.post("/api/v1/certificates/sign", json=invalid_data)
    assert response.status_code == 422  # Validation error


def test_revoke_request_validation(client):
    """Test revoke request validation"""
    # Missing required field
    invalid_data = {}
    
    response = client.post("/api/v1/certificates/revoke", json=invalid_data)
    assert response.status_code == 422  # Validation error


def test_download_nonexistent_file(client, temp_workspace):
    """Test downloading a file that doesn't exist"""
    response = client.get("/api/v1/certificates/download/nonexistent.pem")
    assert response.status_code == 404


def test_openapi_docs_in_development(client):
    """Test OpenAPI documentation is available in development"""
    # Set environment to development
    os.environ["ENV"] = "development"
    
    response = client.get("/docs")
    # Should not be None in development
    assert response.status_code in [200, 307]  # 200 for docs, 307 for redirect


def test_api_response_structure(client):
    """Test API response follows expected structure"""
    response = client.get("/api/v1/config")
    assert response.status_code == 200
    
    # All successful responses should be JSON
    assert response.headers["content-type"] == "application/json"


def test_init_with_custom_values(client, temp_workspace):
    """Test initialization with custom configuration values"""
    custom_config = {
        "country": "GB",
        "state": "England",
        "locality": "London",
        "organization": "Custom Test CA",
        "root_ca_cn": "Custom Root CA",
        "inter_ca_cn": "Custom Intermediate CA"
    }
    
    response = client.post("/api/v1/init", json=custom_config)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    
    # Verify config was updated
    config_response = client.get("/api/v1/config")
    config = config_response.json()
    
    assert config["country"] == "GB"
    assert config["organization"] == "Custom Test CA"


def test_concurrent_requests(client):
    """Test API can handle concurrent requests"""
    import concurrent.futures
    
    def make_request():
        return client.get("/api/v1/config")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request) for _ in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    # All requests should succeed
    assert all(r.status_code == 200 for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
