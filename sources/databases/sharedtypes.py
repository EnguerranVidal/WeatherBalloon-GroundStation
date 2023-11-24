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
# SHARED DATA TYPES ------------------------------------------------------------------------------
class SharedTypesEditorWidget(QWidget):
    change = pyqtSignal()

    def __init__(self, database):
        super().__init__()
        self.currentDataType = None
        self.database = database
        self.baseTypesValues = [baseType.value for baseType in TypeInfo.BaseType]
        self.baseTypeNames = [baseType.name for baseType in TypeInfo.BaseType]
        self.editorCategories = []

        # DATATYPES TABLE
        self.table = QTableWidget()
        sharedTypesContainer, sharedTypesLayout = QWidget(), QVBoxLayout()
        self.table.setColumnCount(3)  # Added a new column for 'Edit' buttons
        self.table.setHorizontalHeaderLabels(['Shared Type', '', 'Description'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        sharedTypesLayout.addWidget(self.table)
        sharedTypesContainer.setLayout(sharedTypesLayout)

        # STACKED WIDGET
        self.stackedWidget = QStackedWidget()
        self.stackedWidget.addWidget(sharedTypesContainer)
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
                    self.change.emit()

    def goToEditor(self, editor):
        editorContainer = QWidget()
        editorLayout = QVBoxLayout(editorContainer)
        goBackButton = QPushButton('Go Back', editorContainer)
        goBackButton.clicked.connect(self.goBackToPreviousEditor)
        if isinstance(editor, StructureEditorWidget):
            editor.elementEditCreation.connect(self.goToEditor)
        editor.change.connect(self.change.emit)
        self.editorCategories.append(editor)
        editorLayout.addWidget(goBackButton)
        editorLayout.addWidget(editor)
        self.stackedWidget.addWidget(editorContainer)
        self.stackedWidget.setCurrentWidget(editorContainer)
        self.change.emit()

    def goBackToPreviousEditor(self):
        currentIndex = self.stackedWidget.currentIndex()
        self.stackedWidget.setCurrentIndex(currentIndex - 1)
        removingEditor = self.stackedWidget.widget(currentIndex)
        self.stackedWidget.removeWidget(removingEditor)
        removingEditor.deleteLater()
        self.editorCategories.pop(-1)
        self.change.emit()

    def addElement(self):
        dialog = ElementAdditionDialog(self.database, None)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            elementCategoryIndex = dialog.stackedWidget.currentIndex()
            category = ['Enum', 'Structure', 'Other'][elementCategoryIndex - 1]
            print(category)
            rowPosition = self.table.rowCount()
            self.table.insertRow(rowPosition)
            itemName = QTableWidgetItem(dialog.elementName)
            self.table.setItem(rowPosition, 0, itemName)
            if category in ['Enum', 'Structure']:
                editButton = QPushButton(category)
            else:
                buttonName = dialog.elementType
                if buttonName in self.baseTypesValues:
                    buttonName = self.baseTypeNames[self.baseTypesValues.index(buttonName)]
                editButton = QPushButton(buttonName)
            editButton.clicked.connect(self.editDataTypeClicked)
            self.table.setCellWidget(rowPosition, 1, editButton)
            descriptionItem = QTableWidgetItem('')
            self.table.setItem(rowPosition, 2, descriptionItem)
            # TODO : Add code to add sharedDataType to database
            self.change.emit()


class ElementAdditionDialog(QDialog):
    def __init__(self, database, dataType=None):
        super().__init__()
        self.elementName, self.elementType = None, None
        self.database, self.dataType = database, dataType
        self.setWindowTitle('Add New Element')
        self.setWindowIcon(QIcon('sources/icons/PyStrato.png'))
        self.setModal(True)
        self.baseTypesValues = [baseType.value for baseType in TypeInfo.BaseType]
        self.baseTypeNames = [baseType.name for baseType in TypeInfo.BaseType]
        self.intTypeNames = [baseType for baseType in self.baseTypeNames if baseType.startswith('INT') or baseType.startswith('UINT')]
        if dataType is None:
            self.elementList = [name for name, typInfo in self.database.dataTypes.items()]
        elif isinstance(dataType, list):
            structInfo = self.database.getTypeInfo(self.dataType[0])
            for element in self.dataType[1:]:
                for name, child in structInfo.type:
                    if name == element:
                        structInfo = structInfo.type[name]
            self.elementList = [name for name, child in structInfo.type]
        else:
            structInfo = self.database.getTypeInfo(self.dataType)
            self.elementList = [name for name, child in structInfo.type]
        # CATEGORIES SELECTION
        categoryLayout = QHBoxLayout()
        categoryButtonGroup = QButtonGroup(self)
        self.enumButton = QPushButton('ENUM', self)
        self.enumButton.setCheckable(True)
        categoryButtonGroup.addButton(self.enumButton)
        self.structButton = QPushButton('STRUCT', self)
        self.structButton.setCheckable(True)
        categoryButtonGroup.addButton(self.structButton)
        self.otherButton = QPushButton('OTHER', self)
        self.otherButton.setCheckable(True)
        categoryButtonGroup.addButton(self.otherButton)
        categoryLayout.addWidget(self.enumButton)
        categoryLayout.addWidget(self.structButton)
        categoryLayout.addWidget(self.otherButton)
        categoryButtonGroup.buttonClicked.connect(self.categoryChosen)

        # ENTRIES & BUTTONS
        self.stackedWidget = QStackedWidget()
        chooseLabel = QLabel('Choose a Category ...')
        self.stackedWidget.addWidget(chooseLabel)
        self.enumLineEdit = QLineEdit()
        self.enumTypeComboBox = QComboBox()
        self.enumTypeComboBox.addItems(self.intTypeNames)
        enumSelector = QWidget()
        enumLayout = QVBoxLayout(enumSelector)
        enumLayout.addWidget(self.enumLineEdit)
        enumLayout.addWidget(self.enumTypeComboBox)
        self.stackedWidget.addWidget(enumSelector)
        self.structureLineEdit = QLineEdit()
        structureSelector = QWidget()
        structureLayout = QVBoxLayout(structureSelector)
        structureLayout.addWidget(self.structureLineEdit)
        self.stackedWidget.addWidget(structureSelector)
        self.otherLineEdit = QLineEdit()
        self.otherTypeButton = QPushButton(self.baseTypeNames[0])
        self.otherTypeButton.clicked.connect(self.changeOtherType)
        otherSelector = QWidget()
        otherLayout = QVBoxLayout(otherSelector)
        otherLayout.addWidget(self.otherLineEdit)
        otherLayout.addWidget(self.otherTypeButton)
        self.stackedWidget.addWidget(otherSelector)
        self.stackedWidget.setCurrentIndex(0)

        self.okButton = QPushButton('OK')
        self.cancelButton = QPushButton('Cancel')
        self.okButton.clicked.connect(self.verifyElementName)
        self.cancelButton.clicked.connect(self.reject)

        # MAIN LAYOUT
        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.okButton)
        buttonLayout.addWidget(self.cancelButton)
        mainLayout = QVBoxLayout()
        mainLayout.addLayout(categoryLayout)
        mainLayout.addWidget(self.stackedWidget)
        mainLayout.addLayout(buttonLayout)
        self.setLayout(mainLayout)

    def categoryChosen(self, button):
        categoryName = button.text()
        currentElementName = self.getCurrentElementName()
        if categoryName == 'ENUM':
            self.stackedWidget.setCurrentIndex(1)
            self.enumLineEdit.setText(currentElementName)
        elif categoryName == 'STRUCT':
            self.stackedWidget.setCurrentIndex(2)
            self.structureLineEdit.setText(currentElementName)
        elif categoryName == 'OTHER':
            self.stackedWidget.setCurrentIndex(3)
            self.otherLineEdit.setText(currentElementName)
        else:
            self.stackedWidget.setCurrentIndex(0)

    def changeOtherType(self):
        if self.dataType is None:
            dialog = TypeSelector(self.database, typeName=self.otherTypeButton.text())
        elif isinstance(self.dataType, list):
            dialog = TypeSelector(self.database, typeName=self.otherTypeButton.text(), dataType=self.dataType[0], haveDataTypes=True)
        else:
            dialog = TypeSelector(self.database, typeName=self.otherTypeButton.text(), dataType=self.dataType, haveDataTypes=True)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            selectedType = dialog.selectedType
            selectedTypeName = selectedType[0].upper() if selectedType[0] in self.baseTypesValues else selectedType[0]
            configType = f'{selectedTypeName}[{selectedType[2]}]' if selectedType[1] else f'{selectedTypeName}'
            self.otherTypeButton.setText(configType)

    def getCurrentElementName(self):
        currentIndex = self.stackedWidget.currentIndex()
        if currentIndex == 1:
            return self.enumLineEdit.text()
        elif currentIndex == 2:
            return self.structureLineEdit.text()
        elif currentIndex == 3:
            return self.otherLineEdit.text()
        else:
            return ''

    def verifyElementName(self):
        name = self.getCurrentElementName()
        if name in self.elementList:
            if self.dataType is None:
                QMessageBox.warning(self, 'Used Name', 'This data-type name is already in use.')
            else:
                QMessageBox.warning(self, 'Used Name', 'This element name is already in use.')
        elif len(name) == 0:
            QMessageBox.warning(self, 'No Name Entered', 'No name was entered.')
        else:
            self.elementName = name
            self.elementType = self.enumTypeComboBox.currentText() if self.stackedWidget.currentIndex() == 1 else self.otherTypeButton.text()
            self.accept()


# ENUMERATORS -----------------------------------------------------------------------------
class EnumEditorWidget(QWidget):
    change = pyqtSignal()

    def __init__(self, database, dataType):
        super().__init__()
        # UI ELEMENTS
        self.enumTypeInfo = None
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
        self.populateValues()

        # MAIN LAYOUT
        layout = QVBoxLayout(self)
        layout.addWidget(self.valuesTableWidget)

    def populateValues(self):
        if isinstance(self.dataType, list):
            enumTypeInfo = self.database.getTypeInfo(self.dataType[0])
            for element in self.dataType[1:]:
                for name, child in enumTypeInfo.type:
                    if name == element:
                        enumTypeInfo = enumTypeInfo.type[name]
                        break
        else:
            enumTypeInfo = self.database.getTypeInfo(self.dataType)
        self.enumTypeInfo = enumTypeInfo
        enumValues = self.enumTypeInfo.type.__members__
        for row, (name, value) in enumerate(enumValues.items()):
            self.addValueRow(name, str(value.value), value.__doc__ if value.__doc__ else '')
        self.valuesTableWidget.resizeColumnsToContents()
        self.valuesTableWidget.itemChanged.connect(self.changeEnumValue)

    def addValueRow(self, name, value, description):
        rowPosition = self.valuesTableWidget.rowCount()
        self.valuesTableWidget.insertRow(rowPosition)
        nameItem = QTableWidgetItem(name)
        self.valuesTableWidget.setItem(rowPosition, 0, nameItem)
        valueItem = QTableWidgetItem(value)
        self.valuesTableWidget.setItem(rowPosition, 1, valueItem)
        descriptionItem = QTableWidgetItem(description)
        self.valuesTableWidget.setItem(rowPosition, 2, descriptionItem)

    def changeEnumValue(self, item):
        row, column = item.row(), item.column()
        if column == 0:
            pass
        elif column == 0:
            pass
        elif column == 2:
            pass
        # TODO : Add code to change Enum Value as well as generated values below it
        self.change.emit()

    def addEnumValue(self):
        dialog = EnumValueAdditionDialog(self.enumTypeInfo)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            valueName = dialog.nameLineEdit.text()
            values = [self.valuesTableWidget.cellWidget(row, 1).text() for row in
                      range(self.valuesTableWidget.rowCount())]
            digits = [s for s in reversed(values) if s.isdigit()]
            self.addValueRow(valueName, str(int(digits[0]) + 1), '')
            # TODO : Add code for enum value addition
            self.change.emit()

    def deleteEnumValue(self):
        selectedRows = [item.row() for item in self.valuesTableWidget.selectedItems()]
        if len(selectedRows):
            selectedRows = sorted(list(set(selectedRows)))
            dialog = EnumValueDeletionMessageBox(selectedRows)
            result = dialog.exec_()
            if result == QMessageBox.Yes:
                for row in reversed(selectedRows):
                    self.valuesTableWidget.removeRow(row)
                    # TODO : Add enum value deletion
                    # TODO : Add code to update other enum values based on the changes
                self.change.emit()


class EnumValueAdditionDialog(QDialog):
    def __init__(self, enumTypeInfo):
        super().__init__()
        self.setWindowTitle('Add Enum Value')
        self.setWindowIcon(QIcon('sources/icons/PyStrato.png'))
        self.setModal(True)
        enumValues = enumTypeInfo.type.__members__
        self.names, self.values = zip(*[(name, value.value) for row, (name, value) in enumerate(enumValues.items())])
        # ENTRIES & BUTTONS
        self.nameLabel = QLabel('Name:')
        self.nameLineEdit = QLineEdit()
        self.okButton = QPushButton('OK')
        self.cancelButton = QPushButton('Cancel')
        self.okButton.clicked.connect(self.verifyEnumValueName)
        self.cancelButton.clicked.connect(self.reject)
        # LAYOUT
        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.okButton)
        buttonLayout.addWidget(self.cancelButton)
        layout = QVBoxLayout(self)
        layout.addWidget(self.nameLabel)
        layout.addWidget(self.nameLineEdit)
        layout.addLayout(buttonLayout)
        self.setLayout(layout)

    def verifyEnumValueName(self):
        name = self.nameLineEdit.text()
        if name in self.names:
            QMessageBox.warning(self, 'Used Name', 'This enum value name is already in use.')
        elif len(name) == 0:
            QMessageBox.warning(self, 'No Name Entered', 'No name was entered.')
        else:
            self.accept()


class EnumValueDeletionMessageBox(QMessageBox):
    def __init__(self, selectedRows):
        super().__init__()
        self.setModal(True)
        self.setWindowIcon(QIcon('sources/icons/PyStrato.png'))
        self.setIcon(QMessageBox.Question)
        self.setWindowTitle('Confirmation')
        self.setText(f'You are going to delete {len(selectedRows)} values(s).\n Do you want to proceed?')
        self.addButton(QMessageBox.Yes)
        self.addButton(QMessageBox.No)
        self.setDefaultButton(QMessageBox.No)


# STRUCTURES -----------------------------------------------------------------------------
class StructureEditorWidget(QWidget):
    elementEditCreation = pyqtSignal(QWidget)
    change = pyqtSignal()

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

        # MAIN LAYOUT
        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.elementTable)
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
            # BUTTON NAME
            if category in ['Simple', 'Array', 'Advanced'] or child.baseTypeName in list(
                    self.database.dataTypes.keys()):
                buttonName = child.baseTypeName
                if buttonName in self.baseTypesValues:
                    buttonName = self.baseTypeNames[self.baseTypesValues.index(buttonName)]
            else:
                buttonName = category
            editButton = QPushButton(buttonName)
            editButton.clicked.connect(self.typeButtonClicked)
            self.elementTable.setCellWidget(rowPosition, 1, editButton)
            descriptionItem = QTableWidgetItem(child.description)
            self.elementTable.setItem(row, 2, descriptionItem)

    def addElement(self):
        dialog = ElementAdditionDialog(self.database, self.dataType)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            elementCategoryIndex = dialog.stackedWidget.currentIndex()
            category = ['Enum', 'Structure', 'Other'][elementCategoryIndex]
            rowPosition = self.elementTable.rowCount()
            self.elementTable.insertRow(rowPosition)
            itemName = QTableWidgetItem(dialog.elementName)
            self.elementTable.setItem(rowPosition, 0, itemName)
            if category in ['Enum', 'Structure']:
                editButton = QPushButton(category)
            else:
                buttonName = dialog.elementType
                if buttonName in self.baseTypesValues:
                    buttonName = self.baseTypeNames[self.baseTypesValues.index(buttonName)]
                editButton = QPushButton(buttonName)
            editButton.clicked.connect(self.editDataTypeClicked)
            self.elementTable.setCellWidget(rowPosition, 1, editButton)
            descriptionItem = QTableWidgetItem('')
            self.elementTable.setItem(rowPosition, 2, descriptionItem)
            # TODO : Add code to add element in struct
            self.change.emit()

    def typeButtonClicked(self):
        senderWidget = self.sender()
        if isinstance(senderWidget, QPushButton):
            row = self.elementTable.indexAt(senderWidget.pos()).row()
            name = self.elementTable.item(row, 0).text()
            baseType, dataType = senderWidget.text(), self.structureInfo.type[name]
            dataTypes = [self.dataType, name] if not isinstance(self.dataType, list) else self.dataType + [name]
            if baseType == 'Enum':
                editor = EnumEditorWidget(self.database, dataTypes)
                self.elementEditCreation.emit(editor)
            elif baseType == 'Structure':
                editor = StructureEditorWidget(self.database, dataTypes)
                self.elementEditCreation.emit(editor)
            else:
                print(self.dataType)
                dialog = TypeSelector(self.database, typeName=baseType, dataType=dataTypes[0], haveDataTypes=True)
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
