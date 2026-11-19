package com.wiredcam

import android.Manifest
import android.content.*
import android.content.pm.PackageManager
import android.os.Bundle
import android.view.Surface
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import java.util.concurrent.Executors
import org.json.JSONObject

class MainActivity : ComponentActivity() {
    private var encoder: H264Encoder? = null; private val executor = Executors.newSingleThreadExecutor()
    private var previewView: PreviewView? = null
    private var camera: Camera? = null
    private val controls = object : BroadcastReceiver() { override fun onReceive(context: Context, intent: Intent) { try { val json = JSONObject(intent.getStringExtra("json") ?: return); when (json.optString("op")) { "camera" -> startCamera(if (json.optString("lens") == "front") CameraSelector.LENS_FACING_FRONT else CameraSelector.LENS_FACING_BACK); "flash" -> camera?.cameraControl?.enableTorch(json.optBoolean("enabled")); "keyframe" -> encoder?.requestKeyFrame() } } catch (_: Exception) { } } }
    private val permission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { if (it) startCamera() }
    override fun onCreate(state: Bundle?) { super.onCreate(state); ContextCompat.registerReceiver(this, controls, IntentFilter("com.wiredcam.CONTROL"), ContextCompat.RECEIVER_NOT_EXPORTED); setContent { App() }; if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) permission.launch(Manifest.permission.CAMERA) else startCamera() }
    @Composable private fun App() { val ctx = LocalContext.current; var streaming by remember { mutableStateOf(false) }; var preview by remember { mutableStateOf(true) }; var port by remember { mutableStateOf("5555") }; var lens by remember { mutableStateOf(CameraSelector.LENS_FACING_BACK) }
        MaterialTheme { Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) { Text("WiredCam", style = MaterialTheme.typography.headlineMedium); if (preview) AndroidView(factory = { PreviewView(it).also { view -> previewView = view; if (ContextCompat.checkSelfPermission(this@MainActivity, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) startCamera(lens) } }, modifier = Modifier.fillMaxWidth().height(220.dp)); OutlinedTextField(port, { port = it.filter(Char::isDigit) }, label = { Text("TCP port") }); Row { Switch(preview, { preview = it }); Text(" Phone preview") }; Row { Button(onClick = { lens = if (lens == CameraSelector.LENS_FACING_BACK) CameraSelector.LENS_FACING_FRONT else CameraSelector.LENS_FACING_BACK; startCamera(lens) }) { Text("Switch camera") }; Spacer(Modifier.width(8.dp)); Button(onClick = { if (!streaming) { ContextCompat.startForegroundService(ctx, Intent(ctx, StreamService::class.java).putExtra("port", port.toIntOrNull() ?: 5555)); streaming = true } else { stopService(Intent(ctx, StreamService::class.java)); streaming = false } }) { Text(if (streaming) "Stop streaming" else "Start streaming") } }; Text(if (streaming) "Server active — connect desktop through ADB" else "Camera is ready") } }
    }
    private fun startCamera(lens: Int = CameraSelector.LENS_FACING_BACK) { val future = ProcessCameraProvider.getInstance(this); future.addListener({ val provider = future.get(); provider.unbindAll(); encoder?.stop(); encoder = H264Encoder(1280, 720, 30, 4_000_000).also { it.start() }; val analysis = ImageAnalysis.Builder().setTargetResolution(android.util.Size(1280, 720)).setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST).setTargetRotation(Surface.ROTATION_0).build().also { it.setAnalyzer(executor) { image -> encoder?.offer(image) ?: image.close() } }; val selector = CameraSelector.Builder().requireLensFacing(lens).build(); val cameraPreview = Preview.Builder().build().also { p -> previewView?.let { p.surfaceProvider = it.surfaceProvider } }; camera = provider.bindToLifecycle(this, selector, cameraPreview, analysis) }, ContextCompat.getMainExecutor(this)) }
    override fun onDestroy() { unregisterReceiver(controls); encoder?.stop(); executor.shutdownNow(); super.onDestroy() }
}
