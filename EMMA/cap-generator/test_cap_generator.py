import os
import pytest
from cap_generator import CAPGenerator, SecureMediaContainer
from lxml import etree

@pytest.fixture
def test_alert_data():
    return {
        'category': 'Safety',
        'event': 'Test Alert',
        'urgency': 'Immediate',
        'severity': 'Extreme',
        'certainty': 'Observed',
        'description': 'Test emergency alert message',
        'attachments': ['test_image.jpg', 'test_video.mp4']
    }

@pytest.fixture
def generator():
    return CAPGenerator()

def test_generate_cap_basic(generator, test_alert_data):
    """Test basic CAP generation without media."""
    cap_file = generator.generate_cap(test_alert_data, include_media=False)
    
    assert os.path.exists(cap_file)
    
    # Parse the generated CAP file
    tree = etree.parse(cap_file)
    root = tree.getroot()
    
    # Verify basic CAP structure
    assert root.tag == "alert"
    assert root.get("xmlns") == "urn:oasis:names:tc:emergency:cap:1.2"
    
    # Verify required elements
    assert root.find("identifier") is not None
    assert root.find("sender").text == "EMMA-System"
    assert root.find("status").text == "Actual"
    assert root.find("msgType").text == "Alert"
    
    # Verify info block
    info = root.find("info")
    assert info.find("category").text == "Safety"
    assert info.find("event").text == "Test Alert"
    assert info.find("description").text == "Test emergency alert message"
    
    # Cleanup
    os.remove(cap_file)

def test_generate_cap_with_media(generator, test_alert_data):
    """Test CAP generation with media attachments."""
    # Create dummy test files
    for attachment in test_alert_data['attachments']:
        with open(attachment, 'w') as f:
            f.write("test content")
    
    try:
        cap_file = generator.generate_cap(test_alert_data, include_media=True)
        
        assert os.path.exists(cap_file)
        
        # Parse the generated CAP file
        tree = etree.parse(cap_file)
        root = tree.getroot()
        
        # Verify mediaLocator is present
        info = root.find("info")
        media_locator = info.find("mediaLocator")
        assert media_locator is not None
        assert "http://http-cdn:3000/alerts/" in media_locator.text
        
        # Verify SMC files were created
        alert_id = root.find("identifier").text
        assert os.path.exists(f"{alert_id}.smc.zip")
        assert os.path.exists(f"{alert_id}.smc.xml")
        
        # Cleanup
        os.remove(cap_file)
        os.remove(f"{alert_id}.smc.zip")
        os.remove(f"{alert_id}.smc.xml")
        
    finally:
        # Cleanup test files
        for attachment in test_alert_data['attachments']:
            if os.path.exists(attachment):
                os.remove(attachment)

def test_secure_media_container():
    """Test SecureMediaContainer functionality."""
    smc = SecureMediaContainer()
    
    # Create test files
    test_files = ['test1.txt', 'test2.txt']
    for file in test_files:
        with open(file, 'w') as f:
            f.write("test content")
    
    try:
        # Create SMC
        zip_path, xml_path = smc.create_smc(test_files, "TEST-ALERT-001")
        
        assert os.path.exists(zip_path)
        assert os.path.exists(xml_path)
        
        # Verify SMC XML structure
        tree = etree.parse(xml_path)
        root = tree.getroot()
        
        assert root.tag == "SecureMediaContainer"
        assert root.get("version") == "1.0"
        assert root.get("alertId") == "TEST-ALERT-001"
        assert root.find("Hash") is not None
        
        # Cleanup
        os.remove(zip_path)
        os.remove(xml_path)
        
    finally:
        # Cleanup test files
        for file in test_files:
            if os.path.exists(file):
                os.remove(file) 