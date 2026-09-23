# Phase 3 Camera Discovery Protocol

The camera app no longer asks users to type an API or IP address. The desktop receiver advertises a DNS-SD/mDNS service and the Android app discovers it with Android Network Service Discovery (NSD).

## Service

```text
Service type: _projected-ai._tcp.local.
WebSocket:    ws://<discovered-host>:<discovered-port>/frames
Properties:   transport=websocket, path=/frames, version=1
```

Start the desktop advertisement with:

```bash
python3 -m pip install -e '.[discovery]'
projected-discovery --name "Projected AI Desktop" --port 8765
```

On Android, tap **Scan for desktop**. The radar listens for nearby services, resolves each host and port, and shows a selectable device card. The user never enters an endpoint. The browser preview intentionally displays a clear message that native radar discovery is available in the Android build; browsers do not expose Android NSD APIs.

After selecting a device, the existing binary JPEG WebSocket protocol is used. The desktop should bind to the local network only during development.

## Build and verify

```bash
npm run build
npx cap sync android
cd android
./gradlew assembleDebug
```
