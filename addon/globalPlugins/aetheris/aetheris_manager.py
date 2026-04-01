import os
from typing import Dict, List
from logHandler import log
import config


class AetherisManager:
    SUPPORTED_EXTENSIONS = ('.wav', '.mp3', '.ogg', '.flac')

    def __init__(self, engine):
        self.engine = engine

        if "Aetheris" not in config.conf:
            config.conf["Aetheris"] = {}

        self.conf_sect = config.conf["Aetheris"]
        self.base_dir: str = self.conf_sect.get("base_dir", "")
        self.active_tracks: Dict[str, dict] = self._load_active_tracks()

        if not self.base_dir or not os.path.isdir(self.base_dir):
            self.active_tracks = {}

    def _load_active_tracks(self) -> Dict[str, dict]:
        saved = self.conf_sect.get("active_tracks", {})
        return {
            path: {
                "volume": int(data.get("volume", 50)),
                "is_random": bool(data.get("is_random", False)),
            }
            for path, data in saved.items()
        }

    def get_categories(self) -> List[str]:
        if not self.base_dir or not os.path.isdir(self.base_dir):
            return []
        try:
            return sorted(
                d for d in os.listdir(self.base_dir)
                if os.path.isdir(os.path.join(self.base_dir, d))
            )
        except OSError as e:
            log.error(f"Aetheris: Failed to list categories: {e}")
            return []

    def get_audio_files(self, category_name: str) -> List[str]:
        cat_path = os.path.join(self.base_dir, category_name)
        try:
            return sorted(
                f for f in os.listdir(cat_path)
                if f.lower().endswith(self.SUPPORTED_EXTENSIONS)
            )
        except OSError:
            return []

    def _cleanup_missing_files(self):
        """自动清理 active_tracks 中不存在的文件"""
        missing = [
            p for p in list(self.active_tracks.keys())
            if not os.path.isfile(os.path.join(self.base_dir, p))
        ]
        for p in missing:
            del self.active_tracks[p]

    def sync_to_engine(self) -> None:
        if not self.base_dir or not os.path.isdir(self.base_dir):
            for track_id in list(self.engine.tracks.keys()):
                self.engine.update_track(track_id, "", 0, False, False)
            self.active_tracks.clear()
            return

        self._cleanup_missing_files()

        for rel_path, data in self.active_tracks.items():
            full_path = os.path.join(self.base_dir, rel_path)
            if not os.path.isfile(full_path):
                continue
            self.engine.update_track(
                rel_path,
                full_path,
                data["volume"],
                True,
                data["is_random"],
            )

        for track_id in list(self.engine.tracks.keys()):
            if track_id not in self.active_tracks:
                self.engine.update_track(track_id, "", 0, False, False)

    def save_config(self, current_dir: str) -> None:
        if current_dir != self.base_dir:
            self.active_tracks.clear()

        self.base_dir = current_dir
        self.conf_sect["base_dir"] = current_dir
        self.conf_sect["active_tracks"] = dict(self.active_tracks)
        config.conf.save()