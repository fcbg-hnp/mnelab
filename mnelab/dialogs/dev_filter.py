from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QLabel,
                             QSpinBox, QComboBox, QDialogButtonBox, QCheckBox,
                             QGroupBox, QMessageBox, QListWidget)
from PyQt5.QtCore import Qt, pyqtSlot


from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QLabel,
                             QLineEdit, QDialogButtonBox)

from PyQt5.QtWidgets import QMainWindow

class FirFilterDialog(QDialog):
    def __init__(self, parent, raw):
        super().__init__(parent)
        self.setWindowTitle("Filter data")
        self.raw= raw
        vbox = QVBoxLayout(self)
        grid = QGridLayout()

        grid.addWidget(QLabel("Lower pass-band edge (Hz):"), 0, 0)
        self.lowedit = QLineEdit()
        self.lowedit.setToolTip("Lower pass-band edge")
        grid.addWidget(self.lowedit, 0, 1)

        grid.addWidget(QLabel("Upper pass-band edge (Hz):"), 1, 0)
        self.highedit = QLineEdit()
        self.highedit.setToolTip("Lower pass-band edge")
        grid.addWidget(self.highedit, 1, 1)

        grid.addWidget(QLabel("Filter_length:"), 2, 0)
        self.filter_length_edit = QLineEdit()
        self.filter_length_edit.setToolTip("""Length of the FIR filter to use:\n """
                + """‘auto’ (default): The filter length is chosen based"""
                + """ on the size of the transition regions"""
                + """ (6.6 times the reciprocal of the shortest transition """
                + """ band for fir_window=’hamming’ and fir_design=”firwin2”,"""
                + """ and half that for “firwin”). \n """

                + """str: A human-readable time in units of “s” or “ms”"""
                + """ (e.g., “10s” or “5500ms”) will be converted"""
                + """ to that number of samples if phase="zero","""
                + """ or the shortest power-of-two length"""
                + """ at least that duration for phase="zero-double". \n """

                + """ int: Specified length in samples."""
                + """ For fir_design=”firwin”, this should not be used.""")
        self.filter_length_edit.setText("auto")
        grid.addWidget(self.filter_length_edit, 2, 1)

        grid.addWidget(QLabel("l_trans_bandwidthfloat (Hz):"), 3, 0)
        self.l_trans_bandwidth_edit = QLineEdit()
        self.l_trans_bandwidth_edit.setToolTip("""Width of the transition band"""
                + """ at the low cut-off frequency in Hz"""
                + """ (high pass or cutoff 1 in bandpass)."""
                + """ Can be “auto” (default) to use a multiple of l_freq:")""")
        self.l_trans_bandwidth_edit.setText("auto")
        grid.addWidget(self.l_trans_bandwidth_edit, 3, 1)

        grid.addWidget(QLabel("h_trans_bandwidthfloat (Hz):"), 4, 0)
        self.h_trans_bandwidth_edit = QLineEdit()
        self.h_trans_bandwidth_edit.setToolTip("""Width of the transition band"""
                + """ at the high cut-off frequency in Hz"""
                + """ (low pass or cutoff 2 in bandpass)."""
                + """ Can be “auto” (default) to use a multiple of h_freq:")""")
        self.h_trans_bandwidth_edit.setText("auto")
        grid.addWidget(self.h_trans_bandwidth_edit, 4, 1)

        grid.addWidget(QLabel("Phase:"), 5, 0)
        self.phase_edit = QComboBox()
        self.phases = {"Zero": "zero",
                       "Zero-double": "zero-double",
                       "Minimum": "minimum"}
        self.phase_edit.addItems(self.phases.keys())
        self.phase_edit.setToolTip("""if phase='zero',"""
                + """ the delay of this filter is compensated for,"""
                + """ making it non-causal. If phase=='zero-double',"""
                + """ then this filter is applied twice, once forward,"""
                + """ and once backward (also making it non-causal)."""
                + """ If ‘minimum’, then a minimum-phase filter will be """
                + """ constricted and applied, which is causal but has weaker"""
                + """ stop-band suppression.""")
        self.phase_edit.setCurrentText("zero")
        grid.addWidget(self.phase_edit, 5, 1)

        grid.addWidget(QLabel("Fir window:"), 6, 0)
        self.fir_window_edit = QComboBox()
        self.fir_windows = {"Hamming": "hamming",
                            "Hann": "hann",
                            "Blackman": "blackman"}
        self.fir_window_edit.addItems(self.fir_windows.keys())
        self.fir_window_edit.setToolTip("""The window to use in FIR design""")
        self.fir_window_edit.setCurrentText("“hamming”")
        grid.addWidget(self.fir_window_edit, 6, 1)

        grid.addWidget(QLabel("Fir design:"), 7, 0)
        self.fir_design_edit = QComboBox()
        self.fir_designs = {"firwin": "firwin",
                            "firwin2": "firwin2",}
        self.fir_design_edit.addItems(self.fir_designs.keys())
        self.fir_design_edit.setToolTip("""“firwin” uses a time-domain design"""
                + """ technique that generally gives improved attenuation """
                + """ using fewer samples than “firwin2”.""")
        self.fir_design_edit.setCurrentText("firwin")
        grid.addWidget(self.fir_design_edit, 7, 1)

        grid.addWidget(QLabel("Skip by annotation:"), 8, 0)
        self.annotations = list(set(self.raw.annotations.description))
        self.skip_by_annotation_list = QListWidget()
        self.skip_by_annotation_list.insertItems(0, self.annotations)
        self.skip_by_annotation_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.skip_by_annotation_list.setToolTip("""Selected Annotation segment"""
                + """ will not be included in filtering, and segments on"""
                + """ either side of the given excluded annotated segment"""
                + """ will be filtered separately """)
        for i in range(len(self.annotations)):
            if self.annotations[i] in ('edge', 'bad_acq_skip'):
                self.skip_by_annotation_list.item(i).setSelected(True)
            else:
                self.skip_by_annotation_list.item(i).setSelected(False)
        grid.addWidget(self.skip_by_annotation_list, 8, 1)

        grid.addWidget(QLabel("pad:"), 9, 0)
        self.pads_edit = QComboBox()
        self.pads = {"edge": "edge",
                            "linear_ramp": "linear_ramp",
                            "maximum": "maximum",
                            "mean": "mean",
                            "median": "median",
                            "minimum": "minimum",
                            "reflect": "reflect",
                            "wrap": "wrap",
                            "empty": "empty",
                            "reflect-limited": "reflect-limited"}
        self.pads_edit.addItems(self.pads.keys())
        self.pads_edit.setToolTip("""The type of padding to use.""")
        self.pads_edit.setCurrentText("reflect-limited")
        grid.addWidget(self.pads_edit, 9, 1)


        vbox.addLayout(grid)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    @property
    def low(self):
        low = self.lowedit.text()
        return float(low) if low else None

    @property
    def high(self):
        high = self.highedit.text()
        return float(high) if high else None
