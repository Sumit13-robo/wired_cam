package com.wiredcam

import java.io.DataInputStream
import java.io.DataOutputStream

/** Wire format: type(1), flags(1), ptsUs(8), payload length(4), payload. */
object Protocol {
    const val VERSION = 1
    const val VIDEO_CONFIG = 0x01; const val VIDEO_FRAME = 0x02; const val CONTROL = 0x10
    const val KEYFRAME = 1
    fun write(out: DataOutputStream, type: Int, flags: Int, ptsUs: Long, payload: ByteArray) {
        out.writeByte(type); out.writeByte(flags); out.writeLong(ptsUs); out.writeInt(payload.size); out.write(payload); out.flush()
    }
    data class Packet(val type: Int, val flags: Int, val ptsUs: Long, val payload: ByteArray)
    fun read(input: DataInputStream): Packet? = try {
        val type = input.readUnsignedByte(); val flags = input.readUnsignedByte(); val pts = input.readLong(); val length = input.readInt()
        require(length in 0..(16 * 1024 * 1024)) { "Invalid packet length" }
        Packet(type, flags, pts, ByteArray(length).also(input::readFully))
    } catch (_: Exception) { null }
}
