"""WiredCam desktop client. Run with Python 3.11+ on Windows."""
from __future__ import annotations
import json, shutil, socket, struct, subprocess, sys, threading, time
from fractions import Fraction
from pathlib import Path
import av
import numpy as np
import pyvirtualcam
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget)

HEADER = struct.Struct(">BBQI")
VIDEO_CONFIG, VIDEO_FRAME, CONTROL, KEYFRAME = 1, 2, 16, 1

def adb_path() -> str | None:
    bundled = Path(__file__).parent / "platform-tools" / "adb.exe"
    return str(bundled) if bundled.exists() else shutil.which("adb")

def adb_devices() -> tuple[str, str | None]:
    adb = adb_path()
    if not adb: return "adb.exe not found (install Android platform-tools or bundle it)", None
    result = subprocess.run([adb, "devices"], capture_output=True, text=True, timeout=8)
    rows = [r.split() for r in result.stdout.splitlines()[1:] if r.strip()]
    if not rows: return "No Android device found. Enable USB debugging and reconnect.", None
    serial, state = rows[0][0], rows[0][1]
    if state == "unauthorized": return "Phone is unauthorized — accept the USB debugging prompt.", None
    if state != "device": return f"Device state: {state}", None
    return f"USB device connected: {serial}", serial

class Receiver(QObject):
    frame = Signal(QImage, float, float)
    status = Signal(str)
    disconnected = Signal()
    def __init__(self): super().__init__(); self.sock: socket.socket | None = None; self.running = False; self.decoder = av.CodecContext.create("h264", "r"); self.decoder.options = {"flags": "low_delay", "fflags": "nobuffer", "threads": "1"}; self.record: av.container.OutputContainer | None = None; self.record_stream = None; self.virtual = None; self.latest = None
    def connect(self, host: str, port: int):
        self.running = True; threading.Thread(target=self._run, args=(host, port), daemon=True).start()
    def close(self):
        self.running = False
        if self.sock:
            try: self.sock.shutdown(socket.SHUT_RDWR); self.sock.close()
            except OSError: pass
        if self.record: self.record.close(); self.record = None
        if self.virtual: self.virtual.close(); self.virtual = None
    def send_control(self, obj: dict):
        if self.sock:
            raw = json.dumps(obj).encode(); self.sock.sendall(HEADER.pack(CONTROL, 0, 0, len(raw)) + raw)
    def start_record(self, path: str):
        self.record = av.open(path, "w"); self.record_stream = self.record.add_stream("h264", rate=30)
    def _read_exact(self, size: int) -> bytes:
        data = b""
        while len(data) < size:
            block = self.sock.recv(size - len(data))
            if not block: raise ConnectionError("stream ended")
            data += block
        return data
    def _run(self, host: str, port: int):
        try:
            self.sock = socket.create_connection((host, port), timeout=5); self.sock.settimeout(2); self.status.emit("Connected; waiting for video")
            started = time.monotonic(); frames = 0
            while self.running:
                typ, flags, pts, length = HEADER.unpack(self._read_exact(14))
                if length > 16 * 1024 * 1024: raise ValueError("invalid payload length")
                payload = self._read_exact(length)
                if typ == CONTROL: self.status.emit(f"Phone: {payload.decode(errors='replace')}"); continue
                if typ not in (VIDEO_CONFIG, VIDEO_FRAME): continue
                # Config is Annex-B SPS/PPS; feed to decoder before frames. Recording writes only media frames.
                packet = av.Packet(payload); packet.pts = packet.dts = pts; packet.time_base = Fraction(1, 1_000_000)
                if self.record and typ == VIDEO_FRAME: self.record.mux(packet)
                for decoded in self.decoder.decode(packet):
                    rgb = decoded.to_ndarray(format="rgb24"); self.latest = rgb
                    if self.virtual is not None: self.virtual.send(rgb)
                    image = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format.Format_RGB888).copy()
                    frames += 1; elapsed = max(time.monotonic() - started, .001); self.frame.emit(image, frames / elapsed, max(0, (time.monotonic_ns() // 1000 - pts) / 1000))
        except Exception as exc:
            if self.running: self.status.emit(f"Disconnected: {exc}")
        finally: self.running = False; self.disconnected.emit()

class Window(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("WiredCam Desktop"); self.receiver = Receiver(); self.receiver.frame.connect(self.on_frame); self.receiver.status.connect(self.statusBar().showMessage); self.receiver.disconnected.connect(lambda: self.connect_btn.setText("Connect")); self._build(); self.refresh_device()
    def _build(self):
        root = QWidget(); self.setCentralWidget(root); layout = QVBoxLayout(root); form = QFormLayout(); self.device = QLabel(); form.addRow("Device", self.device); self.ip = QLineEdit("127.0.0.1"); self.port = QSpinBox(); self.port.setRange(1, 65535); self.port.setValue(5555); form.addRow("Phone address", self.ip); form.addRow("Port", self.port); self.camera = QComboBox(); self.camera.addItems(["Rear", "Front"]); self.camera.currentIndexChanged.connect(lambda i: self.control({"op":"camera", "lens":"front" if i else "back"})); form.addRow("Camera", self.camera); self.flash = QCheckBox("Flashlight"); self.flash.toggled.connect(lambda v: self.control({"op":"flash", "enabled":v})); form.addRow("", self.flash); layout.addLayout(form)
        buttons = QHBoxLayout(); self.connect_btn = QPushButton("Connect"); self.connect_btn.clicked.connect(self.toggle); refresh = QPushButton("Refresh USB"); refresh.clicked.connect(self.refresh_device); snapshot = QPushButton("Snapshot"); snapshot.clicked.connect(self.snapshot); record = QPushButton("Record MP4"); record.clicked.connect(self.toggle_record); buttons.addWidget(self.connect_btn); buttons.addWidget(refresh); buttons.addWidget(snapshot); buttons.addWidget(record); layout.addLayout(buttons)
        self.preview = QLabel("No video"); self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter); self.preview.setMinimumSize(640, 360); self.preview.setStyleSheet("background:#111;color:#ddd;"); layout.addWidget(self.preview); self.stats = QLabel("FPS: — | transport latency: — ms"); layout.addWidget(self.stats)
        self.virtual_check = QCheckBox("Publish virtual webcam (requires OBS Virtual Camera backend)"); self.virtual_check.toggled.connect(self.toggle_virtual); layout.addWidget(self.virtual_check)
    def refresh_device(self): self.device.setText(adb_devices()[0])
    def toggle(self):
        if self.receiver.running: self.receiver.close(); self.connect_btn.setText("Connect"); return
        host, port = self.ip.text().strip(), self.port.value()
        if host in ("127.0.0.1", "localhost"):
            message, serial = adb_devices(); self.device.setText(message)
            if not serial: return
            adb = adb_path(); result = subprocess.run([adb, "-s", serial, "forward", f"tcp:{port}", f"tcp:{port}"], capture_output=True, text=True)
            if result.returncode: QMessageBox.warning(self, "ADB forwarding failed", result.stderr); return
        self.receiver.connect(host, port); self.connect_btn.setText("Disconnect")
    def control(self, obj):
        if self.receiver.running: self.receiver.send_control(obj)
    def on_frame(self, image, fps, latency): self.preview.setPixmap(QPixmap.fromImage(image).scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)); self.stats.setText(f"FPS: {fps:.1f} | transport latency: {latency:.1f} ms")
    def snapshot(self):
        pix = self.preview.pixmap()
        if pix:
            name, _ = QFileDialog.getSaveFileName(self, "Save snapshot", "wiredcam.png", "PNG (*.png)")
            if name: pix.save(name, "PNG")
    def toggle_virtual(self, enabled):
        try:
            if enabled and self.receiver.virtual is None: self.receiver.virtual = pyvirtualcam.Camera(width=1280, height=720, fps=30, fmt=pyvirtualcam.PixelFormat.RGB)
            if not enabled and self.receiver.virtual is not None: self.receiver.virtual.close(); self.receiver.virtual = None
        except Exception as exc:
            self.virtual_check.blockSignals(True); self.virtual_check.setChecked(False); self.virtual_check.blockSignals(False); QMessageBox.warning(self, "Virtual camera unavailable", str(exc))
    def toggle_record(self):
        if self.receiver.record: self.receiver.record.close(); self.receiver.record = None; self.statusBar().showMessage("Recording saved"); return
        name, _ = QFileDialog.getSaveFileName(self, "Record stream", "wiredcam.mp4", "MP4 (*.mp4)")
        if name: self.receiver.start_record(name); self.statusBar().showMessage("Recording H.264 stream")
    def closeEvent(self, event): self.receiver.close(); event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv); w = Window(); w.resize(900, 700); w.show(); sys.exit(app.exec())
