import os
import zipfile
import base64
from lxml import etree
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives.serialization import load_pem_private_key

CAP_TEMPLATE = '''<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <identifier>alert123</identifier>
  <sender>emma@demo.org</sender>
  <sent>2024-06-01T12:00:00+00:00</sent>
  <status>Actual</status>
  <msgType>Alert</msgType>
  <scope>Public</scope>
  <info>
    <category>Safety</category>
    <event>Test Alert</event>
    <urgency>Immediate</urgency>
    <severity>Extreme</severity>
    <certainty>Observed</certainty>
    <headline>Test Alert</headline>
    <description>This is a test alert.</description>
    <parameter>
      <valueName>mediaLocator</valueName>
      <value>http://http-cdn:8080/alerts/alert123.zip</value>
    </parameter>
  </info>
</alert>
'''

ECAP_TEMPLATE = '''<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2" xmlns:ecap="urn:emma:ecap:1.0">
  <identifier>alert123</identifier>
  <sender>emma@demo.org</sender>
  <sent>2024-06-01T12:00:00+00:00</sent>
  <status>Actual</status>
  <msgType>Alert</msgType>
  <scope>Public</scope>
  <info>
    <category>Safety</category>
    <event>Test Alert</event>
    <urgency>Immediate</urgency>
    <severity>Extreme</severity>
    <certainty>Observed</certainty>
    <headline>Test Alert</headline>
    <description>This is a test alert with media.</description>
    <parameter>
      <valueName>mediaLocator</valueName>
      <value>http://http-cdn:8080/alerts/alert123.zip</value>
    </parameter>
    <ecap:SecureMediaContainer>
      <ecap:Signature>{signature}</ecap:Signature>
      <ecap:Certificate>{certificate}</ecap:Certificate>
    </ecap:SecureMediaContainer>
  </info>
</alert>
'''

class SecureMediaContainer:
    def __init__(self, attachments, privkey_path, cert_path):
        self.attachments = attachments
        self.privkey_path = privkey_path
        self.cert_path = cert_path

    def create_zip(self, out_path):
        with zipfile.ZipFile(out_path, 'w') as zf:
            for f in self.attachments:
                zf.write(f, os.path.basename(f))

    def sign_zip(self, zip_path):
        with open(self.privkey_path, 'rb') as f:
            privkey = load_pem_private_key(f.read(), password=None)
        with open(zip_path, 'rb') as f:
            data = f.read()
        signature = privkey.sign(data, ec.ECDSA(hashes.SHA256()))
        return base64.b64encode(signature).decode()

    def get_cert_b64(self):
        with open(self.cert_path, 'rb') as f:
            return base64.b64encode(f.read()).decode()

if __name__ == "__main__":
    # Generate text-only CAP
    with open("alert123.xml", "w") as f:
        f.write(CAP_TEMPLATE)

    # Prepare media
    os.makedirs("media", exist_ok=True)
    with open("media/test.jpg", "wb") as f:
        f.write(os.urandom(1024))  # Dummy image

    smc = SecureMediaContainer(
        attachments=["media/test.jpg"],
        privkey_path="cert/private_key.pem",
        cert_path="cert/public_key.pem"
    )
    smc.create_zip("alert123.smc.zip")
    signature = smc.sign_zip("alert123.smc.zip")
    cert_b64 = smc.get_cert_b64()

    # Generate eCAP
    ecap_xml = ECAP_TEMPLATE.format(signature=signature, certificate=cert_b64)
    with open("alert123.ecap.xml", "w") as f:
        f.write(ecap_xml) 