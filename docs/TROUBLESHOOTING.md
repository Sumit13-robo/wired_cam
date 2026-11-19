# Troubleshooting

**No device found:** Install Android SDK Platform Tools, or copy its `platform-tools` folder next to `windows-app/main.py`. Enable Developer Options, enable USB debugging, reconnect the cable, and accept the RSA authorization prompt on the phone. `adb devices` must show `device`, not `unauthorized`.

**Desktop connects but stays black:** Start streaming on the phone first, ensure both port fields are 5555, then run `adb forward --list`. On some devices the hardware AVC encoder does not accept flexible YUV input at 720p; select a supported camera size or use a device/vendor update. The desktop intentionally drops late frames rather than buffering.

**Another app cannot see WiredCam:** Install and start OBS Virtual Camera, then enable the virtual-camera option in the desktop app. `pyvirtualcam` publishes through installed virtual-camera backends; it cannot create a Windows driver itself.

**Cable reconnect:** press Refresh USB then Connect. The desktop reissues `adb forward`; no network or Internet permission is used.

**High latency:** Use 720p30, a short/high-quality USB cable, and disable USB hubs. Measure glass-to-glass by filming a stopwatch visible in both the phone preview and desktop preview; subtract displayed stopwatch times. The target is 100–150 ms, though camera sensor and vendor codec pipelines can make this device-specific.
