# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CartoLineGen
                                 A QGIS plugin
 Generalize lines suitable for presentation on printed or screen maps.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2018-06-19
        git sha              : $Format:%H$
        copyright            : (C) 2018 by Drazen Tutic / Faculty of Geodesy, University of Zagreb
        email                : dtutic@geof.hr
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .cartolinegen_dialog import CartoLineGenDialog
import os.path

from PyQt5.QtWidgets import QFileDialog
from qgis.gui import QgsMessageBar
from .generalize import Generalize
from qgis.core import *
import qgis
import datetime

class CartoLineGen:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'CartoLineGen_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = CartoLineGenDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Cartographic Line Generalization')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'CartoLineGen')
        self.toolbar.setObjectName(u'CartoLineGen')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('CartoLineGen', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/cartolinegen/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Cartographic Line Generalization'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Cartographic Line Generalization'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar


    def run(self):
        """Run method that performs all the real work"""
        #round canvas map scale to 1000, results of generalisation are not that much sensitive to exact scale denominator
        self.dlg.dlg_scale.setText(str(int(self.iface.mapCanvas().scale()/1000+1e-12)*1000))
        #reset output file dialog
        self.dlg.dlg_file.setStorageMode(3)
        self.dlg.dlg_file.setFilePath('')
        #connect counting of vertices when layer or selected features are changed in order to estimate time
        self.dlg.dlg_layer.currentIndexChanged.connect(self.count_vertices) 
        self.dlg.dlg_selected.stateChanged.connect(self.count_vertices)
        #populate vector layers with lines or polygons into layer combo box
        layers = QgsProject.instance().mapLayers().values()
        self.dlg.dlg_layer.clear()
        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer and (layer.geometryType() == QgsWkbTypes.LineString or layer.geometryType() == QgsWkbTypes.Polygon):
                self.dlg.dlg_layer.addItem( layer.name(), layer ) 
        #count vertices if there is layer in project in order to show it when dialog is loaded
        layer = self.dlg.dlg_layer.itemData(self.dlg.dlg_layer.currentIndex())
        if layer is None: #no input layer 
            qgis.utils.iface.messageBar().pushMessage("Error", "No layer to generalize!", level=Qgis.Critical, duration=10)
            return -1
        else:
            self.count_vertices()
        #execute dialog    
        result = self.dlg.exec_()
        if result:
            #check if valid output filename is given
            filePath = self.dlg.dlg_file.filePath()
            if os.path.exists(filePath) or os.access(os.path.dirname(filePath), os.W_OK):
                count = self.count_vertices()
                info = "Performing generalisation. Started at "+str(datetime.datetime.now().time()).split('.')[0]+". It can take up to "+ str(int(count/400000)+1)+" min! Please wait until it finishes."
                qgis.utils.iface.messageBar().pushMessage("Info", info, level=Qgis.Info, duration=84600)
                try:
                    self.generalize()
                except:
                    qgis.utils.iface.messageBar().pushMessage("Error", "Can't generalize! Check geometry validity.", level=Qgis.Critical, duration=10)
            else:        
                qgis.utils.iface.messageBar().pushMessage("Error", "Invalid output file given!", level=Qgis.Critical, duration=10)
            
    def count_vertices(self):
        inLayer = self.dlg.dlg_layer.itemData(self.dlg.dlg_layer.currentIndex())
        if inLayer is not None and inLayer.type() == 0: #Layer is vector
            #check if only selected objects are to be generalized           
            if self.dlg.dlg_selected.isChecked():
                feat = inLayer.selectedFeatures()
            else:    
                feat = inLayer.getFeatures()
            #estimate number of vertices from wkbSize/16, it is much faster than counting vertices
            count = sum([feature.geometry().asWkb().length() for feature in feat])/16
            #round estimated number of vertices to 100
            count = int(count/100+1)*100
            if count > 0:
                #estimate time needed for generalisation and warn user that it can take up a while
                self.dlg.dlg_warning.setText("~"+str(count)+" vertices. Generalisation can take up to "+ str(int(count/400000)+1)+" min!")
                return count
            else:    
                self.dlg.dlg_warning.setText("No features selected! Output file will be empty.")
        else:        
            self.dlg.dlg_warning.setText("Please select a vector layer to generalize!")

    def generalize(self):
        inLayer = self.dlg.dlg_layer.itemData(self.dlg.dlg_layer.currentIndex())
        #check if layer is in projected CRS, current approach makes no sense for geographic coordinates
        #if one still wants to generalize in geographic coordinates layer CRS should be changed manually to projected CRS
        if not inLayer.crs().isGeographic():
            #create temporary shapefile filename, it will be used as input by external process "generalize.py" which uses GDAL/OGR
            inFile = os.path.dirname(inLayer.dataProvider().dataSourceUri())+'temp.shp'
            #check if only selected objects are to be generalized           
            sel = self.dlg.dlg_selected.isChecked()
            #sometimes layer can have malformed geometries, so select all valid features for save
            if not sel:
                inLayer.selectAll()                  
            #save to temporary file because GDAL/OGR functions are used to access geometries and write generalised lines    
            error = QgsVectorFileWriter.writeAsVectorFormat(inLayer, inFile, "UTF-8", inLayer.crs(), "ESRI Shapefile", True)
            if error != QgsVectorFileWriter.NoError:
                qgis.utils.iface.messageBar().pushMessage("Error", "Can't create temporary copy of selected layer in "+inFile, level=Qgis.Critical, duration=10)
            #set selection to previous state, in fact deselect object if no features were selected in the first place
            if not sel:
                inLayer.removeSelection()
            #scale is main parameter of algorithm    
            scale = float(self.dlg.dlg_scale.text())
            #check if small polygons should be filtered out by area threshold: 0.5 mm2 in map scale
            #too small lines are never removed for these can break topology
            if self.dlg.dlg_remove_small.isChecked():
                area = 0.5
            else:
                area = 0            
            #set output filename    
            outFile = self.dlg.dlg_file.filePath()
            #type of generalisation: simplification&smoothing = 0, only simplification =1 or only smoothing=2
            alg_type = self.dlg.dlg_type.currentIndex()
            
            #call generalisation algorithm which is based on python GDAL/OGR API
            print(scale, area,alg_type,inFile,outFile)
            Generalize(scale,area,alg_type,inFile,outFile)
            qgis.utils.iface.messageBar().clearWidgets()
            qgis.utils.iface.messageBar().pushMessage("Success", str(datetime.datetime.now().time()).split('.')[0]+" : Generalisation finished and data saved to "+outFile, level=Qgis.Success, duration=10)
            
            #check if to load output and add layer to map canvas
            if self.dlg.dlg_add.isChecked():
                outLayer = self.iface.addVectorLayer(outFile, inLayer.name()+"_generalized_to_1:"+str(int(scale)), "ogr")
                if not outLayer:
                    qgis.utils.iface.messageBar().pushMessage("Error", "Can't open generalised layer!", level=Qgis.Critical, duration=10)
            #remove temp files
            os.remove(os.path.dirname(inLayer.dataProvider().dataSourceUri())+'temp.dbf')
            os.remove(os.path.dirname(inLayer.dataProvider().dataSourceUri())+'temp.prj')
            os.remove(os.path.dirname(inLayer.dataProvider().dataSourceUri())+'temp.qpj')
            os.remove(os.path.dirname(inLayer.dataProvider().dataSourceUri())+'temp.shp')
            os.remove(os.path.dirname(inLayer.dataProvider().dataSourceUri())+'temp.shx')
            os.remove(os.path.dirname(inLayer.dataProvider().dataSourceUri())+'temp.cpg')
        else:    
            qgis.utils.iface.messageBar().clearWidgets()
            qgis.utils.iface.messageBar().pushMessage("Error", "Layer must be in projected coordinate reference system (CRS)!", level=Qgis.Critical, duration=10)