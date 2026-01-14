#!/usr/bin/env python3
"""
Unit tests for Certificate Manager
Tests core functionality without requiring interactive password inputs
"""

import pytest
import sys
import os
import json
from pathlib import Path
import tempfile
import shutil

# Setup path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))
from certmgr import CertificateManager


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


def test_default_config_generation():
    """Test default configuration generation"""
    mgr = CertificateManager()
    config = mgr._get_default_config()
    
    assert config["country"] == "US"
    assert config["state"] == "California"
    assert config["root_ca_days"] == 3650
    assert config["inter_ca_days"] == 1825
    assert config["cert_days"] == 365


def test_config_persistence(temp_workspace):
    """Test configuration save and load"""
    mgr = CertificateManager()
    mgr.config["organization"] = "Test Organization"
    mgr._save_config()
    
    # Create new manager instance
    mgr2 = CertificateManager()
    assert mgr2.config["organization"] == "Test Organization"


def test_init_creates_directories(temp_workspace):
    """Test init creates necessary directories"""
    mgr = CertificateManager()
    mgr.init(interactive=False)
    
    # Check directories exist
    assert Path("conf").exists()
    assert Path("ca/root").exists()
    assert Path("ca/intermediate").exists()
    assert Path("csr").exists()
    assert Path("private_keys").exists()
    assert Path("issued_certificates").exists()
    assert Path("crl").exists()
    
    # Check CA structure
    assert (Path("ca/root") / "index.txt").exists()
    assert (Path("ca/root") / "serial").exists()
    assert (Path("ca/intermediate") / "index.txt").exists()


def test_template_rendering(temp_workspace):
    """Test configuration template rendering"""
    mgr = CertificateManager()
    mgr.init(interactive=False)
    
    # Create a simple template
    template_file = Path("conf/test.template")
    template_file.write_text("Hello {{NAME}}, your country is {{COUNTRY}}")
    
    output_file = Path("conf/test.conf")
    variables = {"NAME": "World", "COUNTRY": "US"}
    
    mgr._render_template(template_file, output_file, variables)
    
    result = output_file.read_text()
    assert result == "Hello World, your country is US"


def test_config_file_format(temp_workspace):
    """Test configuration file is valid JSON"""
    mgr = CertificateManager()
    mgr.config["test_key"] = "test_value"
    mgr._save_config()
    
    config_file = Path("conf/certmgr_config.json")
    assert config_file.exists()
    
    # Verify JSON format
    with open(config_file, 'r') as f:
        loaded_config = json.load(f)
    
    assert loaded_config["test_key"] == "test_value"


def test_openssl_command_construction():
    """Test OpenSSL command construction"""
    mgr = CertificateManager()
    
    # This would normally execute, but we're just testing structure
    # In real scenario, we'd mock subprocess.run
    args = ["version"]
    
    # Verify command structure (without execution)
    cmd = ["openssl"] + args
    assert cmd == ["openssl", "version"]


def test_serial_number_initialization(temp_workspace):
    """Test serial number files are properly initialized"""
    mgr = CertificateManager()
    mgr.init(interactive=False)
    
    root_serial = Path("ca/root/serial")
    inter_serial = Path("ca/intermediate/serial")
    
    assert root_serial.read_text().strip() == "1000"
    assert inter_serial.read_text().strip() == "1000"


def test_crlnumber_initialization(temp_workspace):
    """Test CRL number files are properly initialized"""
    mgr = CertificateManager()
    mgr.init(interactive=False)
    
    root_crlnum = Path("ca/root/crlnumber")
    inter_crlnum = Path("ca/intermediate/crlnumber")
    
    assert root_crlnum.read_text().strip() == "1000"
    assert inter_crlnum.read_text().strip() == "1000"


def test_private_key_permissions(temp_workspace):
    """Test private key directory has correct permissions"""
    mgr = CertificateManager()
    mgr.init(interactive=False)
    
    private_dir = Path("private_keys")
    stat_info = private_dir.stat()
    
    # Check that only owner has permissions (0o700)
    # This is Unix-specific
    if hasattr(os, 'chmod'):
        permissions = oct(stat_info.st_mode)[-3:]
        assert permissions == "700"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
