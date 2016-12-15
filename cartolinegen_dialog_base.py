# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'cartolinegen_dialog_base.ui'
#
# Created: Thu Dec 15 09:47:49 2016
#      by: PyQt4 UI code generator 4.10.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_CartoLineGenDialogBase(object):
    def setupUi(self, CartoLineGenDialogBase):
        CartoLineGenDialogBase.setObjectName(_fromUtf8("CartoLineGenDialogBase"))
        CartoLineGenDialogBase.resize(442, 425)
        self.button_box = QtGui.QDialogButtonBox(CartoLineGenDialogBase)
        self.button_box.setGeometry(QtCore.QRect(80, 380, 341, 32))
        self.button_box.setOrientation(QtCore.Qt.Horizontal)
        self.button_box.setStandardButtons(QtGui.QDialogButtonBox.Close|QtGui.QDialogButtonBox.Ok)
        self.button_box.setObjectName(_fromUtf8("button_box"))
        self.label = QtGui.QLabel(CartoLineGenDialogBase)
        self.label.setGeometry(QtCore.QRect(20, 20, 251, 16))
        self.label.setObjectName(_fromUtf8("label"))
        self.dlg_layer = QgsMapLayerComboBox(CartoLineGenDialogBase)
        self.dlg_layer.setGeometry(QtCore.QRect(20, 50, 401, 27))
        self.dlg_layer.setFilters(gui.QgsMapLayerProxyModel.LineLayer|gui.QgsMapLayerProxyModel.PolygonLayer)
        self.dlg_layer.setObjectName(_fromUtf8("dlg_layer"))
        self.label_2 = QtGui.QLabel(CartoLineGenDialogBase)
        self.label_2.setGeometry(QtCore.QRect(20, 130, 151, 10))
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.dlg_scale = QtGui.QLineEdit(CartoLineGenDialogBase)
        self.dlg_scale.setGeometry(QtCore.QRect(170, 120, 151, 22))
        self.dlg_scale.setObjectName(_fromUtf8("dlg_scale"))
        self.dlg_selected = QtGui.QCheckBox(CartoLineGenDialogBase)
        self.dlg_selected.setGeometry(QtCore.QRect(20, 90, 191, 20))
        self.dlg_selected.setObjectName(_fromUtf8("dlg_selected"))
        self.dlg_file = QtGui.QLineEdit(CartoLineGenDialogBase)
        self.dlg_file.setEnabled(True)
        self.dlg_file.setGeometry(QtCore.QRect(20, 273, 301, 22))
        self.dlg_file.setObjectName(_fromUtf8("dlg_file"))
        self.dlg_browse = QtGui.QPushButton(CartoLineGenDialogBase)
        self.dlg_browse.setEnabled(True)
        self.dlg_browse.setGeometry(QtCore.QRect(330, 266, 93, 30))
        self.dlg_browse.setObjectName(_fromUtf8("dlg_browse"))
        self.dlg_add = QtGui.QCheckBox(CartoLineGenDialogBase)
        self.dlg_add.setEnabled(True)
        self.dlg_add.setGeometry(QtCore.QRect(20, 313, 151, 20))
        self.dlg_add.setChecked(True)
        self.dlg_add.setObjectName(_fromUtf8("dlg_add"))
        self.label_3 = QtGui.QLabel(CartoLineGenDialogBase)
        self.label_3.setGeometry(QtCore.QRect(20, 247, 251, 16))
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.dlg_remove_small = QtGui.QCheckBox(CartoLineGenDialogBase)
        self.dlg_remove_small.setGeometry(QtCore.QRect(230, 90, 191, 20))
        self.dlg_remove_small.setChecked(True)
        self.dlg_remove_small.setObjectName(_fromUtf8("dlg_remove_small"))
        self.dlg_warning = QtGui.QLabel(CartoLineGenDialogBase)
        self.dlg_warning.setGeometry(QtCore.QRect(20, 350, 401, 16))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.dlg_warning.setFont(font)
        self.dlg_warning.setText(_fromUtf8(""))
        self.dlg_warning.setObjectName(_fromUtf8("dlg_warning"))
        self.dlg_type = QtGui.QComboBox(CartoLineGenDialogBase)
        self.dlg_type.setGeometry(QtCore.QRect(170, 160, 251, 22))
        self.dlg_type.setObjectName(_fromUtf8("dlg_type"))
        self.dlg_type.addItem(_fromUtf8(""))
        self.dlg_type.addItem(_fromUtf8(""))
        self.dlg_type.addItem(_fromUtf8(""))
        self.dlg_type.addItem(_fromUtf8(""))
        self.label_4 = QtGui.QLabel(CartoLineGenDialogBase)
        self.label_4.setGeometry(QtCore.QRect(20, 160, 121, 30))
        self.label_4.setObjectName(_fromUtf8("label_4"))

        self.retranslateUi(CartoLineGenDialogBase)
        QtCore.QObject.connect(self.button_box, QtCore.SIGNAL(_fromUtf8("accepted()")), CartoLineGenDialogBase.accept)
        QtCore.QObject.connect(self.button_box, QtCore.SIGNAL(_fromUtf8("rejected()")), CartoLineGenDialogBase.reject)
        QtCore.QMetaObject.connectSlotsByName(CartoLineGenDialogBase)

    def retranslateUi(self, CartoLineGenDialogBase):
        CartoLineGenDialogBase.setWindowTitle(_translate("CartoLineGenDialogBase", "Cartographic Line Generalisation - CartoLineGen", None))
        self.label.setText(_translate("CartoLineGenDialogBase", "Input line or polygon layer to generalise:", None))
        self.label_2.setText(_translate("CartoLineGenDialogBase", "Map scale denominator:", None))
        self.dlg_selected.setText(_translate("CartoLineGenDialogBase", "Use only selected features", None))
        self.dlg_browse.setText(_translate("CartoLineGenDialogBase", "Browse", None))
        self.dlg_add.setText(_translate("CartoLineGenDialogBase", "Add result to canvas", None))
        self.label_3.setText(_translate("CartoLineGenDialogBase", "Specify output file:", None))
        self.dlg_remove_small.setText(_translate("CartoLineGenDialogBase", "Remove too small areas", None))
        self.dlg_type.setItemText(0, _translate("CartoLineGenDialogBase", "Simplification + Smoothing", None))
        self.dlg_type.setItemText(1, _translate("CartoLineGenDialogBase", "Simplification", None))
        self.dlg_type.setItemText(2, _translate("CartoLineGenDialogBase", "Smoothing", None))
        self.dlg_type.setItemText(3, _translate("CartoLineGenDialogBase", "Orthogonal Segments", None))
        self.label_4.setText(_translate("CartoLineGenDialogBase", "Generalisation type:", None))

from qgis import gui
from qgis.gui import QgsMapLayerComboBox
