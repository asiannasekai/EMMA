package com.emma.alert.websocket;

import android.util.Log;
import okhttp3.*;
import org.json.JSONException;
import org.json.JSONObject;
import java.util.concurrent.TimeUnit;

public class WebSocketAlertClient extends WebSocketListener {
    private static final String TAG = "WebSocketAlertClient";
    private static final int RECONNECT_INTERVAL = 5000; // 5 seconds
    private static final int HEARTBEAT_INTERVAL = 30000; // 30 seconds
    
    private OkHttpClient client;
    private WebSocket webSocket;
    private AlertHandler alertHandler;
    private String serverUrl;
    private String ueId;
    private JSONObject location;
    private boolean isConnected = false;
    private boolean shouldReconnect = true;
    
    private Runnable heartbeatRunnable;
    private android.os.Handler handler;
    
    public interface AlertHandler {
        void onAlertReceived(JSONObject alertData);
        void onConnectionStatusChanged(boolean connected);
        void onError(String error);
    }
    
    public WebSocketAlertClient(String serverUrl, String ueId, AlertHandler handler) {
        this.serverUrl = serverUrl;
        this.ueId = ueId;
        this.alertHandler = handler;
        this.handler = new android.os.Handler(android.os.Looper.getMainLooper());
        
        this.client = new OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(10, TimeUnit.SECONDS)
            .pingInterval(30, TimeUnit.SECONDS)
            .build();
            
        setupHeartbeat();
    }
    
    public void connect() {
        connect(null);
    }
    
    public void connect(JSONObject location) {
        if (isConnected) {
            Log.w(TAG, "Already connected to WebSocket server");
            return;
        }
        
        this.location = location;
        shouldReconnect = true;
        
        try {
            Request request = new Request.Builder()
                .url(serverUrl)
                .build();
                
            webSocket = client.newWebSocket(request, this);
            Log.i(TAG, "Connecting to WebSocket server: " + serverUrl);
            
        } catch (Exception e) {
            Log.e(TAG, "Failed to create WebSocket connection", e);
            alertHandler.onError("Failed to connect: " + e.getMessage());
        }
    }
    
    public void disconnect() {
        shouldReconnect = false;
        
        if (webSocket != null) {
            webSocket.close(1000, "Client disconnect");
        }
        
        stopHeartbeat();
        Log.i(TAG, "Disconnected from WebSocket server");
    }
    
    public void updateLocation(double latitude, double longitude) {
        try {
            location = new JSONObject();
            location.put("lat", latitude);
            location.put("lon", longitude);
            
            if (isConnected) {
                JSONObject message = new JSONObject();
                message.put("type", "location_update");
                message.put("location", location);
                sendMessage(message);
            }
        } catch (JSONException e) {
            Log.e(TAG, "Error updating location", e);
        }
    }
    
    public void acknowledgeAlert(String alertId, boolean received, boolean displayed) {
        try {
            JSONObject ack = new JSONObject();
            ack.put("type", "alert_ack");
            ack.put("alertId", alertId);
            ack.put("received", received);
            ack.put("displayed", displayed);
            ack.put("timestamp", System.currentTimeMillis());
            
            sendMessage(ack);
            Log.d(TAG, "Sent acknowledgment for alert: " + alertId);
            
        } catch (JSONException e) {
            Log.e(TAG, "Error creating alert acknowledgment", e);
        }
    }
    
    private void sendMessage(JSONObject message) {
        if (webSocket != null && isConnected) {
            webSocket.send(message.toString());
        } else {
            Log.w(TAG, "Cannot send message - not connected to WebSocket");
        }
    }
    
    private void setupHeartbeat() {
        heartbeatRunnable = new Runnable() {
            @Override
            public void run() {
                if (isConnected) {
                    try {
                        JSONObject heartbeat = new JSONObject();
                        heartbeat.put("type", "heartbeat");
                        heartbeat.put("timestamp", System.currentTimeMillis());
                        sendMessage(heartbeat);
                        
                        handler.postDelayed(this, HEARTBEAT_INTERVAL);
                    } catch (JSONException e) {
                        Log.e(TAG, "Error sending heartbeat", e);
                    }
                }
            }
        };
    }
    
    private void startHeartbeat() {
        stopHeartbeat();
        handler.postDelayed(heartbeatRunnable, HEARTBEAT_INTERVAL);
    }
    
    private void stopHeartbeat() {
        if (heartbeatRunnable != null) {
            handler.removeCallbacks(heartbeatRunnable);
        }
    }
    
    private void registerWithServer() {
        try {
            JSONObject registration = new JSONObject();
            registration.put("type", "register");
            registration.put("ueId", ueId);
            
            if (location != null) {
                registration.put("location", location);
            }
            
            // Add device capabilities
            JSONObject capabilities = new JSONObject();
            capabilities.put("supportsVideo", true);
            capabilities.put("supportsImages", true);
            capabilities.put("supportsAudio", true);
            capabilities.put("screenSize", "standard");
            registration.put("capabilities", capabilities);
            
            sendMessage(registration);
            Log.i(TAG, "Sent registration message for UE: " + ueId);
            
        } catch (JSONException e) {
            Log.e(TAG, "Error creating registration message", e);
        }
    }
    
    private void scheduleReconnect() {
        if (shouldReconnect && !isConnected) {
            handler.postDelayed(() -> {
                Log.i(TAG, "Attempting to reconnect...");
                connect(location);
            }, RECONNECT_INTERVAL);
        }
    }
    
    // WebSocketListener methods
    @Override
    public void onOpen(WebSocket webSocket, Response response) {
        Log.i(TAG, "WebSocket connection opened");
        isConnected = true;
        
        // Register with the server
        registerWithServer();
        
        // Start heartbeat
        startHeartbeat();
        
        // Notify handler
        handler.post(() -> alertHandler.onConnectionStatusChanged(true));
    }
    
    @Override
    public void onMessage(WebSocket webSocket, String text) {
        try {
            JSONObject message = new JSONObject(text);
            String messageType = message.getString("type");
            
            Log.d(TAG, "Received message type: " + messageType);
            
            switch (messageType) {
                case "welcome":
                    Log.i(TAG, "Received welcome message");
                    break;
                    
                case "registration_confirmed":
                    Log.i(TAG, "Registration confirmed by server");
                    break;
                    
                case "emergency_alert":
                    handleEmergencyAlert(message);
                    break;
                    
                case "heartbeat_ack":
                    Log.v(TAG, "Heartbeat acknowledged");
                    break;
                    
                case "error":
                    String error = message.optString("message", "Unknown error");
                    Log.e(TAG, "Server error: " + error);
                    handler.post(() -> alertHandler.onError(error));
                    break;
                    
                default:
                    Log.w(TAG, "Unknown message type: " + messageType);
            }
            
        } catch (JSONException e) {
            Log.e(TAG, "Error parsing WebSocket message", e);
        }
    }
    
    private void handleEmergencyAlert(JSONObject message) {
        try {
            JSONObject alertData = message.getJSONObject("alert");
            String alertId = alertData.optString("identifier", "unknown");
            
            Log.i(TAG, "Received emergency alert: " + alertId);
            
            // Acknowledge receipt
            acknowledgeAlert(alertId, true, false);
            
            // Pass to alert handler
            handler.post(() -> alertHandler.onAlertReceived(alertData));
            
        } catch (JSONException e) {
            Log.e(TAG, "Error processing emergency alert", e);
        }
    }
    
    @Override
    public void onClosing(WebSocket webSocket, int code, String reason) {
        Log.i(TAG, "WebSocket closing: " + code + " " + reason);
    }
    
    @Override
    public void onClosed(WebSocket webSocket, int code, String reason) {
        Log.i(TAG, "WebSocket closed: " + code + " " + reason);
        isConnected = false;
        stopHeartbeat();
        
        // Notify handler
        handler.post(() -> alertHandler.onConnectionStatusChanged(false));
        
        // Schedule reconnect if needed
        scheduleReconnect();
    }
    
    @Override
    public void onFailure(WebSocket webSocket, Throwable t, Response response) {
        Log.e(TAG, "WebSocket failure", t);
        isConnected = false;
        stopHeartbeat();
        
        String error = "Connection failed: " + t.getMessage();
        handler.post(() -> {
            alertHandler.onConnectionStatusChanged(false);
            alertHandler.onError(error);
        });
        
        // Schedule reconnect
        scheduleReconnect();
    }
    
    public boolean isConnected() {
        return isConnected;
    }
    
    public String getUeId() {
        return ueId;
    }
}