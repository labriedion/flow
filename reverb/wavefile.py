"""Read and write 16-bit PCM WAV files with the standard-library `wave` module.

Audio on disk is integers; the reverb math wants floats. These helpers bridge
the two, normalising to the conventional `[-1, 1]` range on the way in and
clipping back to signed 16-bit on the way out.

    >>> from reverb.wavefile import write_wav, read_wav
    >>> write_wav("/tmp/tone.wav", [[0.0, 0.5, -0.5, 1.0]], 22050)
    >>> channels, rate = read_wav("/tmp/tone.wav")
    >>> rate
    22050
    >>> len(channels)              # mono -> one channel
    1

Mono is `[channel]`; stereo is `[left, right]`. Only 16-bit PCM is handled —
the format the reverb writes — and anything else raises a clear error. Standard
library only.
"""

from __future__ import annotations

import wave
from array import array
from collections.abc import Sequence

_MAX_INT16 = 32767
_MIN_INT16 = -32768


def read_wav(path: str) -> tuple[list[array], int]:
    """Read a 16-bit PCM WAV file.

    Returns `(channels, sample_rate)` where `channels` is a list of
    `array('d')`, one per channel, with samples normalised to `[-1, 1]`. Mono
    files give one channel, stereo two. Raises `ValueError` for unsupported
    formats (non-16-bit, or a file `wave` cannot parse).
    """
    try:
        with wave.open(path, "rb") as w:
            n_channels = w.getnchannels()
            sample_width = w.getsampwidth()
            sample_rate = w.getframerate()
            n_frames = w.getnframes()
            raw = w.readframes(n_frames)
    except wave.Error as exc:
        raise ValueError(f"not a readable WAV file: {exc}") from exc
    except EOFError as exc:
        raise ValueError("WAV file is empty or truncated") from exc

    if sample_width != 2:
        raise ValueError(
            f"only 16-bit PCM WAV is supported, got {sample_width * 8}-bit"
        )

    interleaved = array("h")              # signed 16-bit
    interleaved.frombytes(raw)
    # WAV stores little-endian; swap if this machine is big-endian.
    import sys
    if sys.byteorder == "big":
        interleaved.byteswap()

    scale = 1.0 / 32768.0
    channels = [array("d") for _ in range(n_channels)]
    for i, value in enumerate(interleaved):
        channels[i % n_channels].append(value * scale)
    return channels, sample_rate


def write_wav(path: str, channels: Sequence[Sequence[float]], sample_rate: int) -> None:
    """Write channels of floats in `[-1, 1]` to a 16-bit PCM WAV file.

    `channels` is `[mono]` or `[left, right]`; samples outside `[-1, 1]` are
    clipped rather than wrapped. Channels of unequal length are zero-padded to
    the longest.
    """
    if not channels:
        raise ValueError("need at least one channel to write")
    if sample_rate <= 0:
        raise ValueError(f"sample_rate must be positive, got {sample_rate!r}")

    n_channels = len(channels)
    n_frames = max((len(ch) for ch in channels), default=0)

    interleaved = array("h", bytes(2 * n_frames * n_channels))
    k = 0
    for frame in range(n_frames):
        for ch in channels:
            sample = ch[frame] if frame < len(ch) else 0.0
            # Scale to int16 and clip.
            value = int(round(sample * 32768.0))
            if value > _MAX_INT16:
                value = _MAX_INT16
            elif value < _MIN_INT16:
                value = _MIN_INT16
            interleaved[k] = value
            k += 1

    import sys
    if sys.byteorder == "big":
        interleaved.byteswap()

    with wave.open(path, "wb") as w:
        w.setnchannels(n_channels)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(interleaved.tobytes())
