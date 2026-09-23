package com.projectedai.camera;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(ProjectedDiscoveryPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
