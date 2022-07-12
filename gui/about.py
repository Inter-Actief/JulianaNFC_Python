import wx
import wx.adv

from juliana import resource_path

class AboutDialog(wx.Dialog):
    def __init__(self, *args, **kwargs):
        from juliana import APP_SUPPORT, APP_LINK
        kwargs["style"] = kwargs.get("style", 0) | wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwargs)
        self.SetSize((400, 350))
        self.SetIcon(wx.Icon(resource_path("resources/main.png"), type=wx.BITMAP_TYPE_PNG))
        self.hyperlink_2 = wx.adv.HyperlinkCtrl(self, wx.ID_ANY, APP_LINK, APP_LINK, style=wx.adv.HL_ALIGN_CENTRE)
        self.hyperlink_3 = wx.adv.HyperlinkCtrl(self, wx.ID_ANY, APP_SUPPORT, f"mailto://{APP_SUPPORT}", style=wx.adv.HL_ALIGN_CENTRE)
        self.button_2 = wx.Button(self, wx.ID_OK, "")

        self.__set_properties()
        self.__do_layout()

    def __set_properties(self):
        self.SetTitle(f"About JulianaNFC")
        self.SetSize((400, 350))

    def __do_layout(self):
        from juliana import APP_NAME, APP_VERSION, APP_AUTHOR
        grid_sizer_1 = wx.BoxSizer(wx.VERTICAL)
        grid_sizer_1.Add((0, 10), 0, wx.EXPAND, 0)
        label_1 = wx.StaticText(self, wx.ID_ANY, f"{APP_NAME} v{APP_VERSION}", style=wx.ALIGN_CENTER)
        label_1.SetFont(wx.Font(18, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, 0, ""))
        grid_sizer_1.Add(label_1, 0, wx.ALIGN_CENTER, 8)
        grid_sizer_1.Add((0, 8), 0, wx.EXPAND, 0)
        static_line_1 = wx.StaticLine(self, wx.ID_ANY)
        grid_sizer_1.Add(static_line_1, 0, wx.ALL | wx.EXPAND, 0)
        grid_sizer_1.Add((0, 8), 0, wx.EXPAND, 0)
        label_2 = wx.StaticText(self, wx.ID_ANY, f"JulianaNFC is a small tray application that allows scanning "
                                                 f"NFC cards to a websocket for use in web applications.", style=wx.ALIGN_CENTER)
        label_2.Wrap(320)
        grid_sizer_1.Add(label_2, 0, wx.ALIGN_CENTER, 8)
        grid_sizer_1.Add((0, 8), 0, wx.EXPAND, 0)
        label_3 = wx.StaticText(self, wx.ID_ANY, f"JulianaNFC was created by {APP_AUTHOR}", style=wx.ALIGN_CENTER)
        label_3.Wrap(320)
        grid_sizer_1.Add(label_3, 0, wx.ALIGN_CENTER, 8)
        grid_sizer_1.Add((0, 8), 0, wx.EXPAND, 0)
        label_6 = wx.StaticText(self, wx.ID_ANY, "For more information, check the GitHub:", style=wx.ALIGN_CENTER)
        grid_sizer_1.Add(label_6, 0, wx.ALIGN_CENTER, 0)
        grid_sizer_1.Add(self.hyperlink_2, 0, wx.ALIGN_CENTER, 0)
        label_7 = wx.StaticText(self, wx.ID_ANY, "For support, mail the WWW-committee:", style=wx.ALIGN_CENTER)
        grid_sizer_1.Add(label_7, 0, wx.ALIGN_CENTER, 0)
        grid_sizer_1.Add(self.hyperlink_3, 0, wx.ALIGN_CENTER, 0)
        grid_sizer_1.Add((0, 10), 0, wx.EXPAND, 0)
        grid_sizer_1.Add(self.button_2, 0, wx.ALIGN_CENTER, 0)
        grid_sizer_1.Add((0, 10), 0, wx.EXPAND, 0)
        self.SetSizer(grid_sizer_1)
        grid_sizer_1.Fit(self)
        self.Layout()
