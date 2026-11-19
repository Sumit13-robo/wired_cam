# WiredCam

WiredCam is a USB-only Android camera streamer. Android runs the camera/encoder and a localhost TCP server; the Windows client uses ADB port forwarding over the USB cable. There is no cloud service, account, Wi-Fi discovery, or Internet permission.

## Repository layout

- `android-app` — Kotlin Android app, min SDK 26.
- `web-app` — local browser dashboard and ADB/AVC bridge for Windows.
- `windows-app` — legacy PySide6 desktop client.
- `docs/PROTOCOL.md` — binary transport specification.

## Milestone A — build and test the phone server

1. Install Android Studio with Android SDK Platform 35, open this folder, and run `./gradlew :android-app:assembleDebug` (or use Android Studio's **Run** action). The included Gradle wrapper downloads Gradle automatically; Android Studio creates the machine-local `local.properties` SDK path file.
2. On the phone enable **Developer options > USB debugging**, connect USB, and install `android-app/build/outputs/apk/debug/android-app-debug.apk`.
3. Open WiredCam, grant Camera access, and press **Start streaming**. A persistent notification indicates the foreground service is listening on port 5555.
4. Verify on a computer with `adb forward tcp:5555 tcp:5555`; then use a TCP client to connect to `127.0.0.1:5555`. The first bytes are the protocol header in [PROTOCOL.md](docs/PROTOCOL.md).

## Milestone B — run the website

1. Install 64-bit Python 3.11+ and Android Platform Tools. Put `adb.exe` on `PATH`, or copy the complete Platform Tools directory into `web-app/platform-tools`.
2. From a Windows command prompt: `cd web-app`, `py -3.11 -m venv .venv`, `.venv\\Scripts\\activate`, then `pip install -r requirements.txt`.
3. Start the local app with `uvicorn server:app --host 127.0.0.1 --port 8765`, then open `http://127.0.0.1:8765`.
4. With the phone app streaming, click **Connect camera**. The bridge detects authorization status, runs `adb -s SERIAL forward tcp:5555 tcp:5555`, decodes AVC locally, and sends preview frames only to the open browser tab.
5. For USB tethering instead, open **Connection options**, enable **Use USB tethering**, enter the phone IP, then connect. No ADB is used in that mode.

## Windows package

The Windows package is a native `WiredCam.exe` that starts the local browser dashboard automatically. It is not hosted on the internet and works only on `127.0.0.1`.

To package it yourself on Windows, run PowerShell from the repository root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\web-app\package.ps1
```

The application is created at `web-app\dist\WiredCam\WiredCam.exe`. Install Android Platform Tools, then put `adb.exe` on `PATH` or copy the full `platform-tools` folder next to the EXE.

## Release artifacts through GitHub Actions

Every push to `main` runs **Build release artifacts**. Its artifacts are:

- `WiredCam-Android-debug-APK` — installable APK built against Android SDK 35.
- `WiredCam-Windows` — portable Windows dashboard folder containing `WiredCam.exe`.

Open the repository’s **Actions** tab, select the completed run, then download both artifacts. For APK installation, enable **Install unknown apps** for your file manager and open the downloaded APK on the phone.

## Milestone C — controls

The UI sends camera and flashlight controls according to the protocol. Current Android build reserves full dynamic reconfiguration (resolution, bitrate, focus, zoom, and flash application) for the next iteration; reconnect after changing encoder settings. The server safely ignores controls it does not implement.

## Milestone D — virtual camera and packaging

Install OBS Studio and start its **Virtual Camera**. Install `pyvirtualcam` with the requirements above; a backend must be present before frames can be exposed. Create a portable executable with `pyinstaller --noconfirm --windowed --name WiredCam main.py`, then copy `platform-tools` beside `dist/WiredCam/WiredCam.exe`.

## Milestone E — audio and recording

The desktop Record button muxes received AVC access units into MP4 without a video re-encode. Audio packet types are documented but microphone capture/AAC muxing is intentionally not yet implemented.

## Limitations and next steps

CameraX's ImageAnalysis path is broadly compatible but costs more latency than a device-specific Surface pipeline. Test real hardware before promising the 100–150 ms target. Add a `Camera2`/MediaCodec surface path for devices whose encoders reject flexible YUV input, implement applied controls and rotation metadata, then add AAC audio and an installer. See [Troubleshooting](docs/TROUBLESHOOTING.md).
