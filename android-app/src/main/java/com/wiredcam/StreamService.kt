package com.wiredcam

import android.app.*
import android.content.*
import android.os.*
import androidx.core.app.NotificationCompat
import java.net.ServerSocket
import java.net.Socket
import java.net.InetAddress
import java.io.*
import java.util.concurrent.Executors

class StreamService : Service() {
    companion object { @Volatile var instance: StreamService? = null }
    private val worker = Executors.newCachedThreadPool(); private var server: ServerSocket? = null
    private var client: Socket? = null; private var wakeLock: PowerManager.WakeLock? = null
    @Volatile var output: DataOutputStream? = null
    override fun onBind(intent: Intent?) = null
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        instance = this
        val port = intent?.getIntExtra("port", 5555) ?: 5555
        startForeground(7, notification()); wakeLock = (getSystemService(POWER_SERVICE) as PowerManager).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "WiredCam:stream").apply { acquire() }
        worker.execute { acceptLoop(port) }; return START_STICKY
    }
    private fun notification(): Notification {
        val channel = NotificationChannel("stream", "WiredCam streaming", NotificationManager.IMPORTANCE_LOW)
        (getSystemService(NOTIFICATION_SERVICE) as NotificationManager).createNotificationChannel(channel)
        return NotificationCompat.Builder(this, "stream").setSmallIcon(android.R.drawable.presence_video_online).setContentTitle("WiredCam is ready").setContentText("Waiting for desktop client").build()
    }
    private fun acceptLoop(port: Int) { try { server = ServerSocket(port, 1, InetAddress.getLoopbackAddress()); while (!Thread.currentThread().isInterrupted) { client = server!!.accept(); output = DataOutputStream(BufferedOutputStream(client!!.getOutputStream())); sendHandshake(); readControls(client!!) } } catch (_: IOException) { } finally { output = null } }
    private fun sendHandshake() = send(Protocol.CONTROL, 0, 0, "{\"op\":\"hello\",\"version\":1,\"codec\":\"avc\",\"width\":1280,\"height\":720,\"fps\":30}".toByteArray())
    private fun readControls(socket: Socket) { val input = DataInputStream(BufferedInputStream(socket.getInputStream())); while (socket.isConnected) { val p = Protocol.read(input) ?: break; if (p.type == Protocol.CONTROL) sendBroadcast(Intent("com.wiredcam.CONTROL").putExtra("json", String(p.payload))) }; try { socket.close() } catch (_: IOException) {}; output = null }
    fun send(type: Int, flags: Int, pts: Long, bytes: ByteArray) { synchronized(this) { try { output?.let { Protocol.write(it, type, flags, pts, bytes) } } catch (_: IOException) { output = null } } }
    override fun onDestroy() { instance = null; try { client?.close(); server?.close() } catch (_: IOException) {}; wakeLock?.let { if (it.isHeld) it.release() }; worker.shutdownNow(); super.onDestroy() }
}
