import wx
import wx.adv
import signal
import os
import time
import logging

from juliana import resource_path


logging.basicConfig(level=logging.INFO)


class JulianaTrayIcon(wx.adv.TaskBarIcon):
    def __init__(self, frame):
        self.frame = frame
        super(JulianaTrayIcon, self).__init__()
        self.SetIcon(wx.Icon(resource_path("resources/main.png"), type=wx.BITMAP_TYPE_PNG), "JulianaNFC")
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.on_left_click)

    def CreatePopupMenu(self):
        self.menu = wx.Menu()
        self.create_menu_text(self.menu, "JulianaNFC")
        self.menu.AppendSeparator()
        self.create_menu_item(self.menu, "About", self.on_about)
        self.create_menu_item(self.menu, "Exit", self.on_exit)
        return self.menu

    def create_menu_item(self, menu, label, callback, icon=None):
        item = wx.MenuItem(menu, -1, label)
        menu.Bind(wx.EVT_MENU, callback, id=item.GetId())
        menu.Append(item)
        if icon is not None:
            bitmap = wx.Bitmap(icon, type=wx.BITMAP_TYPE_PNG)
            item.SetBitmaps(checked=bitmap, unchecked=bitmap)
        return item

    def create_menu_text(self, menu, label, icon=None):
        item = wx.MenuItem(menu, -1, label)
        menu.Append(item)
        item.Enable(False)
        if icon is not None:
            bitmap = wx.Bitmap(icon, type=wx.BITMAP_TYPE_PNG)
            item.SetBitmaps(checked=bitmap, unchecked=bitmap)
        return item

    def on_left_click(self, event):
        if self.frame.IsShown():
            logging.info("Tray icon was left-clicked. Hiding main window")
            self.frame.Show(False)
        else:
            logging.info("Tray icon was left-clicked. Showing main window")
            self.frame.Show(True)

    def on_about(self, event):
        logging.debug("Tray option about clicked.")
        from gui.about import AboutDialog
        dialog = AboutDialog(None, wx.ID_ANY, "")
        dialog.ShowModal()
        dialog.Destroy()

    def on_exit(self, event):
        logging.info("Tray option exit clicked. Exiting Juliana")
        self.RemoveIcon()
        wx.CallAfter(self.Destroy)
        self.frame.Close(force=True)


class JulianaApp(wx.App):
    def __init__(self, *args, **kwargs):
        super(JulianaApp, self).__init__(*args, **kwargs)
        bitmap = wx.Bitmap(resource_path('resources/splash.png'))
        self.splash = wx.adv.SplashScreen(bitmap, wx.adv.SPLASH_CENTER_ON_SCREEN | wx.adv.SPLASH_TIMEOUT, 3500, self.frame)

    def OnInit(self):
        from juliana import APP_NAME, APP_VERSION, APP_AUTHOR, APP_SUPPORT
        self.frame = wx.Frame(None, title="JulianaNFC", size=(640, 480))
        self.frame.SetIcon(wx.Icon(resource_path("resources/main.png"), type=wx.BITMAP_TYPE_PNG))
        
        self.panel = wx.Panel(self.frame)

        self.console = wx.TextCtrl(self.panel, style=(wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP))
        self.console.AppendText(f"{APP_NAME} v{APP_VERSION} (By {APP_AUTHOR})\n")
        self.console.AppendText(f"Support: {APP_SUPPORT}\n\n")

        self.horizontal = wx.BoxSizer(wx.HORIZONTAL)
        self.horizontal.Add((8, 0), 0, wx.EXPAND, 0)
        self.horizontal.Add(self.console, proportion=1, flag=wx.EXPAND)
        self.horizontal.Add((8, 0), 0, wx.EXPAND, 0)

        self.vertical = wx.BoxSizer(wx.VERTICAL)
        self.vertical.Add((0, 8), 0, wx.EXPAND, 0)
        self.vertical.Add(self.horizontal, proportion=1, flag=wx.EXPAND)
        self.vertical.Add((0, 8), 0, wx.EXPAND, 0)

        self.panel.SetSizerAndFit(self.vertical)
        self.frame.Bind(wx.EVT_CLOSE, self.OnClose)

        self.SetTopWindow(self.frame)
        JulianaTrayIcon(self.frame)
        return True

    def OnClose(self, evt):
        if evt.CanVeto():
            logging.info("Main window closed. Hiding to systray")
            self.frame.Show(False)
            evt.Veto()
        else:
            logging.info("Main window closed and we must stop. Exiting Juliana")
            wx.CallAfter(self.Destroy)
            evt.Skip()

    def OnExit(self):
        os.kill(os.getpid(), signal.SIGINT)
        time.sleep(1)
        os.kill(os.getpid(), signal.SIGKILL)
        return 0

    def add_message(self, message):
        self.console.AppendText(f"{message}\n")
