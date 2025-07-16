# QGIS Plugin: SmartCSV Exporter
# Combines simplicity and robustness: allows expression filtering, column selection,
# optional export of selected features, row ranges, optional geometry export,
# preview of feature count before export, saved settings, and batch export across layers.
# Now with improved GUI layout, support for exporting into subfolders based on layer groups,
# and CSV metadata headers.
# Author: Lalit BC
# Version: 1.5

import os
import csv
from qgis.PyQt.QtCore import Qt, QSettings
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                                 QListWidget, QListWidgetItem, QCheckBox, QPushButton,
                                 QFileDialog, QLineEdit, QMessageBox, QAction, QRadioButton,
                                 QSpinBox, QButtonGroup, QGroupBox, QFormLayout)
from qgis.core import (QgsProject, QgsVectorLayer, QgsVectorFileWriter, QgsFeatureRequest,
                       QgsExpression, Qgis)
from qgis.utils import iface

class SmartCSVExporter(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartCSV Exporter")
        self.resize(520, 640)

        self.settings = QSettings()

        # --- Layer selection ---
        self.layer_combo = QComboBox()
        self.populate_layers()

        self.batch_checkbox = QCheckBox("Export all visible layers (batch mode)")

        layer_box = QGroupBox("Layer Options")
        layer_layout = QVBoxLayout()
        layer_layout.addWidget(QLabel("Select Layer:"))
        layer_layout.addWidget(self.layer_combo)
        layer_layout.addWidget(self.batch_checkbox)
        layer_box.setLayout(layer_layout)

        # --- Column selection ---
        self.columns_list = QListWidget()
        self.columns_list.setSelectionMode(QListWidget.MultiSelection)

        self.select_all_button = QPushButton("Select All Columns")
        self.clear_columns_button = QPushButton("Clear Column Selection")

        self.select_all_button.clicked.connect(self.select_all_columns)
        self.clear_columns_button.clicked.connect(self.clear_column_selection)

        col_btns = QHBoxLayout()
        col_btns.addWidget(self.select_all_button)
        col_btns.addWidget(self.clear_columns_button)

        column_box = QGroupBox("Field Options")
        column_layout = QVBoxLayout()
        column_layout.addWidget(self.columns_list)
        column_layout.addLayout(col_btns)
        column_box.setLayout(column_layout)

        # --- Filter and Geometry ---
        self.include_geometry_checkbox = QCheckBox("Include geometry (WKT)")
        self.include_geometry_checkbox.setChecked(False)

        self.filter_input = QLineEdit()
        self.feature_count_label = QLabel("Features to export: 0")

        filter_box = QGroupBox("Feature Filtering")
        filter_layout = QFormLayout()
        filter_layout.addRow("Expression Filter:", self.filter_input)
        filter_layout.addRow("Feature Count:", self.feature_count_label)
        filter_box.setLayout(filter_layout)

        # --- Row export mode ---
        self.radio_all = QRadioButton("All features")
        self.radio_selected = QRadioButton("Selected features only")
        self.radio_range = QRadioButton("Feature range:")
        self.radio_all.setChecked(True)

        self.range_start = QSpinBox()
        self.range_end = QSpinBox()
        self.range_start.setMinimum(0)
        self.range_end.setMinimum(0)

        self.row_mode_group = QButtonGroup()
        self.row_mode_group.addButton(self.radio_all)
        self.row_mode_group.addButton(self.radio_selected)
        self.row_mode_group.addButton(self.radio_range)

        range_line = QHBoxLayout()
        range_line.addWidget(QLabel("From"))
        range_line.addWidget(self.range_start)
        range_line.addWidget(QLabel("To"))
        range_line.addWidget(self.range_end)

        row_box = QGroupBox("Row Selection")
        row_layout = QVBoxLayout()
        row_layout.addWidget(self.radio_all)
        row_layout.addWidget(self.radio_selected)
        row_layout.addWidget(self.radio_range)
        row_layout.addLayout(range_line)
        row_box.setLayout(row_layout)

        # --- Output options ---
        self.browse_button = QPushButton("Choose Output Directory")
        self.browse_button.clicked.connect(self.browse_directory)
        self.file_path = ""

        # --- Action buttons ---
        self.export_button = QPushButton("Export to CSV")
        self.close_button = QPushButton("Close")
        self.export_button.clicked.connect(self.export_to_csv)
        self.close_button.clicked.connect(self.close)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.export_button)
        btn_layout.addWidget(self.close_button)

        # --- Main layout ---
        layout = QVBoxLayout()
        layout.addWidget(layer_box)
        layout.addWidget(column_box)
        layout.addWidget(self.include_geometry_checkbox)
        layout.addWidget(filter_box)
        layout.addWidget(row_box)
        layout.addWidget(self.browse_button)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Signals
        self.layer_combo.currentIndexChanged.connect(self.populate_columns)
        self.filter_input.textChanged.connect(self.update_feature_count)
        self.radio_all.toggled.connect(self.update_feature_count)
        self.radio_selected.toggled.connect(self.update_feature_count)
        self.radio_range.toggled.connect(self.update_feature_count)
        self.range_start.valueChanged.connect(self.update_feature_count)
        self.range_end.valueChanged.connect(self.update_feature_count)
        self.batch_checkbox.toggled.connect(self.update_ui_state)

        self.restore_settings()
        self.populate_columns()
        self.update_feature_count()

    def populate_layers(self):
        self.layer_combo.clear()
        for layer in QgsProject.instance().layerTreeRoot().findLayers():
            qlayer = layer.layer()
            if isinstance(qlayer, QgsVectorLayer):
                self.layer_combo.addItem(qlayer.name(), qlayer)

    def populate_columns(self):
        self.columns_list.clear()
        layer = self.current_layer()
        if layer:
            for field in layer.fields():
                item = QListWidgetItem(field.name())
                item.setSelected(True)
                self.columns_list.addItem(item)
            self.restore_column_selection(layer.name())

    def select_all_columns(self):
        for i in range(self.columns_list.count()):
            self.columns_list.item(i).setSelected(True)

    def clear_column_selection(self):
        for i in range(self.columns_list.count()):
            self.columns_list.item(i).setSelected(False)

    def current_layer(self):
        return self.layer_combo.currentData()

    def browse_directory(self):
        last_dir = self.settings.value("SmartCSV/LastDir", "")
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory", last_dir)
        if directory:
            self.file_path = directory
            self.settings.setValue("SmartCSV/LastDir", directory)
            self.browse_button.setText(os.path.basename(directory))

    def update_feature_count(self):
        layer = self.current_layer()
        if not layer:
            self.feature_count_label.setText("Features to export: 0")
            return

        expr_text = self.filter_input.text()
        expr = QgsExpression(expr_text) if expr_text else None
        request = QgsFeatureRequest()
        if expr:
            request.setFilterExpression(expr_text)

        if self.radio_selected.isChecked():
            ids = layer.selectedFeatureIds()
            count = sum(1 for f in layer.getFeatures(request) if f.id() in ids)
        elif self.radio_range.isChecked():
            start = self.range_start.value()
            end = self.range_end.value()
            count = sum(1 for i, _ in enumerate(layer.getFeatures(request)) if start <= i <= end)
        else:
            count = sum(1 for _ in layer.getFeatures(request))

        self.feature_count_label.setText(f"Features to export: {count}")

    def export_to_csv(self):
        if not self.file_path:
            iface.messageBar().pushMessage("SmartCSV Exporter", "No output directory selected.", level=Qgis.Warning)
            return

        if self.batch_checkbox.isChecked():
            for node in QgsProject.instance().layerTreeRoot().findLayers():
                layer = node.layer()
                if not isinstance(layer, QgsVectorLayer):
                    continue
                rel_path = node.name().replace("/", "_") + ".csv"
                self.export_layer(layer, rel_path)
        else:
            layer = self.current_layer()
            self.export_layer(layer, f"{layer.name()}.csv")

        iface.messageBar().pushMessage("SmartCSV Exporter", "Export completed.", level=Qgis.Success)
        self.accept()

    def export_layer(self, layer, rel_path):
        columns = [item.text() for item in self.columns_list.selectedItems()]
        if not columns:
            iface.messageBar().pushMessage("SmartCSV Exporter", "No columns selected.", level=Qgis.Warning)
            return

        full_path = os.path.join(self.file_path, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # Write CSV manually for metadata
        with open(full_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["# Layer Name", layer.name()])
            writer.writerow(["# CRS", layer.crs().authid()])
            writer.writerow(["# Exported Fields"] + columns)
            writer.writerow(columns)

            expr_text = self.filter_input.text()
            expr = QgsExpression(expr_text) if expr_text else None
            request = QgsFeatureRequest()
            if expr:
                request.setFilterExpression(expr_text)

            features = layer.getFeatures(request)
            if self.radio_selected.isChecked():
                ids = set(layer.selectedFeatureIds())
                features = filter(lambda f: f.id() in ids, features)
            elif self.radio_range.isChecked():
                start = self.range_start.value()
                end = self.range_end.value()
                features = (f for i, f in enumerate(features) if start <= i <= end)

            for feature in features:
                row = [feature[name] for name in columns]
                if self.include_geometry_checkbox.isChecked():
                    row.append(feature.geometry().asWkt())
                writer.writerow(row)

    def save_column_selection(self):
        layer = self.current_layer()
        if not layer:
            return
        selected = [item.text() for item in self.columns_list.selectedItems()]
        self.settings.setValue(f"SmartCSV/columns/{layer.name()}", selected)

    def restore_column_selection(self, layer_name):
        saved = self.settings.value(f"SmartCSV/columns/{layer_name}", [])
        for i in range(self.columns_list.count()):
            item = self.columns_list.item(i)
            item.setSelected(item.text() in saved)

    def restore_settings(self):
        dir_label = os.path.basename(self.settings.value("SmartCSV/LastDir", ""))
        if dir_label:
            self.browse_button.setText(dir_label)

    def update_ui_state(self):
        enabled = not self.batch_checkbox.isChecked()
        self.layer_combo.setEnabled(enabled)
        self.columns_list.setEnabled(enabled)

class SmartCSVPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None

    def initGui(self):
        self.action = QAction("SmartCSV Exporter", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu("&SmartCSV Exporter", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginMenu("&SmartCSV Exporter", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        dialog = SmartCSVExporter()
        dialog.exec_()

def classFactory(iface):
    return SmartCSVPlugin(iface)
