import sys
import os
import threading
import random

sys.path.append(os.path.dirname(__file__))

import winrt.windows.media.playback as playback
import winrt.windows.media.core as core
from winrt.windows.foundation import Uri
import logHandler


class AudioTrack:
    def __init__(self, track_id, path, volume, is_random):
        self.track_id = track_id
        self.path = path
        self.volume = max(0.0, min(1.0, volume / 100.0))
        self.is_random = is_random
        self.player = playback.MediaPlayer()
        self.timer = None

        self._media_ended_token = None
        self._media_failed_token = None

        self._setup_player()

    def _setup_player(self):
        try:
            uri_string = "file:///" + self.path.replace("\\", "/")
            self.player.source = core.MediaSource.create_from_uri(Uri(uri_string))
            self.player.volume = self.volume
            self.player.is_looping_enabled = not self.is_random

            self._media_ended_token = self.player.add_media_ended(self._on_media_ended)
            self._media_failed_token = self.player.add_media_failed(self._on_media_failed)
        except Exception as e:
            logHandler.log.error(
                f"WhiteNoise: Failed to setup media player for {self.path}. Error: {e}"
            )

    def _on_media_ended(self, sender, args):
        if self.is_random:
            delay = random.uniform(3.0, 30.0)
            self.timer = threading.Timer(delay, self._play_internal)
            self.timer.daemon = True
            self.timer.start()

    def _on_media_failed(self, sender, args):
        logHandler.log.error(
            f"WhiteNoise: MediaFailed for track {self.track_id}. Path: {self.path}"
        )

    def _play_internal(self):
        try:
            self.player.play()
        except Exception as e:
            logHandler.log.error(f"WhiteNoise: Playback error - {e}")

    def play(self):
        self._cancel_timer()
        self._play_internal()

    def stop(self):
        self._cancel_timer()
        try:
            self.player.pause()
        except Exception:
            pass

    def set_mute(self, muted):
        self.player.is_muted = muted

    def _cancel_timer(self):
        if self.timer and self.timer.is_alive():
            self.timer.cancel()
        self.timer = None

    def cleanup(self):
        self.stop()
        if self._media_ended_token:
            self.player.remove_media_ended(self._media_ended_token)
        if self._media_failed_token:
            self.player.remove_media_failed(self._media_failed_token)


class AudioEngine:
    def __init__(self):
        self.tracks = {}
        self.is_muted = False

    def update_track(self, track_id, path, volume, enabled, is_random):
        if track_id in self.tracks:
            self.tracks[track_id].cleanup()
            del self.tracks[track_id]

        if enabled:
            try:
                track = AudioTrack(track_id, path, volume, is_random)
                track.set_mute(self.is_muted)
                self.tracks[track_id] = track
                track.play()
            except Exception as e:
                logHandler.log.error(
                    f"WhiteNoise: Error updating track {track_id}: {e}"
                )

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        for track in self.tracks.values():
            track.set_mute(self.is_muted)
        return self.is_muted

    def shutdown(self):
        for track in list(self.tracks.values()):
            track.cleanup()
        self.tracks.clear()