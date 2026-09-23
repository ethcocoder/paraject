package com.projectedai.camera;

import android.content.Context;
import android.net.nsd.NsdManager;
import android.net.nsd.NsdServiceInfo;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "ProjectedDiscovery")
public class ProjectedDiscoveryPlugin extends Plugin {
    private static final String SERVICE_TYPE = "_projected-ai._tcp.";
    private NsdManager manager;
    private NsdManager.DiscoveryListener listener;

    @PluginMethod
    public void startDiscovery(PluginCall call) {
        stopDiscoveryInternal();
        manager = (NsdManager) getContext().getSystemService(Context.NSD_SERVICE);
        listener = new NsdManager.DiscoveryListener() {
            @Override public void onDiscoveryStarted(String serviceType) { call.resolve(); }
            @Override public void onDiscoveryStopped(String serviceType) { }
            @Override public void onStartDiscoveryFailed(String serviceType, int errorCode) { call.reject("Discovery could not start: " + errorCode); }
            @Override public void onStopDiscoveryFailed(String serviceType, int errorCode) { }
            @Override public void onServiceFound(NsdServiceInfo service) {
                manager.resolveService(service, new NsdManager.ResolveListener() {
                    @Override public void onResolveFailed(NsdServiceInfo failed, int errorCode) { }
                    @Override public void onServiceResolved(NsdServiceInfo resolved) {
                        JSObject result = new JSObject();
                        result.put("name", resolved.getServiceName());
                        result.put("host", resolved.getHost().getHostAddress());
                        result.put("port", resolved.getPort());
                        result.put("endpoint", "ws://" + resolved.getHost().getHostAddress() + ":" + resolved.getPort() + "/frames");
                        notifyListeners("deviceFound", result);
                    }
                });
            }
            @Override public void onServiceLost(NsdServiceInfo service) { }
        };
        manager.discoverServices(SERVICE_TYPE, NsdManager.PROTOCOL_DNS_SD, listener);
    }

    @PluginMethod
    public void stopDiscovery(PluginCall call) { stopDiscoveryInternal(); call.resolve(); }

    private void stopDiscoveryInternal() {
        if (manager != null && listener != null) {
            try { manager.stopServiceDiscovery(listener); } catch (Exception ignored) { }
            listener = null;
        }
    }

    @Override protected void handleOnDestroy() { stopDiscoveryInternal(); super.handleOnDestroy(); }
}
