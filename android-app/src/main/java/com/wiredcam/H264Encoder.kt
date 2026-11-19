package com.wiredcam

import android.media.*
import androidx.camera.core.ImageProxy
import java.nio.ByteBuffer

/** CameraX supplies YUV frames; this uses the platform hardware AVC encoder. */
class H264Encoder(private val width: Int, private val height: Int, private val fps: Int, private val bitrate: Int) {
    private val codec = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
    private val info = MediaCodec.BufferInfo(); private var started = false; private var config = ByteArray(0)
    fun start() {
        val f = MediaFormat.createVideoFormat(MediaFormat.MIMETYPE_VIDEO_AVC, width, height).apply {
            setInteger(MediaFormat.KEY_BIT_RATE, bitrate); setInteger(MediaFormat.KEY_FRAME_RATE, fps)
            setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1); setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Flexible)
            setInteger(MediaFormat.KEY_BITRATE_MODE, MediaCodecInfo.EncoderCapabilities.BITRATE_MODE_CBR)
            if (android.os.Build.VERSION.SDK_INT >= 30) setInteger(MediaFormat.KEY_LOW_LATENCY, 1)
        }
        codec.configure(f, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE); codec.start(); started = true
    }
    fun offer(image: ImageProxy) { if (!started) { image.close(); return }; try { val index = codec.dequeueInputBuffer(0); if (index >= 0) { val input = codec.getInputBuffer(index)!!; input.clear(); image.toNv12(input, width, height); codec.queueInputBuffer(index, 0, width * height * 3 / 2, image.imageInfo.timestamp / 1000, 0) }; drain() } catch (_: Exception) { } finally { image.close() } }
    private fun drain() { while (true) { val index = codec.dequeueOutputBuffer(info, 0); when { index >= 0 -> { val b = codec.getOutputBuffer(index)!!; val bytes = ByteArray(info.size); b.position(info.offset); b.limit(info.offset + info.size); b.get(bytes); val key = info.flags and MediaCodec.BUFFER_FLAG_KEY_FRAME != 0; val codecConfig = info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG != 0; if (key && config.isNotEmpty()) StreamService.instance?.send(Protocol.VIDEO_CONFIG, Protocol.KEYFRAME, info.presentationTimeUs, config); if (info.size > 0 && !codecConfig) StreamService.instance?.send(Protocol.VIDEO_FRAME, if (key) Protocol.KEYFRAME else 0, info.presentationTimeUs, bytes); codec.releaseOutputBuffer(index, false) }
                index == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> { val f = codec.outputFormat; val sps = f.getByteBuffer("csd-0")?.copy() ?: ByteArray(0); val pps = f.getByteBuffer("csd-1")?.copy() ?: ByteArray(0); config = sps + pps }
                else -> return }
        } }
    fun requestKeyFrame() { codec.setParameters(android.os.Bundle().apply { putInt(MediaCodec.PARAMETER_KEY_REQUEST_SYNC_FRAME, 0) }) }
    fun stop() { if (started) try { codec.stop(); codec.release() } catch (_: Exception) {}; started = false }
    private fun ByteBuffer.copy(): ByteArray { val d = duplicate(); return ByteArray(d.remaining()).also(d::get) }
}

private fun ImageProxy.toNv12(out: ByteBuffer, targetW: Int, targetH: Int) {
    require(width == targetW && height == targetH) { "Camera output must match encoder size" }
    val y = planes[0]; val u = planes[1]; val v = planes[2]
    for (row in 0 until height) for (col in 0 until width) out.put(y.buffer.get(row * y.rowStride + col * y.pixelStride))
    for (row in 0 until height / 2) for (col in 0 until width / 2) { out.put(u.buffer.get(row * u.rowStride + col * u.pixelStride)); out.put(v.buffer.get(row * v.rowStride + col * v.pixelStride)) }
}
