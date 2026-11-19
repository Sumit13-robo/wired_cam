# WiredCam protocol v1

The Android server listens on TCP port `5555` on the device loopback interface. Desktop programs normally reach it through `adb forward tcp:5555 tcp:5555`; USB tethering may instead use the phone's tethering address.

Every packet has this network-byte-order header followed immediately by its payload:

| bytes | field | meaning |
|---:|---|---|
| 1 | type | `01` AVC configuration, `02` AVC access unit, `03` AAC configuration, `04` AAC access unit, `10` UTF-8 JSON control |
| 1 | flags | bit 0 is set for a video keyframe |
| 8 | PTS | signed presentation timestamp in microseconds |
| 4 | length | unsigned payload byte count, maximum 16 MiB |

The server sends a `0x10` message first: `{"op":"hello","version":1,"codec":"avc","width":1280,"height":720,"fps":30}`. AVC config payloads are Annex-B SPS followed by PPS. The server sends them before every keyframe so a newly connected receiver can decode immediately. AVC frame payloads are Annex-B H.264 access units.

Desktop-to-phone controls are `0x10` JSON messages: `{"op":"camera","lens":"front"}`, `{"op":"flash","enabled":true}`, `{"op":"bitrate","bps":4000000}`, `{"op":"resolution","width":1280,"height":720}`, and `{"op":"keyframe"}`. Unknown controls must be ignored for forward compatibility.

Audio types are reserved for the second milestone; version 1 currently sends video only.
