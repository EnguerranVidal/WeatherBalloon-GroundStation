######################## IMPORTS ########################
import os
from typing import Optional
import pyqtgraph as pg

# ------------------- PyQt Modules -------------------- #
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# --------------------- Sources ----------------------- #
from sources.common.FileHandling import load_settings
from sources.common.balloondata import BalloonPackageDatabase
from sources.common.Widgets import BasicDisplay, ArgumentSelectorWidget


######################## CLASSES ########################
class CustomGraph(BasicDisplay):
    def __init__(self, path, parent=None):
        super().__init__(path, parent)
        layout = QVBoxLayout(self)
        self.plotWidget = pg.PlotWidget(self)
        self.plotWidget.setBackground('w')
        layout.addWidget(self.plotWidget)

        self.settingsWidget = CustomGraphEditDialog(self.currentDir, self)

        x_values = [1, 2, 3]
        y_values = [8, 5, 10]
        # self.plotWidget.plot(x_values, y_values)

    def applyChanges(self, editWidget):
        backgroundColor = editWidget.backgroundColorFrame.colorLabel.text()
        self.plotWidget.setBackground(backgroundColor)


class CustomGraphEditDialog(QWidget):
    def __init__(self, path, parent: CustomGraph = None):
        super().__init__(parent)
        self.currentDir = path
        # Create the curves Tab Widget
        self.tabWidget = QTabWidget()
        self.tabWidget.addTab(CurveEditor(0, self.currentDir, self), "Tab 1")
        self.tabWidget.addTab(CurveEditor(1, self.currentDir, self), "Tab 2")
        self.tabWidget.setMovable(True)

        # Create a custom color frame widget
        plotItem = parent.plotWidget.getPlotItem()
        viewBox = plotItem.getViewBox()
        color = viewBox.background.brush().color().getRgb()
        r, g, b, a = color
        color = (r / 255, g / 255, b / 255, a / 255)
        color = QColor(*color)
        hexString = color.name()
        self.backgroundColorFrame = ColorEditor('Background Color', color=hexString, parent=self)

        # Add the color frame to the layout
        layout = QVBoxLayout()
        layout.addWidget(self.tabWidget)
        layout.addWidget(self.backgroundColorFrame)
        self.setLayout(layout)


class CurveEditor(QWidget):
    def __init__(self, curveIndex: int, path, parent=None):
        super().__init__(parent)
        self.currentDir = path
        # TODO Finish Curve Editor
        # Retrieving Curve parameters from parent and index

        # Setting editing widgets
        self.lineEditX = QLineEdit()
        self.lineEditY = QLineEdit()
        labelEditX = QLabel()
        labelEditX.setPixmap(QPixmap('sources/icons/light-theme/icons8-x-coordinate-96.png').scaled(25, 25))
        labelEditY = QLabel()
        labelEditY.setPixmap(QPixmap('sources/icons/light-theme/icons8-y-coordinate-96.png').scaled(25, 25))

        selectionButtonPixmap = QPixmap('sources/icons/light-theme/icons8-add-database-96.png').scaled(25, 25)
        self.buttonSelectorX = QPushButton()
        self.buttonSelectorX.setIcon(QIcon(selectionButtonPixmap))
        self.buttonSelectorY = QPushButton()
        self.buttonSelectorY.setIcon(QIcon(selectionButtonPixmap))
        self.buttonSelectorY.clicked.connect(self.openCurveArgumentSelector)

        nameLabel = QLabel('Name: ')
        self.nameEdit = QLineEdit()

        self.colorEditor = ColorEditor('Curve Color', color='#ffffff', parent=self)

        layout = QGridLayout()
        layout.addWidget(nameLabel, 0, 0, 1, 1)
        layout.addWidget(self.nameEdit, 0, 1, 1, 1)
        layout.addWidget(labelEditX, 1, 0)
        layout.addWidget(self.lineEditX, 1, 1)
        layout.addWidget(self.buttonSelectorX, 1, 2)
        layout.addWidget(labelEditY, 2, 0)
        layout.addWidget(self.lineEditY, 2, 1)
        layout.addWidget(self.buttonSelectorY, 2, 2)
        layout.addWidget(self.colorEditor, 3, 0, 1, 3)
        self.setLayout(layout)

    def openCurveArgumentSelector(self):
        curveArgumentSelector = CurveArgumentSelector(self.currentDir, self)
        curveArgumentSelector.exec_()
        if curveArgumentSelector.selectedArgument is not None:
            self.lineEditY.setText(curveArgumentSelector.selectedArgument)


class ColorEditor(QGroupBox):
    def __init__(self, name, color='#ffffff', parent=None):
        super().__init__(parent)
        self.setTitle(name)

        # Create a color button widget and set its initial color to the specified color
        self.colorButton = QPushButton()
        self.colorButton.setMinimumSize(QSize(20, 20))
        self.colorButton.setMaximumSize(QSize(20, 20))
        self.colorButton.setStyleSheet(f"background-color: {color};")

        # Create a label to display the hex code of the selected color and set its initial text to the specified color
        self.colorLabel = QLabel(color)
        self.colorButton.clicked.connect(self.changeColor)

        # Add the color button and label to the layout
        layout = QHBoxLayout()
        layout.addWidget(self.colorButton)
        layout.addWidget(self.colorLabel)
        self.setLayout(layout)

    def changeColor(self):
        color = QColorDialog.getColor()
        self.colorButton.setStyleSheet(f"background-color: {color.name()};")
        self.colorLabel.setText(color.name())


class CurveArgumentSelector(QDialog):
    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.selectedArgument = None
        self.currentDir = path
        self.formatPath = os.path.join(self.currentDir, 'formats')
        # Set up label
        self.label = QLabel("Select an argument")

        # Set up item selection widget
        self.itemSelectionWidget = ArgumentSelectorWidget(self.currentDir)
        self.itemSelectionWidget.treeWidget.itemSelectionChanged.connect(self.selectionMade)

        # Set buttons for bottom row
        bottomRowLayout = QHBoxLayout()
        self.selectButton = QPushButton("Select")
        self.cancelButton = QPushButton("Cancel")
        bottomRowLayout.addWidget(self.selectButton)
        bottomRowLayout.addWidget(self.cancelButton)

        # Setting Up Selected Name and Info
        self.selectionNameLabel = QLabel()
        self.selectionInfoEdit = QLineEdit()
        self.selectionInfoEdit.setReadOnly(True)
        self.selectionInfoEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.selectionInfoEdit.setAlignment(Qt.AlignTop | Qt.AlignBottom)

        leftLayout = QVBoxLayout()
        leftLayout.addWidget(self.label)
        leftLayout.addWidget(self.itemSelectionWidget)
        leftLayout.addLayout(bottomRowLayout)

        # Set layout for label and lineedit
        rightLayout = QVBoxLayout()
        rightLayout.addWidget(self.selectionNameLabel, stretch=0)
        rightLayout.addWidget(self.selectionInfoEdit, stretch=1)
        rightLayout.setAlignment(self.selectionInfoEdit, Qt.AlignBottom)

        mainLayout = QHBoxLayout()
        mainLayout.addLayout(leftLayout)
        mainLayout.addLayout(rightLayout)
        mainLayout.setStretchFactor(leftLayout, 1)
        mainLayout.setStretchFactor(rightLayout, 2)
        self.setLayout(mainLayout)

    def selectionMade(self):
        currentItem = self.itemSelectionWidget.treeWidget.currentItem()

        def getParentChain(item):
            if item.parent():
                parent = item.parent()
                name = getParentChain(parent) + '/' + item.text(0)
            else:
                name = item.text(0)
            return name

        if not currentItem.isDisabled():
            # Retrieving Data
            database = self.itemSelectionWidget.comboBox.currentText()
            telemetry = self.itemSelectionWidget.label.text()
            treeChain = getParentChain(currentItem)
            itemName = currentItem.text(0)
            # Updating Value
            self.selectionNameLabel.setText(itemName)
            self.selectedArgument = '{}${}${}'.format(database, telemetry, treeChain)



class SplitViewGraph(BasicDisplay):
    def __init__(self, parent=None):
        super().__init__(parent)
        # TODO SPLIT VIEW 2D GRAPH


# TODO MULTI-CURVES 2D GRAPH
# TODO 3D GRAPH
