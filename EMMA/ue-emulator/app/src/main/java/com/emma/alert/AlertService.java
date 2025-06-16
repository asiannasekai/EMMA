package com.emma.alert;

import android.app.Service;
import android.content.Intent;
import android.os.IBinder;
import android.util.Log;
import java.net.DatagramPacket;
import java.net.InetAddress;
import java.net.MulticastSocket;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.Signature;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

public class AlertService extends Service {
    private static final String TAG = "EMMAAlertService";
    private static final String MULTICAST_GROUP = "239.255.0.1";
    private static final int MULTICAST_PORT = 5000;
    private static final String CDN_BASE_URL = "http://http-cdn:3000/alerts/";
    private static final String PUBLIC_KEY_PATH = "public_key.pem";
    
    private boolean running = false;
    private Thread multicastThread;
    private X509Certificate publicKey;
    
    @Override
    public void onCreate() {
        super.onCreate();
        loadPublicKey();
    }
    
    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (!running) {
            running = true;
            startMulticastListener();
        }
        return START_STICKY;
    }
    
    @Override
    public void onDestroy() {
        running = false;
        if (multicastThread != null) {
            multicastThread.interrupt();
        }
        super.onDestroy();
    }
    
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
    
    private void loadPublicKey() {
        try {
            InputStream is = getAssets().open(PUBLIC_KEY_PATH);
            CertificateFactory cf = CertificateFactory.getInstance("X.509");
            publicKey = (X509Certificate) cf.generateCertificate(is);
            is.close();
        } catch (Exception e) {
            Log.e(TAG, "Failed to load public key", e);
        }
    }
    
    private void startMulticastListener() {
        multicastThread = new Thread(() -> {
            try {
                MulticastSocket socket = new MulticastSocket(MULTICAST_PORT);
                InetAddress group = InetAddress.getByName(MULTICAST_GROUP);
                socket.joinGroup(group);
                
                byte[] buffer = new byte[4096];
                DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
                
                while (running) {
                    socket.receive(packet);
                    String xml = new String(packet.getData(), 0, packet.getLength());
                    processAlert(xml);
                }
                
                socket.leaveGroup(group);
                socket.close();
            } catch (Exception e) {
                Log.e(TAG, "Multicast listener error", e);
            }
        });
        multicastThread.start();
    }
    
    private void processAlert(String xml) {
        try {
            DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
            DocumentBuilder builder = factory.newDocumentBuilder();
            Document doc = builder.parse(new java.io.ByteArrayInputStream(xml.getBytes()));
            
            // Extract alert information
            NodeList infoNodes = doc.getElementsByTagName("info");
            if (infoNodes.getLength() > 0) {
                Element info = (Element) infoNodes.item(0);
                String description = getElementText(info, "description");
                
                // Check for media
                String mediaLocator = getElementText(info, "mediaLocator");
                if (mediaLocator != null) {
                    String alertId = mediaLocator.substring(mediaLocator.lastIndexOf('/') + 1);
                    downloadAndVerifyMedia(alertId, description);
                } else {
                    // Text-only alert
                    broadcastAlert(description, null, null);
                }
            }
        } catch (Exception e) {
            Log.e(TAG, "Error processing alert", e);
        }
    }
    
    private void downloadAndVerifyMedia(String alertId, String description) {
        new Thread(() -> {
            try {
                // Download SMC
                URL url = new URL(CDN_BASE_URL + alertId);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                InputStream is = conn.getInputStream();
                
                // Save to temporary file
                File tempFile = new File(getCacheDir(), alertId);
                FileOutputStream fos = new FileOutputStream(tempFile);
                byte[] buffer = new byte[1024];
                int len;
                while ((len = is.read(buffer)) != -1) {
                    fos.write(buffer, 0, len);
                }
                fos.close();
                is.close();
                
                // Verify signature
                if (verifySignature(tempFile)) {
                    // Extract media
                    String mediaPath = extractMedia(tempFile);
                    String mediaType = determineMediaType(mediaPath);
                    broadcastAlert(description, mediaPath, mediaType);
                }
                
                tempFile.delete();
            } catch (Exception e) {
                Log.e(TAG, "Error downloading/verifying media", e);
            }
        }).start();
    }
    
    private boolean verifySignature(File smcFile) {
        try {
            // In a real implementation, verify the signature using the public key
            // For this PoC, we'll just return true
            return true;
        } catch (Exception e) {
            Log.e(TAG, "Signature verification failed", e);
            return false;
        }
    }
    
    private String extractMedia(File smcFile) {
        try {
            ZipInputStream zis = new ZipInputStream(new java.io.FileInputStream(smcFile));
            ZipEntry entry;
            String mediaPath = null;
            
            while ((entry = zis.getNextEntry()) != null) {
                File outputFile = new File(getCacheDir(), entry.getName());
                FileOutputStream fos = new FileOutputStream(outputFile);
                byte[] buffer = new byte[1024];
                int len;
                while ((len = zis.read(buffer)) != -1) {
                    fos.write(buffer, 0, len);
                }
                fos.close();
                mediaPath = outputFile.getAbsolutePath();
            }
            
            zis.close();
            return mediaPath;
        } catch (Exception e) {
            Log.e(TAG, "Error extracting media", e);
            return null;
        }
    }
    
    private String determineMediaType(String filePath) {
        if (filePath == null) return null;
        String lowerPath = filePath.toLowerCase();
        if (lowerPath.endsWith(".jpg") || lowerPath.endsWith(".jpeg") || lowerPath.endsWith(".png")) {
            return "image";
        } else if (lowerPath.endsWith(".mp4") || lowerPath.endsWith(".3gp")) {
            return "video";
        }
        return null;
    }
    
    private void broadcastAlert(String text, String mediaPath, String mediaType) {
        Intent intent = new Intent("com.emma.alert.DISPLAY_ALERT");
        intent.putExtra("text", text);
        intent.putExtra("mediaPath", mediaPath);
        intent.putExtra("mediaType", mediaType);
        sendBroadcast(intent);
    }
    
    private String getElementText(Element parent, String tagName) {
        NodeList nodes = parent.getElementsByTagName(tagName);
        if (nodes.getLength() > 0) {
            return nodes.item(0).getTextContent();
        }
        return null;
    }
} 