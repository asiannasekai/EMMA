// Minimal Android service for EMMA alert reception
import android.app.Service;
import android.content.Intent;
import android.os.IBinder;
import java.net.*;
import java.io.*;
import java.security.*;
import java.security.spec.*;
import java.util.zip.*;
import javax.xml.parsers.*;
import org.w3c.dom.*;

public class EmmaAlertService extends Service {
    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        new Thread(this::listenMulticast).start();
        return START_STICKY;
    }

    void listenMulticast() {
        try {
            MulticastSocket socket = new MulticastSocket(5000);
            socket.joinGroup(InetAddress.getByName("239.255.0.1"));
            byte[] buf = new byte[2048];
            while (true) {
                DatagramPacket packet = new DatagramPacket(buf, buf.length);
                socket.receive(packet);
                String xml = new String(packet.getData(), 0, packet.getLength());
                if (xml.contains("mediaLocator")) {
                    String url = extractMediaLocator(xml);
                    fetchAndShowMedia(url, xml);
                }
            }
        } catch (Exception e) { e.printStackTrace(); }
    }

    String extractMediaLocator(String xml) throws Exception {
        DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
        Document doc = dbf.newDocumentBuilder().parse(new ByteArrayInputStream(xml.getBytes()));
        NodeList params = doc.getElementsByTagName("parameter");
        for (int i = 0; i < params.getLength(); i++) {
            Element param = (Element) params.item(i);
            if (param.getElementsByTagName("valueName").item(0).getTextContent().equals("mediaLocator")) {
                return param.getElementsByTagName("value").item(0).getTextContent();
            }
        }
        return null;
    }

    void fetchAndShowMedia(String url, String xml) throws Exception {
        // Download zip
        InputStream in = new URL(url).openStream();
        File zipFile = new File(getFilesDir(), "alert123.zip");
        try (FileOutputStream out = new FileOutputStream(zipFile)) {
            byte[] buf = new byte[1024];
            int n;
            while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
        }
        // Verify signature (omitted for brevity, see README)
        // Unzip and launch UI
        unzip(zipFile, new File(getFilesDir(), "alert123"));
        Intent i = new Intent(this, EmmaAlertActivity.class);
        i.putExtra("alertText", extractText(xml));
        i.putExtra("mediaDir", new File(getFilesDir(), "alert123").getAbsolutePath());
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        startActivity(i);
    }

    void unzip(File zip, File outDir) throws IOException {
        outDir.mkdirs();
        try (ZipInputStream zis = new ZipInputStream(new FileInputStream(zip))) {
            ZipEntry entry;
            while ((entry = zis.getNextEntry()) != null) {
                File out = new File(outDir, entry.getName());
                try (FileOutputStream fos = new FileOutputStream(out)) {
                    byte[] buf = new byte[1024];
                    int n;
                    while ((n = zis.read(buf)) > 0) fos.write(buf, 0, n);
                }
            }
        }
    }

    String extractText(String xml) throws Exception {
        DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
        Document doc = dbf.newDocumentBuilder().parse(new ByteArrayInputStream(xml.getBytes()));
        return doc.getElementsByTagName("description").item(0).getTextContent();
    }

    @Override
    public IBinder onBind(Intent intent) { return null; }
} 