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
import java.io.File;

public class MainActivity extends Activity {
    private TextView alertText;
    private ImageView alertImage;
    private VideoView alertVideo;
    private Handler handler;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        
        // Initialize views
        alertText = findViewById(R.id.alert_text);
        alertImage = findViewById(R.id.alert_image);
        alertVideo = findViewById(R.id.alert_video);
        
        handler = new Handler(Looper.getMainLooper());
        
        // Start the alert service
        startService(new Intent(this, AlertService.class));
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
    
    @Override
    protected void onDestroy() {
        super.onDestroy();
        stopService(new Intent(this, AlertService.class));
    }
} 