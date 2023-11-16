######################## IMPORTS ########################
import dataclasses
import re
from enum import Enum

from ecom.datatypes import TypeInfo

# ------------------- PyQt Modules -------------------- #
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from sources.common.widgets.Widgets import ValueWidget, TypeSelector
# --------------------- Sources ----------------------- #
from sources.common.widgets.Widgets import SquareIconButton, ValueWidget, SquareIconButton, TypeSelector
from sources.databases.balloondata import BalloonPackageDatabase, serializeTypedValue
from ecom.datatypes import TypeInfo, StructType, EnumType, ArrayType, DynamicSizeError


######################## CLASSES ########################
class SharedTypesEditorWidget(QWidget):
    change = pyqtSignal()

    def __init__(self, database):
        super().__init__()
        self.currentDataType = None
        self.database = database
        self.baseTypesValues = [baseType.value for baseType in TypeInfo.BaseType]
        self.baseTypeNames = [baseType.name for baseType in TypeInfo.BaseType]

        # DATATYPES TABLE
        self.table = QTableWidget()
        self.table.setColumnCount(3)  # Added a new column for 'Edit' buttons
        self.table.setHorizontalHeaderLabels(['Shared Type', '', 'Description'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

        # STACKED WIDGET
        self.stackedWidget = QStackedWidget()
        self.stackedWidget.addWidget(self.table)
        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.stackedWidget)
        self.setLayout(mainLayout)

        self.populateDataTypes()

    def populateDataTypes(self):
        autogeneratedTypes = ['ConfigurationId', 'Configuration', 'TelecommandType', 'TelemetryType', ]
        originalTypes = ['TelecommandMessageHeader', 'TelemetryMessageHeader']
        for name, typInfo in self.database.dataTypes.items():
            if name not in autogeneratedTypes and name not in originalTypes:
                rowPosition = self.table.rowCount()
                self.table.insertRow(rowPosition)
                itemName = QTableWidgetItem(name)
                self.table.setItem(rowPosition, 0, itemName)
                category = self.getDataTypeCategory(typInfo)
                if category in ['Enum', 'Structure']:
                    editButton = QPushButton(category)
                else:
                    buttonName = typInfo.baseTypeName
                    if buttonName in self.baseTypesValues:
                        buttonName = self.baseTypeNames[self.baseTypesValues.index(buttonName)]
                    editButton = QPushButton(buttonName)
                editButton.clicked.connect(self.editDataTypeClicked)
                self.table.setCellWidget(rowPosition, 1, editButton)
                descriptionItem = QTableWidgetItem(typInfo.description if typInfo.description else '')
                self.table.setItem(rowPosition, 2, descriptionItem)

    @staticmethod
    def getDataTypeCategory(typeInfo):
        if issubclass(typeInfo.type, Enum):
            return 'Enum'
        elif issubclass(typeInfo.type, StructType):
            return 'Structure'
        elif issubclass(typeInfo.type, ArrayType):
            return 'Array'
        elif typeInfo.description is None:
            return 'Simple'
        else:
            return 'Advanced'

    def editDataTypeClicked(self):
        senderWidget = self.sender()
        if isinstance(senderWidget, QPushButton):
            row = self.table.indexAt(senderWidget.pos()).row()
            name = self.table.item(row, 0).text()
            baseType, dataType = senderWidget.text(), self.database.dataTypes[name]
            category = self.getDataTypeCategory(dataType)
            if category == 'Enum':
                editor = EnumEditorWidget(self.database, name)
                self.goToEditor(editor)
            elif category == 'Structure':
                editor = StructureEditorWidget(self.database, name)
                self.goToEditor(editor)
            else:
                dialog = TypeSelector(self.database, baseType)
                result = dialog.exec_()
                if result == QDialog.Accepted:
                    selectedType = dialog.selectedType
                    selectedTypeName = selectedType[0].upper() if selectedType[0] in self.baseTypesValues else selectedType[0]
                    configType = f'{selectedTypeName}[{selectedType[2]}]' if selectedType[1] else f'{selectedTypeName}'
                    senderWidget.setText(configType)

    def goToEditor(self, editor):
        editorContainer = QWidget()
        editorLayout = QVBoxLayout(editorContainer)
        goBackButton = QPushButton('Go Back', editorContainer)
        goBackButton.clicked.connect(self.goBackToPreviousEditor)
        if isinstance(editor, StructureEditorWidget):
            editor.elementEditCreation.connect(self.goToEditor)
        editorLayout.addWidget(goBackButton)
        editorLayout.addWidget(editor)
        self.stackedWidget.addWidget(editorContainer)
        self.stackedWidget.setCurrentWidget(editorContainer)

    def goBackToPreviousEditor(self):
        currentIndex = self.stackedWidget.currentIndex()
        self.stackedWidget.setCurrentIndex(currentIndex - 1)
        removingEditor = self.stackedWidget.widget(currentIndex)
        self.stackedWidget.removeWidget(removingEditor)
        removingEditor.deleteLater()


class EnumEditorWidget(QWidget):
    def __init__(self, database, dataType):
        super().__init__()
        # UI ELEMENTS
        self.database, self.dataType = database, dataType
        self.baseTypesValues = [baseType.value for baseType in TypeInfo.BaseType]
        self.baseTypeNames = [baseType.name for baseType in TypeInfo.BaseType]
        self.valuesTableWidget = QTableWidget()
        self.valuesTableWidget.setColumnCount(3)
        self.valuesTableWidget.setHorizontalHeaderLabels(['Name', 'Value', 'Description'])
        self.valuesTableWidget.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.valuesTableWidget.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.valuesTableWidget.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.valuesTableWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.addValueButton = QPushButton('Add Value')
        self.addValueButton.clicked.connect(self.addEnumValue)
        self.populateValues()

        # MAIN LAYOUT
        layout = QVBoxLayout(self)
        layout.addWidget(self.valuesTableWidget)
        layout.addWidget(self.addValueButton)

    def populateValues(self):
        print(self.dataType)
        if isinstance(self.dataType, list):
            enumTypeInfo = self.database.getTypeInfo(self.dataType[0])
            for element in self.dataType[1:]:
                for name, child in enumTypeInfo.type:
                    if name == element:
                        enumTypeInfo = enumTypeInfo.type[name]
                        break
        else:
            enumTypeInfo = self.database.getTypeInfo(self.dataType)
        enumValues = enumTypeInfo.type.__members__
        self.valuesTableWidget.setRowCount(len(enumValues))
        for row, (name, value) in enumerate(enumValues.items()):
            nameItem = QTableWidgetItem(name)
            self.valuesTableWidget.setItem(row, 0, nameItem)
            valueItem = QLineEdit(str(value.value))
            if enumTypeInfo.baseTypeName and enumTypeInfo.baseTypeName in enumTypeInfo.type._value2member_map_:
                baseTypeValue = enumTypeInfo.type._value2member_map_[enumTypeInfo.baseTypeName].value
                if isinstance(value.value, baseTypeValue):
                    valueItem.setText(str(value.value))
            self.valuesTableWidget.setCellWidget(row, 1, valueItem)
            descriptionItem = QTableWidgetItem(value.__doc__ if value.__doc__ else '')
            self.valuesTableWidget.setItem(row, 2, descriptionItem)
        self.valuesTableWidget.resizeColumnsToContents()

    def addEnumValue(self):
        pass


class StructureEditorWidget(QWidget):
    elementEditCreation = pyqtSignal(QWidget)

    def __init__(self, database, dataType):
        super().__init__()
        self.structureInfo = None
        self.database, self.dataType = database, dataType
        self.baseTypesValues = [baseType.value for baseType in TypeInfo.BaseType]
        self.baseTypeNames = [baseType.name for baseType in TypeInfo.BaseType]

        # ELEMENT TABLE & BUTTON
        self.elementTable = QTableWidget()
        self.elementTable.setColumnCount(3)
        self.elementTable.setHorizontalHeaderLabels(['Element', 'Type', 'Description'])
        self.elementTable.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.elementTable.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.elementTable.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.populateElements()
        self.addElementButton = QPushButton('Add Element')
        self.addElementButton.clicked.connect(self.addElement)

        # MAIN LAYOUT
        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.elementTable)
        mainLayout.addWidget(self.addElementButton)
        self.setLayout(mainLayout)

    def populateElements(self):
        if isinstance(self.dataType, list):
            structInfo = self.database.getTypeInfo(self.dataType[0])
            for element in self.dataType[1:]:
                for name, child in structInfo.type:
                    if name == element:
                        structInfo = structInfo.type[name]
                        break
        else:
            structInfo = self.database.getTypeInfo(self.dataType)
        self.structureInfo = structInfo
        for row, (name, child) in enumerate(structInfo.type):
            rowPosition = self.elementTable.rowCount()
            self.elementTable.insertRow(rowPosition)
            nameItem = QTableWidgetItem(name)
            self.elementTable.setItem(row, 0, nameItem)
            category = self.getTypeCategory(child)
            buttonName = category if category not in ['Simple', 'Array'] else child.baseTypeName
            if buttonName in self.baseTypesValues:
                buttonName = self.baseTypeNames[self.baseTypesValues.index(buttonName)]
            editButton = QPushButton(buttonName)
            editButton.clicked.connect(self.typeButtonClicked)
            self.elementTable.setCellWidget(rowPosition, 1, editButton)
            descriptionItem = QTableWidgetItem(child.description)
            self.elementTable.setItem(row, 2, descriptionItem)

    def addElement(self):
        pass

    def typeButtonClicked(self):
        senderWidget = self.sender()
        if isinstance(senderWidget, QPushButton):
            row = self.elementTable.indexAt(senderWidget.pos()).row()
            name = self.elementTable.item(row, 0).text()
            baseType, dataType = senderWidget.text(), self.structureInfo.type[name]
            category = self.getTypeCategory(dataType)
            dataTypes = [self.dataType, name] if not isinstance(self.dataType, list) else self.dataType + [name]
            if category == 'Enum':
                editor = EnumEditorWidget(self.database, dataTypes)
                self.elementEditCreation.emit(editor)
            elif category == 'Structure':
                editor = StructureEditorWidget(self.database, dataTypes)
                self.elementEditCreation.emit(editor)
            else:
                dialog = TypeSelector(self.database, baseType)
                result = dialog.exec_()
                if result == QDialog.Accepted:
                    selectedType = dialog.selectedType
                    selectedTypeName = selectedType[0].upper() if selectedType[0] in self.baseTypesValues else selectedType[0]
                    configType = f'{selectedTypeName}[{selectedType[2]}]' if selectedType[1] else f'{selectedTypeName}'
                    senderWidget.setText(configType)

    @staticmethod
    def getTypeCategory(typeInfo):
        if issubclass(typeInfo.type, Enum):
            return 'Enum'
        elif issubclass(typeInfo.type, StructType):
            return 'Structure'
        elif issubclass(typeInfo.type, ArrayType):
            return 'Array'
        elif typeInfo.description is None:
            return 'Simple'
        else:
            return 'Advanced'