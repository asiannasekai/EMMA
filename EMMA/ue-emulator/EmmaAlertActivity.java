import android.app.Activity;
import android.os.Bundle;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.LinearLayout;
import android.graphics.BitmapFactory;
import java.io.File;

public class EmmaAlertActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);

        String alertText = getIntent().getStringExtra("alertText");
        String mediaDir = getIntent().getStringExtra("mediaDir");

        TextView tv = new TextView(this);
        tv.setText(alertText);
        layout.addView(tv);

        File dir = new File(mediaDir);
        for (File f : dir.listFiles()) {
            if (f.getName().endsWith(".jpg")) {
                ImageView iv = new ImageView(this);
                iv.setImageBitmap(BitmapFactory.decodeFile(f.getAbsolutePath()));
                layout.addView(iv);
            }
        }
        setContentView(layout);
    }
} 