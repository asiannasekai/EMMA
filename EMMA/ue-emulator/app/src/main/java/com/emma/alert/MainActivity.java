package com.emma.alert;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.widget.TextView;
import android.widget.ImageView;
import android.widget.VideoView;
import android.view.View;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.widget.Toast;
import android.content.pm.PackageManager;
import android.location.Location;
import android.location.LocationManager;
import android.location.LocationListener;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import android.Manifest;

import com.emma.alert.websocket.WebSocketAlertClient;
import org.json.JSONObject;
import org.json.JSONException;

import java.io.File;
import java.util.UUID;

public class MainActivity extends Activity implements WebSocketAlertClient.AlertHandler, LocationListener {
    private static final String TAG = "MainActivity";
    private static final int LOCATION_PERMISSION_REQUEST = 1001;
    
    private TextView alertText;
    private ImageView alertImage;
    private VideoView alertVideo;
    private TextView connectionStatus;
    private Handler handler;
    
    private WebSocketAlertClient webSocketClient;
    private LocationManager locationManager;
    private String ueId;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        
        // Initialize views
        alertText = findViewById(R.id.alert_text);
        alertImage = findViewById(R.id.alert_image);
        alertVideo = findViewById(R.id.alert_video);
        connectionStatus = findViewById(R.id.connection_status);
        
        handler = new Handler(Looper.getMainLooper());
        
        // Generate unique UE ID
        ueId = "UE-" + UUID.randomUUID().toString().substring(0, 8);
        
        // Initialize WebSocket client
        String serverUrl = getWebSocketServerUrl();
        webSocketClient = new WebSocketAlertClient(serverUrl, ueId, this);
        
        // Initialize location services
        initializeLocation();
        
        // Connect to alert distributor
        connectToAlertDistributor();
        
        Log.i(TAG, "EMMA UE Emulator started with ID: " + ueId);
    }
    
    private String getWebSocketServerUrl() {
        // Try to get from environment or use default
        String host = System.getenv("ALERT_DISTRIBUTOR_HOST");
        if (host == null) {
            host = "alert-distributor"; // Docker service name
        }
        
        String port = System.getenv("ALERT_DISTRIBUTOR_PORT");
        if (port == null) {
            port = "8080";
        }
        
        return "ws://" + host + ":" + port;
    }
    
    private void initializeLocation() {
        locationManager = (LocationManager) getSystemService(LOCATION_SERVICE);
        
        // Check for location permissions
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
                != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this,
                    new String[]{Manifest.permission.ACCESS_FINE_LOCATION},
                    LOCATION_PERMISSION_REQUEST);
        } else {
            startLocationUpdates();
        }
    }
    
    private void startLocationUpdates() {
        try {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
                    == PackageManager.PERMISSION_GRANTED) {
                
                locationManager.requestLocationUpdates(
                    LocationManager.GPS_PROVIDER,
                    30000, // 30 seconds
                    100,   // 100 meters
                    this
                );
                
                // Get last known location
                Location lastLocation = locationManager.getLastKnownLocation(LocationManager.GPS_PROVIDER);
                if (lastLocation != null) {
                    updateLocationInWebSocket(lastLocation);
                }
            }
        } catch (SecurityException e) {
            Log.e(TAG, "Location permission not granted", e);
        }
    }
    
    private void connectToAlertDistributor() {
        updateConnectionStatus("Connecting...", false);
        
        try {
            // Get current location for registration
            JSONObject location = null;
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
                    == PackageManager.PERMISSION_GRANTED) {
                
                Location lastLocation = locationManager.getLastKnownLocation(LocationManager.GPS_PROVIDER);
                if (lastLocation != null) {
                    location = new JSONObject();
                    location.put("lat", lastLocation.getLatitude());
                    location.put("lon", lastLocation.getLongitude());
                }
            }
            
            webSocketClient.connect(location);
            
        } catch (JSONException e) {
            Log.e(TAG, "Error creating location object", e);
            webSocketClient.connect();
        }
    }
    
    private void updateLocationInWebSocket(Location location) {
        if (webSocketClient != null && webSocketClient.isConnected()) {
            webSocketClient.updateLocation(location.getLatitude(), location.getLongitude());
        }
    }
    
    private void updateConnectionStatus(String status, boolean connected) {
        handler.post(() -> {
            if (connectionStatus != null) {
                connectionStatus.setText("Status: " + status);
                connectionStatus.setTextColor(connected ? 
                    getResources().getColor(android.R.color.holo_green_light) :
                    getResources().getColor(android.R.color.holo_red_light));
            }
        });
    }
    
    public void displayAlert(String text, String mediaPath, String mediaType) {
        handler.post(() -> {
            // Show alert text
            alertText.setText(text);
            alertText.setVisibility(View.VISIBLE);
            
            // Handle media based on type
            if (mediaPath != null && new File(mediaPath).exists()) {
                if ("image".equals(mediaType)) {
                    alertImage.setImageURI(Uri.parse(mediaPath));
                    alertImage.setVisibility(View.VISIBLE);
                    alertVideo.setVisibility(View.GONE);
                } else if ("video".equals(mediaType)) {
                    alertVideo.setVideoURI(Uri.parse(mediaPath));
                    alertVideo.setVisibility(View.VISIBLE);
                    alertImage.setVisibility(View.GONE);
                    alertVideo.start();
                }
            }
        });
    }
    
    // WebSocketAlertClient.AlertHandler implementation
    @Override
    public void onAlertReceived(JSONObject alertData) {
        try {
            String alertId = alertData.optString("identifier", "unknown");
            String description = alertData.optString("description", "Emergency Alert");
            String headline = alertData.optString("headline", "");
            String severity = alertData.optString("severity", "Unknown");
            
            Log.i(TAG, "Received emergency alert: " + alertId + " - " + headline);
            
            // Display the alert
            String displayText = headline + "\n\n" + description + "\n\nSeverity: " + severity;
            displayAlert(displayText, null, null);
            
            // Show toast notification
            Toast.makeText(this, "Emergency Alert Received: " + headline, Toast.LENGTH_LONG).show();
            
            // Check for media attachments
            if (alertData.has("mediaLocator") || alertData.has("media_attachments")) {
                // TODO: Download and display media
                Log.i(TAG, "Alert contains media attachments");
            }
            
            // Acknowledge that alert was displayed
            webSocketClient.acknowledgeAlert(alertId, true, true);
            
        } catch (Exception e) {
            Log.e(TAG, "Error processing received alert", e);
        }
    }
    
    @Override
    public void onConnectionStatusChanged(boolean connected) {
        String status = connected ? "Connected (" + ueId + ")" : "Disconnected";
        updateConnectionStatus(status, connected);
        
        if (connected) {
            Toast.makeText(this, "Connected to EMMA Alert System", Toast.LENGTH_SHORT).show();
        } else {
            Toast.makeText(this, "Disconnected from Alert System", Toast.LENGTH_SHORT).show();
        }
    }
    
    @Override
    public void onError(String error) {
        Log.e(TAG, "WebSocket error: " + error);
        Toast.makeText(this, "Alert System Error: " + error, Toast.LENGTH_LONG).show();
        updateConnectionStatus("Error: " + error, false);
    }
    
    // LocationListener implementation
    @Override
    public void onLocationChanged(Location location) {
        Log.d(TAG, "Location updated: " + location.getLatitude() + ", " + location.getLongitude());
        updateLocationInWebSocket(location);
    }
    
    @Override
    public void onStatusChanged(String provider, int status, Bundle extras) {
        Log.d(TAG, "Location provider status changed: " + provider + " = " + status);
    }
    
    @Override
    public void onProviderEnabled(String provider) {
        Log.d(TAG, "Location provider enabled: " + provider);
    }
    
    @Override
    public void onProviderDisabled(String provider) {
        Log.d(TAG, "Location provider disabled: " + provider);
    }
    
    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        if (requestCode == LOCATION_PERMISSION_REQUEST) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                startLocationUpdates();
            } else {
                Log.w(TAG, "Location permission denied");
                Toast.makeText(this, "Location permission required for precise alerts", Toast.LENGTH_LONG).show();
            }
        }
    }
    
    @Override
    protected void onResume() {
        super.onResume();
        if (webSocketClient != null && !webSocketClient.isConnected()) {
            connectToAlertDistributor();
        }
    }
    
    @Override
    protected void onDestroy() {
        super.onDestroy();
        
        if (webSocketClient != null) {
            webSocketClient.disconnect();
        }
        
        if (locationManager != null) {
            try {
                locationManager.removeUpdates(this);
            } catch (SecurityException e) {
                Log.e(TAG, "Error removing location updates", e);
            }
        }
        
        Log.i(TAG, "EMMA UE Emulator destroyed");
    }
} 