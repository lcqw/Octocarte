# Client compatibility notes

The user reported successful NAS end-to-end playback through Wavio, with roughly
1–2 seconds to start temporary YouTube playback and immediate album submission
visible in ALACarte. This is manual acceptance, not an instrumented latency result.

During the same trial, queued ALAC tracks showed M4A-to-OGA conversion in Wavio.
Disabling prefetching and clearing prefetched tracks resolved the unwanted
conversion. Wavio's inspected Android code treats high-bitrate MP4-container
tracks as ALAC and requests Opus for prefetching, even when original streaming is
selected. The current track is excluded from that prefetch window. See the
[inspected source](https://github.com/Joel-Mercier/wavio/blob/2e826459fbe6d8574ba188d6041d11dd57fbda2b/apps/mobile/services/backend/streaming.ts#L211-L315).

Navidrome web playback was reported working through lossless ALAC-to-FLAC
conversion. This does not establish direct ALAC decoding support in every client.
Navic has also been confirmed working with Octocarte in a subsequent test.

ALACarte can optionally convert acquired ALAC to FLAC using its own quality
setting. Both are lossless formats. Lower compressed bitrate after that conversion
alone is not evidence of reduced audio quality. Octocarte leaves this choice in
ALACarte and does not override it. Changing the preference does not automatically
rewrite albums already present in the library.
