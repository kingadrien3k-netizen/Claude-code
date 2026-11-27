# Finally Listened (album)
Artist: Babylyst · 7 tracks · about 13 minutes

| # | Track | Length | Tempo | Mastering fixes |
|---|---|---|---|---|
| 1 | Lost | 1:31 | 150 | tamed the extra-deep sub, more bass body, clarity and air |
| 2 | Hard Headed | 2:00 | 165 | tightened the sub, cleared low-mid mud, clarity and air |
| 3 | Rapping | 1:55 | 150 | added low-end warmth, cut boxy mids, clarity and air |
| 4 | Breadwinner | 1:37 | 166 | cut boxiness around 700 Hz, clarity and air |
| 5 | Charts | 1:42 | 120 | filled the hollow bass body, tamed the huge sub, clarity and air |
| 6 | World4U | 2:18 | 160 | added low-end warmth, cut muddy mids, clarity and air |
| 7 | Turning Over | 2:03 | 150 | added low-end warmth, cut very boxy mids, clarity and air |

All tracks: glue compression, matched loudness (about -11 LUFS, 2-3 dB louder than before), clean peaks (no clipping, true peak at or below -0.5 dBTP), trimmed tail silence, tagged as album "Finally Listened".
Order: the story goes from struggle (Lost, Hard Headed) to grind (Rapping, Breadwinner) to success (Charts, World4U) to growth (Turning Over).

## v2 remix (vocals forward), Nov 25
Feedback: "my voice can't be heard." Split every song into vocals and beat with Demucs (htdemucs), then remixed:
- Vocal chain: high-pass 90 Hz, -2 dB at 300 Hz (mud), -2 dB at 800 Hz (box), +4 dB at 3.5 kHz (presence), +3 dB air above 10 kHz, de-esser, 3:1 compression.
- Beat: same per-song bass/mid fixes as v1, plus a pocket carved for the voice (-3 dB at 2.8 kHz, -1.5 dB at 900 Hz).
- Balance: vocal set 7 LU over the beat on every song (before: Lost +0.9, Hard Headed +2.4, Rapping +4.4, Breadwinner +2.0, Charts +2.5, World4U +4.1, Turning Over +3.1, measured on the raw split stems).
- Master: glue compression, about -11 LUFS on all, true peak at or below -0.7 dBTP, no clipping.

## v3 remix (blended), Nov 25
Feedback on v2: "it don't sound mixed at all" (the vocal sounded pasted on top). New approach:
- Base = the ORIGINAL full song (keeps it glued), with the per-song bass/mid fixes.
- Plus a cleaned vocal layer (split with Demucs) 9 dB under the existing vocal: high-pass 100 Hz, mud/box cuts, +2.5 dB at 3 kHz, de-esser, 4:1 compression, soft saturation.
- Space: tempo-synced 1/8-note echo plus a short room reverb on a send.
- The beat ducks gently (1.6:1) only when the vocal plays. No static EQ hole.
- Bus glue (1.8:1), soft clip, master to about -10.6 LUFS, true peak at or below -0.3 dBTP.
- Result (measured): vocal over beat went from +0.9 to +5.6 on Lost, +2.0 to +3.4 on Breadwinner, +3.1 to +5.4 on Turning Over.

## FINAL (Nov 25): original songs, untouched
I asked to stop editing my vocals and not mix anything. The official album is my ORIGINAL uploaded songs, with the audio byte-for-byte unchanged (verified by audio checksum). Only the album, artist and track-number tags were added. The v1, v2 and v3 masters are not used.
Rule going forward: don't process, EQ, or remix my vocals or songs unless I ask.

## v4 ALBUM MASTER (Nov 27), requested: same loudness, even within songs, studio sound
Mastered the original full songs only. No vocal splitting or vocal edits.
Chain: high-pass 28 Hz, per-song tone fix (same as v1 but gentler), +1.5 dB at 3 kHz, +2 dB air above 9 kHz, slow section leveling (dynaudnorm 1.5 s frames), two-stage glue compression (1.8:1, then 3:1 peak control), limiter, exact trim per song.
Result: every song at exactly -11.0 LUFS, true peak -0.3 to -1.5 dBTP, no clipping.
Loudness range (LRA) before -> after: Lost 4.1->1.9, Hard Headed 1.3->1.1, Rapping 3.7->2.6, Breadwinner 0.9->0.9, Charts 6.0->1.6, World4U 2.8->2.4, Turning Over 4.3->3.6.
Delivered as WAV (for DistroKid) and 320 kbps MP3.

## v5 (Nov 27): reference match to "Please Don't Judge Me"
Tone-matched the original song to the Fatt Mack reference (1/3-octave curve, ±6 dB max, level-neutral), then light glue compression and a limiter to about -11 LUFS. The test on Lost was liked ("this good"), except the bass was too high, so the sub boost under 150 Hz was cut in half (about +3 dB at 50 Hz instead of +6). Nothing else changed. If approved, apply the same to all 7 songs.

## FINAL MASTER (Nov 27): approved method
Applied the v5 reference match (Please Don't Judge Me, bass boost x0.5) to all 7 original songs, then glue compression, limiter at 0.72, trim. Result: -11.3 to -11.7 LUFS, true peak -0.4 to -1.8 dBTP, no clipping. Delivered as WAV (release) and 320 kbps MP3.
To recreate: match2.py with BASS_SCALE=0.5 against the reference, then the same chain.
