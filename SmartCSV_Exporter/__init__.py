# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SmartCSV Exporter
                                 A QGIS Plugin
 Export selected or filtered features with selected columns to CSV.
                              -------------------
        begin                : 2025-07-16
        copyright            : (C) 2025 by Lalit BC
        email                : mapmentorsx@gmail.com
 ***************************************************************************/
"""

def classFactory(iface):  # QGIS calls this to instantiate the plugin
    from .main import SmartCSVPlugin
    return SmartCSVPlugin(iface)
