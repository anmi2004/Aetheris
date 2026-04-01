import os
import wx
import globalPluginHandler
import config
import ui
import gui
import addonHandler
from logHandler import log

from .audio_engine import AudioEngine
from .plugin_gui import AetherisGUI
from .aetheris_manager import AetherisManager

addonHandler.initTranslation()

CONF_SPEC = {
    "Aetheris": {
        "base_dir": "string(default='')",
        "auto_play_on_startup": "boolean(default=False)",
        "[[active_tracks]]": {
            "__many__": {
                "volume": "integer(default=50)",
                "is_random": "boolean(default=False)"
            }
        },
    }
}

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = _("Aetheris")

    def __init__(self):
        super().__init__()
        config.conf.spec.update(CONF_SPEC)

        self.engine = AudioEngine()
        self.manager = AetherisManager(self.engine)

        wx.CallAfter(self._restore_playback)

    def _restore_playback(self):
        auto_play = config.conf["Aetheris"].get("auto_play_on_startup", False)
        if auto_play and self.manager.base_dir:
            self.manager.sync_to_engine()

    def script_showSettings(self, gesture):
        dlg = AetherisGUI(gui.mainFrame, self.engine)
        gui.runScriptModalDialog(dlg)

    script_showSettings.__doc__ = _("Open Aetheris settings dialog")

    def script_toggleAetheris(self, gesture):
        if self.engine.tracks:
            self.engine.shutdown()
            ui.message(_("Aetheris stopped"))
        else:
            if not self.manager.base_dir:
                ui.message(_("Aetheris: Please set base directory in settings"))
                return
            self.manager.sync_to_engine()
            ui.message(_("Aetheris started"))

    script_toggleAetheris.__doc__ = _("Toggle Aetheris playback on or off")

    def terminate(self):
        if hasattr(self, 'engine'):
            self.engine.shutdown()
        super().terminate()

    __gestures = {
        "kb:NVDA+shift+w": "showSettings",
        "kb:NVDA+shift+p": "toggleAetheris",
    }