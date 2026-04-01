import wx
import os
import addonHandler
import winUser
from .aetheris_manager import AetherisManager

addonHandler.initTranslation()


class AetherisGUI(wx.Dialog):
    def __init__(self, parent, engine):
        super().__init__(
            parent,
            title=_("Aetheris White Noise Settings"),
            size=(550, 650),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )

        self.manager = AetherisManager(engine)
        self.categories = []
        self.audio_files = []

        self._init_ui()
        self._refresh_categories_ui()

        self.CenterOnParent()
        self.Bind(wx.EVT_SHOW, self._on_show)

    def _init_ui(self):
        panel = wx.Panel(self)
        main = wx.BoxSizer(wx.VERTICAL)

        main.Add(wx.StaticText(panel, label=_("Base &Directory:")), 0, wx.LEFT | wx.TOP, 10)
        dir_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.txtDir = wx.TextCtrl(panel, value=self.manager.base_dir, style=wx.TE_READONLY)
        self.btnBrowse = wx.Button(panel, label=_("&Browse..."))
        dir_sizer.Add(self.txtDir, 1, wx.ALL | wx.CENTER, 5)
        dir_sizer.Add(self.btnBrowse, 0, wx.ALL | wx.CENTER, 5)
        main.Add(dir_sizer, 0, wx.EXPAND)

        main.Add(wx.StaticText(panel, label=_("&Category:")), 0, wx.LEFT | wx.TOP, 10)
        self.comboCategory = wx.ComboBox(panel, style=wx.CB_READONLY)
        main.Add(self.comboCategory, 0, wx.EXPAND | wx.ALL, 10)

        main.Add(wx.StaticText(panel, label=_("&Audio Files:")), 0, wx.LEFT, 10)
        self.listAudio = wx.ListBox(panel, style=wx.LB_SINGLE)
        main.Add(self.listAudio, 1, wx.EXPAND | wx.ALL, 10)

        box = wx.StaticBox(panel, label=_("Track Controls"))
        ctrl = wx.StaticBoxSizer(box, wx.VERTICAL)

        self.checkEnabled = wx.CheckBox(box, label=_("&Enable Track"))
        self.checkRandom = wx.CheckBox(box, label=_("R&andom Trigger"))
        self.sliderVol = wx.Slider(box, value=50, minValue=0, maxValue=100,
                                   style=wx.SL_HORIZONTAL | wx.SL_LABELS)

        ctrl.Add(self.checkEnabled, 0, wx.ALL, 5)
        ctrl.Add(self.checkRandom, 0, wx.ALL, 5)
        ctrl.Add(self.sliderVol, 0, wx.EXPAND | wx.ALL, 5)
        main.Add(ctrl, 0, wx.EXPAND | wx.ALL, 10)

        self.lblStatus = wx.TextCtrl(
            panel,
            style=wx.TE_READONLY | wx.BORDER_NONE | wx.TE_MULTILINE | wx.TE_NO_VSCROLL
        )
        main.Add(self.lblStatus, 0, wx.EXPAND | wx.ALL, 10)

        btns = wx.StdDialogButtonSizer()
        self.btnOK = wx.Button(panel, id=wx.ID_OK, label=_("&OK"))
        self.btnCancel = wx.Button(panel, id=wx.ID_CANCEL, label=_("C&ancel"))
        self.btnApply = wx.Button(panel, id=wx.ID_APPLY, label=_("&Apply"))

        btns.AddButton(self.btnOK)
        btns.AddButton(self.btnCancel)
        btns.AddButton(self.btnApply)
        self.btnOK.SetDefault()
        btns.Realize()
        main.Add(btns, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(main)

        self.btnBrowse.Bind(wx.EVT_BUTTON, self.on_browse)
        self.comboCategory.Bind(wx.EVT_COMBOBOX, self.on_category_change)
        self.listAudio.Bind(wx.EVT_LISTBOX, self.on_audio_select)

        for ctrl in (self.checkEnabled, self.checkRandom):
            ctrl.Bind(wx.EVT_CHECKBOX, self.on_control_change)
        self.sliderVol.Bind(wx.EVT_SLIDER, self.on_control_change)

        self.Bind(wx.EVT_BUTTON, self.on_apply, id=wx.ID_APPLY)
        self.Bind(wx.EVT_BUTTON, self.on_ok, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.on_cancel, id=wx.ID_CANCEL)

        self._update_controls_state(False)
        self._update_status_ui()

    def _on_show(self, event):
        if event.IsShown():
            wx.CallLater(50, self._force_focus_loop, 0)
        event.Skip()

    def _force_focus_loop(self, attempt):
        try:
            my_hwnd = self.GetHandle()
            fg = winUser.getForegroundWindow()

            if fg != my_hwnd:
                self.Raise()
                self.SetFocus()
                if attempt < 10:
                    wx.CallLater(50, self._force_focus_loop, attempt + 1)
                return

            if self.categories:
                self.comboCategory.SetFocus()
            else:
                self.btnBrowse.SetFocus()

        except Exception:
            pass

    def _refresh_categories_ui(self):
        self.categories = self.manager.get_categories()
        self.comboCategory.Set(self.categories)

        if self.categories:
            self.comboCategory.SetSelection(0)
            self._refresh_audio_ui()
        else:
            self.listAudio.Set([])
            self._update_controls_state(False)

    def _refresh_audio_ui(self):
        sel = self.comboCategory.GetSelection()
        if sel == -1:
            self.listAudio.Set([])
            return

        category = self.categories[sel]
        self.audio_files = self.manager.get_audio_files(category)
        self.listAudio.Set(self.audio_files)
        self._update_controls_state(False)

    def on_browse(self, event):
        with wx.DirDialog(self, _("Select Audio Directory"), defaultPath=self.manager.base_dir) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.manager.base_dir = dlg.GetPath()
                self.txtDir.SetValue(self.manager.base_dir)
                self._refresh_categories_ui()

    def on_category_change(self, event):
        self._refresh_audio_ui()

    def on_audio_select(self, event):
        path = self._get_current_rel_path()
        if not path:
            return

        self._update_controls_state(True)

        data = self.manager.active_tracks.get(path, {"volume": 50, "is_random": False})
        self.checkEnabled.SetValue(path in self.manager.active_tracks)
        self.checkRandom.SetValue(data.get("is_random", False))
        self.sliderVol.SetValue(data.get("volume", 50))

    def on_control_change(self, event):
        path = self._get_current_rel_path()
        if not path:
            return

        if self.checkEnabled.GetValue():
            self.manager.active_tracks[path] = {
                "volume": self.sliderVol.GetValue(),
                "is_random": self.checkRandom.GetValue()
            }
        else:
            self.manager.active_tracks.pop(path, None)

        self._update_status_ui()

    def on_apply(self, event):
        self.manager.sync_to_engine()
        self.manager.save_config(self.txtDir.GetValue())
        self._update_status_ui()

    def on_ok(self, event):
        self.on_apply(None)
        self.EndModal(wx.ID_OK)

    def on_cancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def _get_current_rel_path(self):
        c = self.comboCategory.GetSelection()
        a = self.listAudio.GetSelection()
        if c == -1 or a == -1:
            return None
        return os.path.join(self.categories[c], self.audio_files[a])

    def _update_status_ui(self):
        tracks = self.manager.active_tracks
        if not tracks:
            self.lblStatus.SetValue(_("Active Tracks: None"))
        else:
            names = [os.path.basename(p) for p in tracks.keys()]
            self.lblStatus.SetValue(_("Active Tracks: ") + ", ".join(names))

    def _update_controls_state(self, enabled):
        self.checkEnabled.Enable(enabled)
        self.checkRandom.Enable(enabled)
        self.sliderVol.Enable(enabled)