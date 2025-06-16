import os
import zipfile
import hashlib
from datetime import datetime
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from lxml import etree
import json

class SecureMediaContainer:
    def __init__(self, private_key_path=None):
        self.private_key = None
        if private_key_path and os.path.exists(private_key_path):
            with open(private_key_path, 'rb') as key_file:
                self.private_key = serialization.load_pem_private_key(
                    key_file.read(),
                    password=None
                )

    def create_smc(self, attachments, alert_id):
        """Create a Secure Media Container with signed attachments."""
        # Create temporary directory for files
        temp_dir = f"temp_{alert_id}"
        os.makedirs(temp_dir, exist_ok=True)

        # Add attachments to zip
        zip_path = f"{alert_id}.smc.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for attachment in attachments:
                zipf.write(attachment, os.path.basename(attachment))

        # Calculate hash of zip file
        with open(zip_path, 'rb') as f:
            zip_hash = hashlib.sha256(f.read()).hexdigest()

        # Sign the hash if private key is available
        signature = None
        if self.private_key:
            signature = self.private_key.sign(
                zip_hash.encode(),
                ec.ECDSA(hashes.SHA256())
            )

        # Create SMC XML
        smc_xml = etree.Element("SecureMediaContainer")
        smc_xml.set("version", "1.0")
        smc_xml.set("alertId", alert_id)
        
        hash_elem = etree.SubElement(smc_xml, "Hash")
        hash_elem.text = zip_hash
        
        if signature:
            sig_elem = etree.SubElement(smc_xml, "Signature")
            sig_elem.text = signature.hex()

        # Write SMC XML
        with open(f"{alert_id}.smc.xml", 'wb') as f:
            f.write(etree.tostring(smc_xml, pretty_print=True))

        # Cleanup
        os.rmdir(temp_dir)
        return zip_path, f"{alert_id}.smc.xml"

class CAPGenerator:
    def __init__(self, smc=None):
        self.smc = smc or SecureMediaContainer()

    def generate_cap(self, alert_data, include_media=False):
        """Generate a CAP alert with optional media attachments."""
        # Create basic CAP structure
        cap = etree.Element("alert")
        cap.set("xmlns", "urn:oasis:names:tc:emergency:cap:1.2")
        
        # Add required CAP elements
        identifier = etree.SubElement(cap, "identifier")
        identifier.text = f"EMMA-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        sender = etree.SubElement(cap, "sender")
        sender.text = "EMMA-System"
        
        sent = etree.SubElement(cap, "sent")
        sent.text = datetime.now().isoformat()
        
        status = etree.SubElement(cap, "status")
        status.text = "Actual"
        
        msg_type = etree.SubElement(cap, "msgType")
        msg_type.text = "Alert"
        
        scope = etree.SubElement(cap, "scope")
        scope.text = "Public"
        
        # Add info block
        info = etree.SubElement(cap, "info")
        
        category = etree.SubElement(info, "category")
        category.text = alert_data.get('category', 'Other')
        
        event = etree.SubElement(info, "event")
        event.text = alert_data.get('event', 'Emergency Alert')
        
        urgency = etree.SubElement(info, "urgency")
        urgency.text = alert_data.get('urgency', 'Immediate')
        
        severity = etree.SubElement(info, "severity")
        severity.text = alert_data.get('severity', 'Extreme')
        
        certainty = etree.SubElement(info, "certainty")
        certainty.text = alert_data.get('certainty', 'Observed')
        
        # Add description
        description = etree.SubElement(info, "description")
        description.text = alert_data.get('description', 'Emergency Alert Message')

        # If media is included, create SMC and add mediaLocator
        if include_media and alert_data.get('attachments'):
            zip_path, smc_xml = self.smc.create_smc(
                alert_data['attachments'],
                identifier.text
            )
            
            # Add mediaLocator to CAP
            media_locator = etree.SubElement(info, "mediaLocator")
            media_locator.text = f"http://http-cdn:3000/alerts/{os.path.basename(zip_path)}"

        # Write CAP XML
        output_file = f"{identifier.text}.xml"
        with open(output_file, 'wb') as f:
            f.write(etree.tostring(cap, pretty_print=True))

        return output_file

def main():
    # Example usage
    generator = CAPGenerator()
    
    # Example alert data
    alert_data = {
        'category': 'Safety',
        'event': 'Test Alert',
        'urgency': 'Immediate',
        'severity': 'Extreme',
        'certainty': 'Observed',
        'description': 'This is a test emergency alert message.',
        'attachments': ['test_image.jpg', 'test_video.mp4']
    }
    
    # Generate CAP with media
    cap_file = generator.generate_cap(alert_data, include_media=True)
    print(f"Generated CAP file: {cap_file}")

if __name__ == "__main__":
    main() 