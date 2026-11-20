# WiredCam

Turn an Android phone into a USB-only webcam for a Windows PC. WiredCam uses ADB port forwarding over the USB cable, so it does not need Wi-Fi, an account, a cloud service, or an Internet permission on the phone.

> **Direct APK download:** [WiredCam-debug.apk](https://github.com/Sumit13-robo/wired_cam/raw/refs/heads/main/release/WiredCam-debug.apk)
>
> Repository path: [`release/WiredCam-debug.apk`](release/WiredCam-debug.apk). This is a debug-signed build for testing, not a Play Store release.

## What you need

| Device | Requirement |
|---|---|
| Android phone | Android 8.0 (API 26) or later, a working rear/front camera, and a data-capable USB cable |
| Windows laptop | Windows 10/11, a modern web browser, and [Android SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools) |
| Both devices | USB cable connected directly to the laptop where possible; avoid charge-only cables and unreliable hubs |

## Quick start

1. On the phone, install the [WiredCam APK](https://github.com/Sumit13-robo/wired_cam/raw/refs/heads/main/release/WiredCam-debug.apk).
2. Enable **Developer options** and **USB debugging** on the phone.
3. Install Android Platform-Tools on Windows so that `adb.exe` is available.
4. Download the `WiredCam-Windows` artifact from the repository’s [Actions page](https://github.com/Sumit13-robo/wired_cam/actions), extract it, and run `WiredCam.exe`.
5. Connect the phone by USB, unlock it, accept the **Allow USB debugging?** prompt, open WiredCam on the phone, and press **Start streaming**.
6. In the browser dashboard that opens on the laptop, press **Connect camera**.

## 1. Install the Android app

### Download and install

1. On the phone, open this exact link: <https://github.com/Sumit13-robo/wired_cam/raw/refs/heads/main/release/WiredCam-debug.apk>.
2. If Android blocks the install, choose **Settings** on the warning and enable **Allow from this source** for the browser or file manager you used.
3. Return to the installer and choose **Install**.
4. Open **WiredCam** and grant the **Camera** permission when asked.

### Enable USB debugging

Exact wording varies by phone manufacturer.

1. Open **Settings > About phone**.
2. Tap **Build number** seven times. Enter the phone lock-screen PIN if Android asks.
3. Return to Settings and open **System > Developer options** (on some phones it is under **Additional settings**).
4. Enable **USB debugging** and confirm the warning.
5. Connect the phone to the Windows laptop with a USB cable. If asked what the USB connection should do, select **File transfer** rather than charge-only.
6. Leave the phone unlocked. When the **Allow USB debugging?** prompt appears, select **Allow**. You may check **Always allow from this computer** if it is your own laptop.

Android’s official device setup documentation also explains USB debugging and Windows ADB drivers: [Run apps on a hardware device](https://developer.android.com/studio/run/device).

### Start streaming

1. Open WiredCam on the phone.
2. Optionally choose the camera and toggle the phone preview.
3. Leave the port at `5555` unless you change it on both phone and desktop.
4. Tap **Start streaming**. The persistent "WiredCam is ready" notification means the phone is waiting for the Windows app.

## 2. Install Android Platform-Tools on Windows

The Windows bridge needs `adb.exe` to create the USB tunnel.

1. Download **SDK Platform-Tools for Windows** from the official [Platform-Tools page](https://developer.android.com/tools/releases/platform-tools).
2. Extract the ZIP, for example to `C:\Android\platform-tools`.
3. Use either option below:
   - Add `C:\Android\platform-tools` to the Windows **Path** environment variable, then restart the Windows terminal/apps; or
   - Copy the entire `platform-tools` folder next to `WiredCam.exe` after downloading the Windows package.
4. Open Command Prompt and verify the connection:

   ```bat
   adb devices
   ```

   Your device must appear with the state `device`. If it says `unauthorized`, unlock the phone and accept the USB-debugging prompt. If no device is listed, try another data cable/USB port and install the phone manufacturer’s Windows USB driver if needed.

## 3. Get and run the Windows application

### Ready-made package

1. Open [GitHub Actions](https://github.com/Sumit13-robo/wired_cam/actions).
2. Open the newest successful **Build release artifacts** run.
3. Under **Artifacts**, download **WiredCam-Windows**.
4. Extract the ZIP to a normal writable folder, such as `C:\WiredCam`.
5. Ensure `adb.exe` is on `Path`, or place `platform-tools` beside `WiredCam.exe`.
6. Run `WiredCam.exe`. It opens the local dashboard at <http://127.0.0.1:8765>.
7. Press **Refresh USB status**, then **Connect camera**.

The browser dashboard binds only to `127.0.0.1`; it is not exposed to your Wi-Fi network.

### Build the Windows package yourself

Install 64-bit Python 3.11, clone this repository, then run PowerShell from the repository folder:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\web-app\package.ps1
```

The package is created here:

```text
web-app\dist\WiredCam\WiredCam.exe
```

## 4. Use the dashboard

- **Connect camera**: detects the USB-debugging phone, runs `adb forward tcp:5555 tcp:5555`, and opens the stream.
- **Rear/Front camera**: sends a camera-switch control message to the phone.
- **Flashlight**: controls the rear-camera torch when supported by the phone.
- **Refresh video signal**: asks the encoder for an AVC keyframe after a connection hiccup.
- **Connection options**: set a different port, or enable USB tethering and type the phone IP for the fallback direct-TCP mode.

## Build from source

### Android APK

Install Android Studio with **Android SDK Platform 35**. Open the repository folder in Android Studio, let it create the machine-local `local.properties` SDK path, then run:

```bash
./gradlew :android-app:assembleDebug
```

The APK is written to:

```text
android-app/build/outputs/apk/debug/android-app-debug.apk
```

### Browser dashboard without packaging

On Windows, from the repository root:

```bat
cd web-app
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn server:app --host 127.0.0.1 --port 8765
```

Then open <http://127.0.0.1:8765>.

## GitHub release artifacts

Every push to `main` runs **Build release artifacts** and uploads:

- **WiredCam-Android-debug-APK** — an APK compiled against Android SDK 35.
- **WiredCam-Windows** — portable folder containing `WiredCam.exe`.

Use the Actions artifacts for the freshest build. The direct APK link at the top of this README points to the tested build committed to this repository.

## Troubleshooting

- **`adb devices` shows `unauthorized`:** unlock the phone and accept the RSA/USB-debugging prompt.
- **No device appears:** use a data cable, change USB port, select File transfer, then install the OEM Windows USB driver if necessary.
- **Dashboard says it cannot reach the stream:** open the phone app first, grant Camera permission, tap Start streaming, and confirm both port fields are `5555`.
- **Black/late preview:** reconnect, use **Refresh video signal**, and avoid USB hubs. The browser preview is designed for convenient local monitoring; actual latency varies with phone camera/codec hardware.
- **APK will not install:** remove an older build signed by a different key, or uninstall the old WiredCam app before installing this debug build.

See [detailed troubleshooting](docs/TROUBLESHOOTING.md) and the [wire protocol](docs/PROTOCOL.md) for technical details.

## Current limitations

This is a video-only debug build. Dynamic resolution/bitrate/zoom controls, AAC microphone audio, automatic rotation metadata, and a signed production installer are not implemented yet. Camera compatibility and latency depend on the device’s hardware AVC encoder.
