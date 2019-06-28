from matplotlib.backends.backend_qt5agg \
    import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg \
    import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLineEdit, QHBoxLayout,
                             QLabel, QDialogButtonBox, QPushButton)
from PyQt5.QtCore import pyqtSlot, Qt, QSize
from PyQt5.QtGui import QIcon

import mne
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg \
    import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg \
    import NavigationToolbar2QT as NavigationToolbar

from matplotlib.colors import ListedColormap

white = np.array([[0, 0, 0, 0]])
cmp = ListedColormap(white)


class RotateMontageDialog(QDialog):
    def __init__(self, parent, montage):
        super().__init__(parent)
        self.resize(800, 800)
        vbox = QVBoxLayout(self)
        self.plotLayout = QVBoxLayout(self)
        vbox.addLayout(self.plotLayout)

        self.figure = plt.figure(figsize=(10, 10))
        self.figure.patch.set_facecolor('None')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet('background-color:transparent;')
        self.plotLayout.addWidget(self.canvas)
        self.montage = montage

        hbox = QHBoxLayout(self)
        self.cw_button = QPushButton()
        self.cw_button.setIcon(QIcon.fromTheme('object-rotate-right'))
        self.anticw_button = QPushButton()
        self.anticw_button.setIcon(QIcon.fromTheme('object-rotate-left'))
        hbox.addWidget(self.cw_button)
        hbox.addWidget(self.anticw_button)

        self.cw_button.clicked.connect(lambda: self.rotate())
        self.anticw_button.clicked.connect(lambda: self.rotate(anti=True))
        vbox.addLayout(hbox)

        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        self.plot()

    def get_montage(self):
        return self.montage

    def plot(self):
        self.figure.clear()
        ax = self.figure.add_subplot(1, 1, 1)
        data = [0] * len(self.montage.pos)
        mne.viz.plot_topomap(data, self.montage.get_pos2d(), axes=ax,
                             names=self.montage.ch_names, show_names=True,
                             sensors=",", show=False, cmap=cmp)
        self.canvas.draw()

    def rotate(self, anti=False):
        pos = self.montage.pos
        if anti:
            rot_matrix = [[0, 1, 0], [-1, 0, 0], [0, 0, 1]]
        else:
            rot_matrix = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
        new_pos = np.dot(pos, rot_matrix)
        self.montage = mne.channels.Montage(
            new_pos, self.montage.ch_names,
            kind=self.montage.kind,
            selection=[i for i in range(len(new_pos))])
        self.plot()
