# =============================================================================
# Copyright (C) 2010 Diego Duclos
#
# This file is part of pyfa.
#
# pyfa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyfa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyfa.  If not, see <http://www.gnu.org/licenses/>.
# =============================================================================


# noinspection PyPackageRequirements
import wx
from logbook import Logger

import gui.display
import gui.globalEvents as GE
import gui.mainFrame
from graphs.data.base import FitGraph
from graphs.events import RESIST_MODE_CHANGED
from gui.auxFrame import AuxiliaryFrame
from gui.bitmap_loader import BitmapLoader
from service.const import GraphCacheCleanupReason
from service.settings import GraphSettings
from . import canvasPanel
from .ctrlPanel import GraphControlPanel


pyfalog = Logger(__name__)


class GraphFrame(AuxiliaryFrame):

    def __init__(self, parent):
        if not canvasPanel.graphFrame_enabled:
            pyfalog.warning('Matplotlib is not enabled. Skipping initialization.')
            return

        super().__init__(parent, title='Graphs', style=wx.RESIZE_BORDER, size=(520, 390))
        self.mainFrame = gui.mainFrame.MainFrame.getInstance()

        self.SetIcon(wx.Icon(BitmapLoader.getBitmap('graphs_small', 'gui')))

        mainSizer = wx.BoxSizer(wx.VERTICAL)

        # Layout - graph selector
        self.graphSelection = wx.Choice(self, wx.ID_ANY, style=0)
        self.graphSelection.Bind(wx.EVT_CHOICE, self.OnGraphSwitched)
        mainSizer.Add(self.graphSelection, 0, wx.EXPAND)

        # Layout - plot area
        self.canvasPanel = canvasPanel.GraphCanvasPanel(self, self)
        mainSizer.Add(self.canvasPanel, 1, wx.EXPAND | wx.ALL, 0)

        mainSizer.Add(wx.StaticLine(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL), 0, wx.EXPAND)

        # Layout - graph control panel
        self.ctrlPanel = GraphControlPanel(self, self)
        mainSizer.Add(self.ctrlPanel, 0, wx.EXPAND | wx.ALL, 0)

        self.SetSizer(mainSizer)

        # Setup - graph selector
        for view in FitGraph.views:
            self.graphSelection.Append(view.name, view())
        self.graphSelection.SetSelection(0)
        self.ctrlPanel.updateControls(layout=False)

        # Event bindings - local events
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_CHAR_HOOK, self.kbEvent)

        # Event bindings - external events
        self.mainFrame.Bind(GE.FIT_RENAMED, self.OnFitRenamed)
        self.mainFrame.Bind(GE.FIT_CHANGED, self.OnFitChanged)
        self.mainFrame.Bind(GE.FIT_REMOVED, self.OnFitRemoved)
        self.mainFrame.Bind(GE.TARGET_PROFILE_RENAMED, self.OnProfileRenamed)
        self.mainFrame.Bind(GE.TARGET_PROFILE_CHANGED, self.OnProfileChanged)
        self.mainFrame.Bind(GE.TARGET_PROFILE_REMOVED, self.OnProfileRemoved)
        self.mainFrame.Bind(RESIST_MODE_CHANGED, self.OnResistModeChanged)
        self.mainFrame.Bind(GE.GRAPH_OPTION_CHANGED, self.OnGraphOptionChanged)

        self.Layout()
        self.UpdateWindowSize()
        self.draw()

    @classmethod
    def openOne(cls, parent):
        if canvasPanel.graphFrame_enabled:
            super().openOne(parent)

    def UpdateWindowSize(self):
        curW, curH = self.GetSize()
        bestW, bestH = self.GetBestSize()
        newW = max(curW, bestW)
        newH = max(curH, bestH)
        if newW > curW or newH > curH:
            newSize = wx.Size(newW, newH)
            self.SetSize(newSize)
            self.SetMinSize(newSize)

    def kbEvent(self, event):
        keycode = event.GetKeyCode()
        mstate = wx.GetMouseState()
        if keycode == wx.WXK_ESCAPE and mstate.GetModifiers() == wx.MOD_NONE:
            self.Close()
            return
        event.Skip()

    # Fit events
    def OnFitRenamed(self, event):
        event.Skip()
        self.ctrlPanel.OnFitRenamed(event)
        self.draw()

    def OnFitChanged(self, event):
        event.Skip()
        for fitID in event.fitIDs:
            self.clearCache(reason=GraphCacheCleanupReason.fitChanged, extraData=fitID)
        self.ctrlPanel.OnFitChanged(event)
        self.draw()

    def OnFitRemoved(self, event):
        event.Skip()
        self.clearCache(reason=GraphCacheCleanupReason.fitRemoved, extraData=event.fitID)
        self.ctrlPanel.OnFitRemoved(event)
        self.draw()

    # Target profile events
    def OnProfileRenamed(self, event):
        event.Skip()
        self.ctrlPanel.OnProfileRenamed(event)
        self.draw()

    def OnProfileChanged(self, event):
        event.Skip()
        self.clearCache(reason=GraphCacheCleanupReason.profileChanged, extraData=event.profileID)
        self.ctrlPanel.OnProfileChanged(event)
        self.draw()

    def OnProfileRemoved(self, event):
        event.Skip()
        self.clearCache(reason=GraphCacheCleanupReason.profileRemoved, extraData=event.profileID)
        self.ctrlPanel.OnProfileRemoved(event)
        self.draw()

    def OnResistModeChanged(self, event):
        event.Skip()
        for fitID in event.fitIDs:
            self.clearCache(reason=GraphCacheCleanupReason.resistModeChanged, extraData=fitID)
        self.ctrlPanel.OnResistModeChanged(event)
        self.draw()

    def OnGraphOptionChanged(self, event):
        event.Skip()
        self.ctrlPanel.Freeze()
        if getattr(event, 'refreshAxeLabels', False):
            self.ctrlPanel.refreshAxeLabels(restoreSelection=True)
        if getattr(event, 'refreshColumns', False):
            self.ctrlPanel.refreshColumns()
        self.ctrlPanel.Thaw()
        self.clearCache(reason=GraphCacheCleanupReason.optionChanged)
        self.draw()

    def OnGraphSwitched(self, event):
        view = self.getView()
        GraphSettings.getInstance().set('selectedGraph', view.internalName)
        self.clearCache(reason=GraphCacheCleanupReason.graphSwitched)
        self.resetXMark()
        self.ctrlPanel.updateControls()
        self.draw()
        event.Skip()

    def OnClose(self, event):
        self.mainFrame.Unbind(GE.FIT_RENAMED, handler=self.OnFitRenamed)
        self.mainFrame.Unbind(GE.FIT_CHANGED, handler=self.OnFitChanged)
        self.mainFrame.Unbind(GE.FIT_REMOVED, handler=self.OnFitRemoved)
        self.mainFrame.Unbind(GE.TARGET_PROFILE_RENAMED, handler=self.OnProfileRenamed)
        self.mainFrame.Unbind(GE.TARGET_PROFILE_CHANGED, handler=self.OnProfileChanged)
        self.mainFrame.Unbind(GE.TARGET_PROFILE_REMOVED, handler=self.OnProfileRemoved)
        self.mainFrame.Unbind(RESIST_MODE_CHANGED, handler=self.OnResistModeChanged)
        self.mainFrame.Unbind(GE.GRAPH_OPTION_CHANGED, handler=self.OnGraphOptionChanged)
        event.Skip()

    def getView(self):
        return self.graphSelection.GetClientData(self.graphSelection.GetSelection())

    def clearCache(self, reason, extraData=None):
        self.getView().clearCache(reason, extraData)

    def draw(self):
        self.canvasPanel.draw()

    def resetXMark(self):
        self.canvasPanel.xMark = None
