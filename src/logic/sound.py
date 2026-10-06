"""抽選演出用の短い効果音を管理する。"""

from pathlib import Path
from time import monotonic

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QSoundEffect


class SoundManager:
    """WAV効果音の再生、音量、ON/OFFを一元管理する。"""

    _FILES = {
        "candidate": "candidate_tick.wav",
        "flash": "winner_flash.wav",
        "winner": "winner_fanfare.wav",
        "stop": "stopbutton.wav",
        "test": "volume_test.wav",
    }

    def __init__(self, project_root: Path):
        self._audio_dir = project_root / "assets" / "sounds"
        self.enabled = True
        self.volume = 0.7
        self._players: dict[str, tuple[QMediaPlayer, QAudioOutput]] = {}
        self._loaded: set[str] = set()
        self._last_play_at: dict[str, float] = {}
        self._minimum_interval = {"candidate": 0.070}
        self._candidate_effect: QSoundEffect | None = None
        candidate_path = self._audio_dir / self._FILES["candidate"]
        if candidate_path.exists():
            # 候補者音は短音のため、QMediaPlayerではなく事前ロード型を使う。
            self._candidate_effect = QSoundEffect()
            self._candidate_effect.setVolume(self.volume)
            self._candidate_effect.setSource(QUrl.fromLocalFile(str(candidate_path)))

        # 停止音・当選音・テスト音もイベント発生時に読み込まないよう事前ロードする。
        for name, filename in self._FILES.items():
            if name == "candidate":
                continue
            path = self._audio_dir / filename
            if not path.exists():
                continue
            player = QMediaPlayer()
            output = QAudioOutput()
            output.setVolume(self.volume)
            player.setAudioOutput(output)
            player.setSource(QUrl.fromLocalFile(str(path)))
            self._players[name] = (player, output)
            self._loaded.add(name)

    def play(self, name: str):
        """指定した効果音を再生する。音量OFF中は再生しない。"""
        if not self.enabled or name not in self._FILES:
            return

        now = monotonic()
        if now - self._last_play_at.get(name, 0.0) < self._minimum_interval.get(name, 0.0):
            return
        self._last_play_at[name] = now

        if name == "candidate" and self._candidate_effect is not None:
            self._candidate_effect.setVolume(self.volume)
            self._candidate_effect.play()
            return

        path = self._audio_dir / self._FILES[name]
        if not path.exists():
            return

        player, output = self._players.setdefault(
            name,
            (QMediaPlayer(), QAudioOutput()),
        )
        output.setVolume(self.volume)
        player.setAudioOutput(output)
        # MP3を候補者切替のたびに再読み込みするとデコード待ちが発生するため、
        # 音源は最初の一度だけ読み込み、2回目以降は再生位置だけ戻す。
        if name not in self._loaded:
            player.setSource(QUrl.fromLocalFile(str(path)))
            self._loaded.add(name)
        else:
            player.stop()
            player.setPosition(0)
        player.play()

    def set_enabled(self, enabled: bool):
        """音量状態を切り替え、OFF時は再生中の音をすべて停止する。"""
        self.enabled = enabled
        if not enabled:
            self.stop_all()

    def set_volume(self, volume: float):
        """0.0～1.0の範囲で音量を設定する。"""
        self.volume = max(0.0, min(1.0, float(volume)))
        for _, output in self._players.values():
            output.setVolume(self.volume)
        if self._candidate_effect is not None:
            self._candidate_effect.setVolume(self.volume)

    def stop_all(self):
        """すべての再生中効果音を停止する。"""
        for player, _ in self._players.values():
            player.stop()
        if self._candidate_effect is not None:
            self._candidate_effect.stop()
