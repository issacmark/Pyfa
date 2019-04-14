import wx

import gui.mainFrame
from eos.saveddata.drone import Drone as DroneType
from eos.saveddata.fighter import Fighter as FighterType
from eos.saveddata.fit import Fit as FitType
from eos.saveddata.module import Module as ModuleType
from gui import globalEvents as GE
from service.fit import Fit
from .calc.drone.projectedToggleState import CalcToggleProjectedDroneStateCommand
from .calc.fighter.toggleState import CalcToggleFighterStateCommand
from .calc.projectedFit.toggleState import CalcToggleProjectedFitCommand
from .calc.module.projectedChangeState import CalcChangeProjectedModuleStateCommand


class GuiToggleProjectedCommand(wx.Command):

    def __init__(self, fitID, thing, click):
        wx.Command.__init__(self, True, "Toggle Projected Item")
        self.mainFrame = gui.mainFrame.MainFrame.getInstance()
        self.internal_history = wx.CommandProcessor()
        self.fitID = fitID
        fit = Fit.getInstance().getFit(self.fitID)
        if isinstance(thing, FitType):
            self.commandType = CalcToggleProjectedFitCommand
            self.args = (self.fitID, thing.ID)
        elif isinstance(thing, ModuleType):
            position = fit.projectedModules.index(thing)
            self.commandType = CalcChangeProjectedModuleStateCommand
            self.args = (self.fitID, position, click)
        elif isinstance(thing, DroneType):
            self.commandType = CalcToggleProjectedDroneStateCommand
            self.args = (self.fitID, thing.itemID)
        elif isinstance(thing, FighterType):
            position = fit.projectedFighters.index(thing)
            self.commandType = CalcToggleFighterStateCommand
            self.args = (self.fitID, True, position)
        else:
            self.commandType = None
            self.args = ()

    def Do(self):
        if self.commandType is None:
            return False
        if not self.internal_history.Submit(self.commandType(*self.args)):
            return False
        Fit.getInstance().recalc(self.fitID)
        wx.PostEvent(self.mainFrame, GE.FitChanged(fitID=self.fitID))
        return True

    def Undo(self):
        for _ in self.internal_history.Commands:
            self.internal_history.Undo()
        Fit.getInstance().recalc(self.fitID)
        wx.PostEvent(self.mainFrame, GE.FitChanged(fitID=self.fitID))
        return True