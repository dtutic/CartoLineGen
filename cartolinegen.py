# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CartoLineGen
                                 A QGIS plugin
 Simplify and smooth lines for given map scale.
                              -------------------
        begin                : 2016-05-25
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Dražen Tutić, University of Zagreb, Faculty of Geodesy
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

from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from cartolinegen_dialog import CartoLineGenDialog
from PyQt4.QtGui import QFileDialog
from qgis.gui import QgsMessageBar
import os.path
import generalize
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
        self.menu = self.tr(u'&Cartographic Line Generalisation')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'CartoLineGen')
        self.toolbar.setObjectName(u'CartoLineGen')

        # Connect dialog signals to methods
        self.dlg.dlg_browse.clicked.connect(self.browseForFile) # select file to save to


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

        icon_path = ':/plugins/CartoLineGen/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Cartographic Line Generalisation'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Cartographic Line Generalisation'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def browseForFile(self):
        self.dlg.dlg_file.setText(QFileDialog.getSaveFileName(self.dlg, "Save as ESRI Shapefile", "",
                                                 'ESRI Shapefiles (*.shp)'))   
        
    
    def run(self):
        """Run method that performs all the real work"""
        #clear output filename
        self.dlg.dlg_file.setText('')
        #round canvas map scale to 1000, results of generalisation are not that much sensitive to precise scale
        self.dlg.dlg_scale.setText(str(int(self.iface.mapCanvas().scale()/1000+1e-12)*1000))
        #connect counting of vertices when layer or selected features are changed in order to estimate time
        self.dlg.dlg_layer.currentIndexChanged.connect(self.count_vertices) 
        self.dlg.dlg_selected.stateChanged.connect(self.count_vertices)
        layers = QgsMapLayerRegistry.instance().mapLayers().values()
        self.dlg.dlg_layer.clear()
        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer and (layer.geometryType() == QGis.Line or layer.geometryType() == QGis.Polygon):
                self.dlg.dlg_layer.addItem( layer.name(), layer ) 
        
        #count vertices if there is layer in project in order to show it when dialog is loaded
        index = self.dlg.dlg_layer.currentIndex()
        layer = self.dlg.dlg_layer.itemData(index)
        if layer is None: #no input layer 
            qgis.utils.iface.messageBar().pushMessage("Error", "No layer to generalize!", level=QgsMessageBar.CRITICAL, duration=10)
            return -1
        else:
            self.count_vertices()
        #execute dialog    
        result = self.dlg.exec_()
        if result:
            #check if valid output filename is given
            filePath = self.dlg.dlg_file.text()
            if os.path.exists(filePath) or os.access(os.path.dirname(filePath), os.W_OK):
                count = self.count_vertices()
                info = "Performing generalisation. Started at "+str(datetime.datetime.now().time()).split('.')[0]+". It can take up to "+ str(int(count/400000)+1)+" min! Please wait until it finishes."
                qgis.utils.iface.messageBar().pushMessage("Info", info, level=QgsMessageBar.INFO, duration=84600)
                try:
                    self.generalize()
                except:
                    qgis.utils.iface.messageBar().pushMessage("Error", "Can't generalize! Check geometry validity.", level=QgsMessageBar.CRITICAL, duration=10)
            else:        
                qgis.utils.iface.messageBar().pushMessage("Error", "Invalid output file given!", level=QgsMessageBar.CRITICAL, duration=10)
            
    def count_vertices(self):
        index = self.dlg.dlg_layer.currentIndex()
        inLayer = self.dlg.dlg_layer.itemData(index)
        if inLayer is not None and inLayer.type() == 0: #Layer is vector
            #check if only selected objects are to be generalized           
            if self.dlg.dlg_selected.isChecked():
                feat = inLayer.selectedFeatures()
            else:    
                feat = inLayer.getFeatures()
            #estimate number of vertices from wkbSize/16, it is much faster than counting vertices
            count = sum([feature.geometry().wkbSize() for feature in feat])/16
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
        index = self.dlg.dlg_layer.currentIndex()
        inLayer = self.dlg.dlg_layer.itemData(index)
        #check if layer is in projected CRS, current approach makes no sense in geographic coordinates
        #if one still wants to generalize in geographic coordinates layer CRS should be changed manually to projected CRS
        if not inLayer.crs().geographicFlag():
            #create temporary shapefile filename, it will be used as input by external process "generalize.py" which uses GDAL/OGR
            inFile = os.path.dirname(inLayer.dataProvider().dataSourceUri())+'temp.shp'
            #check if only selected objects are to be generalized           
            sel = self.dlg.dlg_selected.isChecked()
            #sometimes layer can have malformed geometries, so select all valid features for save
            if not sel:
                inLayer.selectAll()                  
            #save to temporary file because GDAL/OGR functions are used to access geometries and write generalised lines    
            error = QgsVectorFileWriter.writeAsVectorFormat(inLayer, inFile, "UTF-8", None, "ESRI Shapefile", onlySelected=True)
            if error != QgsVectorFileWriter.NoError:
                qgis.utils.iface.messageBar().pushMessage("Error", "Can't create temporary copy of selected layer in "+inFile, level=QgsMessageBar.CRITICAL, duration=10)
            #set selection to previous state, in fact deselect object for no features were selected in first place
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
            outFile = self.dlg.dlg_file.text()
            #type of generalisation: simplification&smoothing = 0, only simplification =1 or only smoothing=2
            alg_type = self.dlg.dlg_type.currentIndex()
            
            #call generalisation algorithm which is based on python GDAL/OGR API
            generalize.Generalize(scale,area,alg_type,inFile,outFile)
            qgis.utils.iface.messageBar().clearWidgets()
            qgis.utils.iface.messageBar().pushMessage("Success", str(datetime.datetime.now().time()).split('.')[0]+" : Generalisation finished and data saved to "+outFile, level=QgsMessageBar.SUCCESS, duration=10)
            
            #check if to load output and add layer to map canvas
            if self.dlg.dlg_add.isChecked():
                outLayer = self.iface.addVectorLayer(outFile, inLayer.name()+"_generalised", "ogr")
                if not outLayer:
                    qgis.utils.iface.messageBar().pushMessage("Error", "Can't open generalised layer!", level=QgsMessageBar.CRITICAL, duration=10)
            #remove temp files
            os.remove(os.path.dirname(inLayer.dataProvider().dataSourceUri())+'temp.dbf')
            os.remove(os.path.dirname(inLayer.dataProvider().dataSourceUri())+'temp.prj')
            os.remove(os.path.dirname(inLayer.dataProvider().dataSourceUri())+'temp.qpj')
            os.remove(os.path.dirname(inLayer.dataProvider().dataSourceUri())+'temp.shp')
            os.remove(os.path.dirname(inLayer.dataProvider().dataSourceUri())+'temp.shx')
            os.remove(os.path.dirname(inLayer.dataProvider().dataSourceUri())+'temp.cpg')
        else:    
            qgis.utils.iface.messageBar().clearWidgets()
            qgis.utils.iface.messageBar().pushMessage("Error", "Layer must be in projected coordinate reference system (CRS)!", level=QgsMessageBar.CRITICAL, duration=10)
