"""简单音效管理：用 numpy 合成短促 beep，失败时静默运行。

不依赖任何外部音频文件。若 pygame.mixer 或 numpy 不可用，所有方法均为空操作。
"""

from __future__ import annotations

import pygame

try:
    import numpy as np
    _HAS_NUMPY = True
except Exception:
    _HAS_NUMPY = False


class SoundManager:
    def __init__(self) -> None:
        self.enabled = False
        self.sounds = {}
        if not _HAS_NUMPY:
            return
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
            pygame.mixer.init()
            self.enabled = True
        except Exception:
            self.enabled = False
            return
        try:
            self.sounds["fly"] = self._beep(880, 0.12, 0.35, decay=9)
            self.sounds["collide"] = self._beep(180, 0.18, 0.45, decay=10)
            self.sounds["win"] = self._chord([523, 659, 784], 0.5, 0.35)
            self.sounds["lose"] = self._beep(120, 0.5, 0.4, decay=4)
            self.sounds["click"] = self._beep(660, 0.05, 0.25, decay=20)
        except Exception:
            self.enabled = False

    def _beep(self, freq: float, dur: float, vol: float, decay: float = 8.0):
        sr = 44100
        n = int(dur * sr)
        t = np.linspace(0, dur, n, endpoint=False)
        wave = vol * np.sin(2 * np.pi * freq * t) * np.exp(-t * decay)
        stereo = np.column_stack([wave, wave])
        arr = (stereo * 32767).astype(np.int16)
        return pygame.sndarray.make_sound(arr)

    def _chord(self, freqs, dur: float, vol: float):
        sr = 44100
        n = int(dur * sr)
        t = np.linspace(0, dur, n, endpoint=False)
        wave = np.zeros(n)
        for f in freqs:
            wave += np.sin(2 * np.pi * f * t)
        wave = vol * wave / len(freqs) * np.exp(-t * 4)
        stereo = np.column_stack([wave, wave])
        arr = (stereo * 32767).astype(np.int16)
        return pygame.sndarray.make_sound(arr)

    def play(self, name: str) -> None:
        if not self.enabled:
            return
        s = self.sounds.get(name)
        if s is not None:
            try:
                s.play()
            except Exception:
                pass

    def fly(self) -> None:
        self.play("fly")

    def collide(self) -> None:
        self.play("collide")

    def win(self) -> None:
        self.play("win")

    def lose(self) -> None:
        self.play("lose")

    def click(self) -> None:
        self.play("click")
