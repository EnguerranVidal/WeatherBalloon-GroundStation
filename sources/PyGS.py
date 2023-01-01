######################## IMPORTS ########################
import time
import os
import shutil
import sys
import subprocess
from functools import partial

# ------------------- PyQt Modules -------------------- #
from PyQt5.QtCore import QDateTime, QThread

# --------------------- Sources ----------------------- #
from sources.SerialGS import SerialMonitor
from sources.common.FileHandling import load_settings, save_settings, check_format, newTabNameGiving
from sources.common.Widgets import *

from sources.databases.general import PacketTabWidget
from sources.common.GraphWidgets import GraphTabWidget
from sources.displays.general import DisplayTabWidget


######################## CLASSES ########################
class PyGS(QMainWindow):
    def __init__(self, path):
        super().__init__()
        self.currentDir = path
        self.mainIcon = QIcon('sources/icons/light-theme/icons8-hot-air-balloon-96.png')
        self.formatPath = os.path.join(self.currentDir, "formats")
        self.dataPath = os.path.join(self.currentDir, "data")
        self.backupPath = os.path.join(self.dataPath, "backups")
        # Main Window Settings
        self.setGeometry(500, 500, 1000, 600)
        self.setWindowTitle('Weather Balloon Ground Station')
        self.setWindowIcon(self.mainIcon)
        self.settings = load_settings("settings")
        self.center()
        # Date&Time in StatusBar
        self.datetime = QDateTime.currentDateTime()
        self.dateLabel = QLabel(self.datetime.toString('dd.MM.yyyy  hh:mm:ss'))
        self.dateLabel.setStyleSheet('border: 0;')
        self.statusBar().addPermanentWidget(self.dateLabel)
        # FPS in StatusBar
        self.lastUpdate = time.perf_counter()
        self.avgFps = 0.0
        self.fpsLabel = QLabel('Fps : ---')
        self.fpsLabel.setStyleSheet('border: 0;')
        self.statusBar().addPermanentWidget(self.fpsLabel)
        # Status Bar Message and Timer
        self.statusBar().showMessage('Ready')
        self.statusDateTimer = QTimer()
        self.statusDateTimer.timeout.connect(self.updateStatus)
        self.statusDateTimer.start(0)

        ##################  VARIABLES  ##################
        self.serial = None
        self.available_ports = None
        self.packetTabList = []
        self.graphsTabList = []
        self.serialWindow = SerialWindow()
        self.serialWindow.textedit.setDisabled(True)

        self.serialMonitorTimer = QTimer()
        self.serialMonitorTimer.timeout.connect(self.checkSerialMonitor)
        self.serialMonitorTimer.start(100)
        self.newFormatWindow = None
        self.newGraphWindow = None
        self.newPlotWindow = None
        self.changeHeaderWindow = None
        self.trackedFormatsWindow = None

        # Initialize Interface
        self._checkEnvironment()
        self._generateUI()
        self._createActions()
        self._createMenuBar()
        self._createToolBars()

        self.show()

    def _generateUI(self):
        self.generalTabWidget = QTabWidget(self)
        self.generalTabWidget.setTabBar(QTabBar(self.generalTabWidget))
        self.generalTabWidget.setTabPosition(self.generalTabWidget.West)

        # Packet Tab Widget -----------------------------------------
        self.packetTabWidget = PacketTabWidget(self.currentDir)
        self.graphsTabWidget = GraphTabWidget(self.currentDir)
        self.displayTabWidget = DisplayTabWidget(self.currentDir)
        self.graphWidgetsList = []

        # Adding Tabs to Main Widget -------------------------------
        self.generalTabWidget.addTab(self.graphsTabWidget, 'Graphs')
        self.generalTabWidget.addTab(self.packetTabWidget, 'Packets')
        self.generalTabWidget.addTab(self.displayTabWidget, 'Display')

        # TODO
        self.generalTabWidget.currentChanged.connect(self.manageToolBars)
        self.setCentralWidget(self.generalTabWidget)

    def _createToolBars(self):
        # Databases Tool Bar ----------------------
        self.databasesToolBar = QToolBar("Package", self)

        # Displays Tool Bar ----------------------
        self.displaysToolBar = QToolBar('Display', self)
        self.displaysToolBar.addAction(self.newDisplayTabAct)
        self.displaysToolBar.addAction(self.closeDisplayTabAct)
        self.displaysToolBar.addSeparator()

        # Managing ToolBar Appearance ----------------------
        self.addToolBar(self.databasesToolBar)
        self.addToolBar(self.displaysToolBar)
        self.generalTabWidget.currentChanged.connect(self.manageToolBars)
        self.manageToolBars(0)

    def manageToolBars(self, index):
        # Show the ToolBar based on the appearing tab
        if index == 0:
            self.databasesToolBar.hide()
            self.displaysToolBar.show()
        elif index == 1:
            self.databasesToolBar.show()
            self.displaysToolBar.hide()
        elif index == 2:
            self.databasesToolBar.hide()
            self.displaysToolBar.show()

    def _createActions(self):
        # New Format
        self.newFormatAction = QAction('&New Format', self)
        self.newFormatAction.setStatusTip('Create New Packet Format')
        self.newFormatAction.setIcon(QIcon('sources/icons/light-theme/icons8-new-window-96.png'))
        self.newFormatAction.setShortcut('Ctrl+N')
        self.newFormatAction.triggered.connect(self.newFormatTab)
        # Open Format
        self.openFormatAction = QAction('&Open', self)
        self.openFormatAction.setStatusTip('Open Packet Format')
        self.openFormatAction.setIcon(QIcon('sources/icons/light-theme/icons8-open-in-browser-96.png'))
        self.openFormatAction.setShortcut('Ctrl+O')
        self.openFormatAction.triggered.connect(self.openFormatTab)
        # Save Format
        self.saveFormatAction = QAction('&Save', self)
        self.saveFormatAction.setStatusTip('Save Packet Format')
        self.saveFormatAction.setIcon(QIcon('sources/icons/light-theme/icons8-save-96.png'))
        self.saveFormatAction.setShortcut('Ctrl+S')
        self.saveFormatAction.triggered.connect(self.saveFormatTab)
        # Save As Format
        self.saveAsFormatAction = QAction('&Save As', self)
        self.saveAsFormatAction.setStatusTip('Save Packet Format As...')
        self.saveAsFormatAction.triggered.connect(self.saveAsFormatTab)
        # Save All Formats
        self.saveAllFormatAction = QAction('&Save All', self)
        self.saveAllFormatAction.setStatusTip('Save All Packet Formats')
        self.saveAllFormatAction.setIcon(QIcon('sources/icons/light-theme/icons8-save-all-96.png'))
        self.saveAllFormatAction.triggered.connect(self.saveAllFormatTab)
        # Close Format
        self.closeFormatAction = QAction('&Close', self)
        self.closeFormatAction.setStatusTip('Close Current Format')
        self.closeFormatAction.setIcon(QIcon('sources/icons/light-theme/icons8-close-window-96.png'))
        self.closeFormatAction.triggered.connect(self.closeFormatTab)
        # Import Format
        self.importFormatAction = QAction('&Import Format', self)
        self.importFormatAction.setStatusTip('Import Format')
        self.importFormatAction.setIcon(QIcon('sources/icons/light-theme/icons8-download-96.png'))
        self.importFormatAction.triggered.connect(self.importFormat)
        # Tracked Formats
        self.trackedFormatAction = QAction('&Tracked Formats', self)
        self.trackedFormatAction.setStatusTip('Open Tracked Formats Selection Window')
        self.trackedFormatAction.triggered.connect(self.openTrackedFormats)
        # Exit
        self.exitAct = QAction(QIcon('exit.png'), '&Exit', self)
        self.exitAct.setShortcut('Ctrl+Q')
        self.exitAct.setStatusTip('Exit application')
        self.exitAct.triggered.connect(self.close)
        # Change Header
        self.changeHeaderAct = QAction('&Change Header', self)
        self.changeHeaderAct.setStatusTip('Change Packets Header')
        self.changeHeaderAct.triggered.connect(self.openChangeHeader)
        # Add New Graph Tab
        self.newGraphAction = QAction('&Add Graph Tab', self)
        self.newGraphAction.setStatusTip('Add New Graph Tab')
        self.newGraphAction.triggered.connect(self.newGraphTab)
        # Add New Basic TimeAxis Plot
        self.newBasicPlotAction = QAction('&DateTime Plot', self)
        self.newBasicPlotAction.setStatusTip('Add New DateTime Plot')
        self.newBasicPlotAction.triggered.connect(self.newBasicPlot)
        # Add New Remote Plot
        self.newRemotePlotAction = QAction('&Remote Plot', self)
        self.newRemotePlotAction.setStatusTip('Add New Remote Plot')
        self.newRemotePlotAction.triggered.connect(self.newRemotePlot)
        # Toggle Autoscale
        self.autoscaleAct = QAction('&Autoscale', self, checkable=True, checked=self.settings["AUTOSCALE"])
        self.autoscaleAct.setStatusTip("Toggle Graphs' Autoscale")
        self.autoscaleAct.triggered.connect(self.setAutoscale)
        # Run Serial
        self.runSerialAct = QAction('&Run', self)
        self.runSerialAct.setShortcut('Ctrl+R')
        self.runSerialAct.setStatusTip('Run Serial Monitoring')
        self.runSerialAct.triggered.connect(self.startSerial)
        # Stop Serial
        self.stopSerialAct = QAction('&Stop', self)
        self.stopSerialAct.setStatusTip('Stop Serial Monitoring')
        self.stopSerialAct.triggered.connect(self.stopSerial)
        # Opening Serial Monitor
        self.openMonitorAct = QAction('&Open Serial Monitor', self)
        self.openMonitorAct.setShortcut('Ctrl+M')
        self.openMonitorAct.setIcon(QIcon('sources/icons/light-theme/icons8-monitor-96.png'))
        self.openMonitorAct.setStatusTip('Open Serial Monitor')
        self.openMonitorAct.triggered.connect(self.openSerialMonitor)
        # Toggle RSSI Acquirement
        self.rssiAct = QAction('&RSSI', self, checkable=True, checked=self.settings["RSSI"])
        self.rssiAct.setStatusTip('Toggle RSSI Retrieval')

        self.rssiAct.triggered.connect(self.setRssi)
        # Visit GitHub Page
        self.githubAct = QAction('&Visit GitHub', self)
        self.githubAct.setIcon(QIcon('sources/icons/light-theme/icons8-github-96.png'))
        self.githubAct.setStatusTip('Visit GitHub Page')
        self.githubAct.triggered.connect(self.openGithub)

        # Display Graph Actions ---------------------------
        # Add New Display Tab
        self.newDisplayTabAct = QAction('&New Display Tab', self)
        self.newDisplayTabAct.setIcon(QIcon('sources/icons/light-theme/icons8-add-folder-96.png'))
        self.newDisplayTabAct.setStatusTip('Create New Display Tab')
        self.newDisplayTabAct.setShortcut('Ctrl+Shift+N')
        self.newDisplayTabAct.triggered.connect(self.newDisplayTab)
        # Close Display Tab
        self.closeDisplayTabAct = QAction('&Close Display Tab', self)
        self.closeDisplayTabAct.setIcon(QIcon('sources/icons/light-theme/icons8-delete-folder-96.png'))
        self.closeDisplayTabAct.setStatusTip('Close Display Tab')
        self.closeDisplayTabAct.setShortcut('Ctrl+Shift+X')
        self.closeDisplayTabAct.triggered.connect(self.displayTabWidget.closeCurrentTab)

    def _createMenuBar(self):
        self.menubar = self.menuBar()

        ###  FILE MENU  ###
        self.fileMenu = self.menubar.addMenu('&File')
        self.fileMenu.addAction(self.newFormatAction)
        self.fileMenu.addAction(self.openFormatAction)
        self.recentMenu = QMenu('&Recent', self)
        self.recentMenu.aboutToShow.connect(self.populateRecentMenu)

        self.fileMenu.addMenu(self.recentMenu)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.saveFormatAction)
        self.fileMenu.addAction(self.saveAsFormatAction)
        self.fileMenu.addAction(self.saveAllFormatAction)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.closeFormatAction)
        self.fileMenu.addSeparator()
        self.manageFormatsMenu = QMenu('&Manage Formats', self)
        self.manageFormatsMenu.addAction(self.importFormatAction)
        self.manageFormatsMenu.addAction(self.trackedFormatAction)
        self.fileMenu.addMenu(self.manageFormatsMenu)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.exitAct)
        self.fileMenu.aboutToShow.connect(self.populateFileMenu)

        ###  EDIT MENU  ###
        self.editMenu = self.menubar.addMenu('&Edit')
        self.editMenu.addAction(self.changeHeaderAct)

        ###  WINDOW MENU  ###
        self.windowMenu = self.menubar.addMenu('&Window')
        self.manageGraphsMenu = QMenu('&Graph Tab', self)
        self.manageGraphsMenu.addAction(self.newGraphAction)
        self.addPlotMenu = QMenu('&Add New Plot', self)
        self.addPlotMenu.addAction(self.newRemotePlotAction)
        self.addPlotMenu.addAction(self.newBasicPlotAction)
        self.manageGraphsMenu.addMenu(self.addPlotMenu)
        self.windowMenu.addMenu(self.manageGraphsMenu)
        self.windowMenu.addSeparator()
        self.windowMenu.addAction(self.autoscaleAct)

        ###  TOOLS MENU  ###
        self.toolsMenu = self.menubar.addMenu('&Tools')
        self.toolsMenu.addAction(self.runSerialAct)
        self.toolsMenu.addAction(self.stopSerialAct)
        self.toolsMenu.addAction(self.openMonitorAct)
        self.toolsMenu.addSeparator()
        self.portMenu = QMenu('&Port', self)
        self.toolsMenu.addMenu(self.portMenu)
        # Baud Group
        baud_rates = self.settings["AVAILABLE_BAUDS"]
        id_baud = baud_rates.index(str(self.settings["SELECTED_BAUD"]))
        self.baudMenu = QMenu('&Baud    ' + baud_rates[id_baud], self)
        baud_group = QActionGroup(self.baudMenu)
        for baud in baud_rates:
            action = QAction(baud, self.baudMenu, checkable=True, checked=baud == baud_rates[id_baud])
            self.baudMenu.addAction(action)
            baud_group.addAction(action)
        baud_group.setExclusive(True)
        baud_group.triggered.connect(self.selectBaud)
        self.toolsMenu.addMenu(self.baudMenu)
        self.toolsMenu.addSeparator()
        self.toolsMenu.addAction(self.rssiAct)
        self.toolsMenu.aboutToShow.connect(self.populateToolsMenu)

        ###  HELP MENU  ###
        self.helpMenu = self.menubar.addMenu('&Help')
        self.helpMenu.addAction(self.githubAct)

    def _checkEnvironment(self):
        if not os.path.exists(self.formatPath):
            os.mkdir(self.formatPath)
        if not os.path.exists(self.dataPath):
            os.mkdir(self.dataPath)
        if not os.path.exists(self.backupPath):
            os.mkdir(self.backupPath)

    def center(self):
        frameGeometry = self.frameGeometry()
        screenCenter = QDesktopWidget().availableGeometry().center()
        frameGeometry.moveCenter(screenCenter)
        self.move(frameGeometry.topLeft())

    def newFormatTab(self):
        self.newFormatWindow = NewPackageWindow()
        self.newFormatWindow.buttons.accepted.connect(self.acceptNewFormatTab)
        self.newFormatWindow.buttons.rejected.connect(self.newFormatWindow.close)
        self.newFormatWindow.show()

    def acceptNewFormatTab(self):
        name = self.newFormatWindow.nameEdit.text()
        self.packetTabWidget.newFormat(name)
        self.newFormatWindow.close()

    def newDisplayTab(self):
        name = newTabNameGiving(self.displayTabWidget.tabNamesList(), addition='Tab')
        self.displayTabWidget.tabWidget.addTab(QMainWindow(), name)

    def newGraphTab(self):
        self.newGraphWindow = NewGraphWindow()
        self.newGraphWindow.buttons.accepted.connect(self.createNewGraphTab)
        self.newGraphWindow.buttons.rejected.connect(self.newGraphWindow.close)
        self.newGraphWindow.show()

    def newRemotePlot(self):
        if self.graphsTabWidget.graphCentralWindow.count() > 0:
            self.newPlotWindow = NewPlotWindow()
            self.newPlotWindow.buttons.accepted.connect(self.createNewRemotePlot)
            self.newPlotWindow.buttons.rejected.connect(self.newPlotWindow.close)
            self.newPlotWindow.show()
        else:
            cancelling = MessageBox()
            cancelling.setWindowIcon(self.mainIcon)
            cancelling.setWindowTitle("Error")
            cancelling.setText("No Graph tabs are\nset to add a plot too.")
            cancelling.setStandardButtons(QMessageBox.Ok)
            cancelling.setStyleSheet("QLabel{min-width: 200px;}")
            cancelling.exec_()

    def newBasicPlot(self):
        if self.graphsTabWidget.graphCentralWindow.count() > 0:
            self.newPlotWindow = NewPlotWindow()
            self.newPlotWindow.buttons.accepted.connect(self.createNewBasicPlot)
            self.newPlotWindow.buttons.rejected.connect(self.newPlotWindow.close)
            self.newPlotWindow.show()
        else:
            cancelling = MessageBox()
            cancelling.setWindowIcon(self.mainIcon)
            cancelling.setWindowTitle("Error")
            cancelling.setText("No Graph tabs are\nset to add a plot too.")
            cancelling.setStandardButtons(QMessageBox.Ok)
            cancelling.setStyleSheet("QLabel{min-width: 200px;}")
            cancelling.exec_()

    def createNewRemotePlot(self):
        currentIndex = self.graphsTabWidget.graphCentralWindow.currentIndex()
        name = self.newPlotWindow.nameEdit.text()
        widget = self.graphsTabWidget.graphCentralWindow.widget(currentIndex)
        widget.addDockRemote(name)
        self.newPlotWindow.close()

    def createNewBasicPlot(self):
        currentIndex = self.graphsTabWidget.graphCentralWindow.currentIndex()
        name = self.newPlotWindow.nameEdit.text()
        widget = self.graphsTabWidget.graphCentralWindow.widget(currentIndex)
        widget.addDockDateTime(name)
        self.newPlotWindow.close()

    def createNewGraphTab(self):
        name = self.newGraphWindow.nameEdit.text()
        self.graphsTabWidget.addDockTab(name)
        self.newGraphWindow.close()

    def openFormatTab(self):
        if os.path.exists(self.formatPath):
            path = QFileDialog.getExistingDirectory(self, "Select Directory", self.formatPath)
        else:
            path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if os.path.abspath(path) not in [os.path.abspath(self.formatPath), os.path.abspath(self.currentDir)]:
            self.packetTabWidget.openFormat(path)
            self.addToRecent(path)

    def addToRecent(self, path):
        self.settings['OPENED_RECENTLY'].insert(0, path)
        openedRecently = []
        for i in range(len(self.settings['OPENED_RECENTLY'])):
            if self.settings['OPENED_RECENTLY'][i] not in openedRecently:
                openedRecently.append(self.settings['OPENED_RECENTLY'][i])
        self.settings['OPENED_RECENTLY'] = openedRecently
        if len(self.settings['OPENED_RECENTLY']) == 5:
            self.settings['OPENED_RECENTLY'].pop()
        save_settings(self.settings, 'settings')

    def openRecentFile(self, filename):
        filenames = [os.path.basename(path) for path in self.settings['OPENED_RECENTLY']]
        path = self.settings['OPENED_RECENTLY'][filenames.index(filename)]
        if os.path.exists(path):
            self.packetTabWidget.openFormat(path)
            self.addToRecent(path)

    def saveFormatTab(self):
        self.packetTabWidget.saveFormat()
        self.graphsTabWidget.fillComboBox()

    def saveAsFormatTab(self):
        # Create Lines
        path = QFileDialog.getSaveFileName(self, 'Save File')
        self.packetTabWidget.saveFormat(path[0])
        self.graphsTabWidget.fillComboBox()

    def saveAllFormatTab(self):
        self.packetTabWidget.saveAllFormats()

    def closeFormatTab(self):
        self.packetTabWidget.closeFormat()

    def openTrackedFormats(self):
        self.trackedFormatsWindow = TrackedBalloonsWindow(self.currentDir)
        self.trackedFormatsWindow.buttons.accepted.connect(self.editTrackedFormats)
        self.trackedFormatsWindow.buttons.rejected.connect(self.trackedFormatsWindow.close)
        self.trackedFormatsWindow.show()

    def editTrackedFormats(self):
        trackedFormats = self.trackedFormatsWindow.getListedValues()
        self.settings['FORMAT_FILES'] = trackedFormats
        save_settings(self.settings, 'settings')
        self.trackedFormatsWindow.close()
        self.graphsTabWidget.fillComboBox()

    def importFormat(self):
        path = QFileDialog.getOpenFileName(self, 'Import Packet Format')
        # Verifying if chosen file is a format
        if check_format(path[0]):
            # Finally copy the file into our format repository
            shutil.copy2(path[0], self.formatPath)
        else:
            cancelling = MessageBox()
            cancelling.setWindowIcon(self.mainIcon)
            cancelling.setWindowTitle("Error")
            cancelling.setText("This file does not satisfy the required format.")
            cancelling.setStandardButtons(QMessageBox.Ok)
            cancelling.exec_()

    def openChangeHeader(self):
        self.changeHeaderWindow = HeaderChangeWindow()
        acceptButton = QPushButton('Create', self.changeHeaderWindow)
        acceptButton.clicked.connect(self.acceptChangeHeader)
        self.changeHeaderWindow.dlgLayout.addWidget(acceptButton)
        self.changeHeaderWindow.show()

    def acceptChangeHeader(self):
        pass

    def startSerial(self):
        message = "Port : " + self.settings["SELECTED_PORT"] + "  Baud : "
        message += self.settings["SELECTED_BAUD"] + "\nDo you wish to continue ?"
        msg = MessageBox()
        msg.setWindowIcon(self.mainIcon)
        msg.setWindowTitle("Running Warning")
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        msg.setStyleSheet("QLabel{min-width: 200px;}")
        msg.exec_()
        button = msg.clickedButton()
        sb = msg.standardButton(button)
        if sb == QMessageBox.Yes:
            serialPath = os.path.join(self.currentDir, "sources/SerialGS.py")
            if os.path.exists(serialPath):
                self.serial = SerialMonitor(self.currentDir)
                self.serialWindow.textedit.setDisabled(False)
                self.serial.output.connect(self.onSerialOutput)
                self.serial.progress.connect(self.newSerialData)
                self.serial.start()
            else:
                cancelling = MessageBox()
                cancelling.setWindowIcon(self.mainIcon)
                cancelling.setWindowTitle("Error")
                cancelling.setText("Serial.py not found.")
                cancelling.setStandardButtons(QMessageBox.Ok)
                cancelling.setStyleSheet("QLabel{min-width: 200px;}")
                cancelling.exec_()

    def stopSerial(self):
        if self.serial is not None:
            self.serial.interrupt()
            self.serial = None
            time.sleep(0.5)
            self.serialWindow.textedit.setDisabled(True)

    def newSerialData(self, content):
        self.graphsTabWidget.updateTabGraphs(content)

    def onSerialOutput(self, newLine):
        needScrolling = False
        value = self.serialWindow.textedit.verticalScrollBar().maximum()
        if self.serialWindow.textedit.verticalScrollBar().value() == value:
            needScrolling = True
        self.serialWindow.textedit.append(newLine + '\n')
        if bool(self.settings["AUTOSCROLL"]) and needScrolling:
            value = self.serialWindow.textedit.verticalScrollBar().maximum()
            self.serialWindow.textedit.verticalScrollBar().setValue(value)

    def dataCaptureUpdated(self, content):
        self.graphsTabWidget.updateTabGraphs(content)

    def openSerialMonitor(self):
        if self.serialWindow is None:
            self.serialWindow = SerialWindow()
            self.serialWindow.textedit.setDisabled(True)
            self.serialWindow.textedit.setReadOnly(True)
        if self.serialWindow.isVisible():
            self.serialWindow = SerialWindow()
        self.serialWindow.show()

    def setAutoscale(self, action):
        self.settings["AUTOSCALE"] = action
        save_settings(self.settings, "settings")

    def populateFileMenu(self):
        # OPENED RECENTLY MENU
        if len(self.settings['OPENED_RECENTLY']) == 0:
            self.recentMenu.setDisabled(True)
        else:
            self.recentMenu.setDisabled(False)
        # SAVE AND CLOSE ACTIONS
        if len(list(self.packetTabWidget.databases.keys())) == 0:
            self.saveFormatAction.setDisabled(True)
            self.saveAllFormatAction.setDisabled(True)
            self.saveAsFormatAction.setDisabled(True)
            self.closeFormatAction.setDisabled(True)

        else:
            self.saveFormatAction.setDisabled(False)
            self.saveAllFormatAction.setDisabled(False)
            self.saveAsFormatAction.setDisabled(False)
            self.closeFormatAction.setDisabled(False)

    def populateRecentMenu(self):
        self.recentMenu.clear()
        actions = []
        filenames = [os.path.basename(path) for path in self.settings['OPENED_RECENTLY']]
        for filename in filenames:
            action = QAction(filename, self)
            action.triggered.connect(partial(self.openRecentFile, filename))
            actions.append(action)
        self.recentMenu.addActions(actions)

    def populateToolsMenu(self):
        self.portMenu.setTitle('&Port')
        self.portMenu.setDisabled(False)
        import serial.tools.list_ports
        self.available_ports = [comport.device for comport in serial.tools.list_ports.comports()]
        if len(self.available_ports) == 0:
            self.stopSerialAct.setDisabled(True)
            self.portMenu.setDisabled(True)
            self.settings["SELECTED_PORT"] = ""
            save_settings(self.settings, "settings")
        else:
            self.portMenu.clear()
            port_group = QActionGroup(self.portMenu)
            selection = self.settings["SELECTED_PORT"]
            if selection in self.available_ports:
                for port in self.available_ports:
                    action = QAction(port, self.portMenu, checkable=True, checked=port == selection)
                    self.portMenu.addAction(action)
                    port_group.addAction(action)
                self.portMenu.setTitle('&Port    ' + selection)
            else:
                for port in self.available_ports:
                    action = QAction(port, self.portMenu, checkable=True, checked=port == self.available_ports[0])
                    self.portMenu.addAction(action)
                    port_group.addAction(action)
                self.portMenu.setTitle('&Port    ' + self.available_ports[0])
                self.settings["SELECTED_PORT"] = self.available_ports[0]
                save_settings(self.settings, "settings")
            port_group.setExclusive(True)
            port_group.triggered.connect(self.selectPort)
        if self.serial is None:
            self.stopSerialAct.setDisabled(True)
            self.runSerialAct.setDisabled(False)
        else:
            self.stopSerialAct.setDisabled(False)
            self.runSerialAct.setDisabled(True)

    def selectBaud(self, action):
        self.baudMenu.setTitle('&Baud    ' + action.text())
        self.settings["SELECTED_BAUD"] = action.text()
        save_settings(self.settings, "settings")
        # Restart Serial Connection if on
        if self.serial is not None:
            self.stopSerial()
            self.startSerial()

    def selectPort(self, action):
        self.portMenu.setTitle('&Port    ' + action.text())
        self.settings["SELECTED_PORT"] = action.text()
        save_settings(self.settings, "settings")
        # Stop Serial Connection if on
        if self.serial is not None:
            self.stopSerial()

    def setRssi(self, action):
        self.settings["RSSI"] = action
        save_settings(self.settings, "settings")
        # Restart Serial Connection if on
        if self.serial is not None:
            self.stopSerial()
            self.startSerial()

    def checkSerialMonitor(self):
        self.settings = load_settings("settings")
        if self.serial is not None and not self.serial.isRunning():
            self.stopSerial()
            self.serialWindow.textedit.setDisabled(True)

    def updateStatus(self):
        self.datetime = QDateTime.currentDateTime()
        self.dateLabel.setText(self.datetime.toString('dd.MM.yyyy  hh:mm:ss'))
        now = time.perf_counter()
        fps = 1.0 / (now - self.lastUpdate)
        self.lastUpdate = now
        self.avgFps = self.avgFps * 0.8 + fps * 0.2
        self.fpsLabel.setText('Fps : %0.2f ' % self.avgFps)

    @staticmethod
    def openGithub():
        import webbrowser
        webbrowser.open("https://github.com/EnguerranVidal/PyGS")

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Message', "Are you sure to quit?", QMessageBox.Yes |
                                     QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.stopSerial()
            time.sleep(0.5)
            self.serialMonitorTimer.stop()
            for window in QApplication.topLevelWidgets():
                window.close()
            event.accept()
        else:
            event.ignore()
