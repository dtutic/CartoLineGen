# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CartoLineGen
                                 A QGIS plugin
 Simplify and smooth lines for given map scale.
                             -------------------
        begin                : 2016-05-25
        copyright            : (C) 2016 by Dražen Tutić, University of Zagreb, Faculty of Geodesy
        email                : dtutic@geof.hr
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load CartoLineGen class from file CartoLineGen.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .cartolinegen import CartoLineGen
    return CartoLineGen(iface)
