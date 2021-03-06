from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QLabel,
                             QLineEdit, QDialogButtonBox)
from ..utils.information import show_info


class ResampleDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Resample data")
        vbox = QVBoxLayout(self)
        self.sfreqedit = QLineEdit()
        vbox.addWidget(QLabel("Enter Sampling Frequency..."))
        vbox.addWidget(self.sfreqedit)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    @property
    def sfreq(self):
        sfreq = self.sfreqedit.text()
        try:
            return float(sfreq) if sfreq else None
        except Exception as e:
            show_info('Sampling frequency value was not correctly read.',
                      info=str(e))
            return None
