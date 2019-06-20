from PyQt5.QtWidgets import (QLineEdit, QLabel, QComboBox)
from PyQt5.QtCore import Qt
import multiprocessing as mp

from ..app.error import show_error
from ...dialogs.calcdialog import CalcDialog


# Miscellaneous functions for reading, saving and initializing parameters
# =====================================================================
def clear_layout(layout):
    """Clear layout."""
    for i in reversed(range(layout.count())):
        layout.itemAt(i).widget().setParent(None)


# ---------------------------------------------------------------------
def _init_psd_parameters(self):
    """Set the parameters in the parameters text slot
    """
    clear_layout(self.ui.labels)
    clear_layout(self.ui.lines)
    self.ui.labels.addWidget(QLabel('Fmin (Hz)'))
    self.ui.labels.addWidget(QLabel('Fmax (Hz)'))
    self.ui.labels.addWidget(QLabel('Tmin (s)'))
    self.ui.labels.addWidget(QLabel('Tmax (s)'))
    self.fmin = QLineEdit()
    self.fmax = QLineEdit()
    self.tmin = QLineEdit()
    self.tmax = QLineEdit()
    self.ui.lines.addWidget(self.fmin)
    self.ui.lines.addWidget(self.fmax)
    self.ui.lines.addWidget(self.tmin)
    self.ui.lines.addWidget(self.tmax)

    if self.data.info['lowpass'] is not None:
        self.fmax.setText('{:2.1f}'.format(self.data.info['lowpass']))
    else:
        self.fmax.setText('{:2.1f}'.format(self.data.info['sfreq'] / 2))

    if self.data.info['highpass'] is not None:
        self.fmin.setText('{:2.1f}'.format(self.data.info['highpass']))
    else:
        self.fmin.setText('0')
    self.tmin.setText('{:2.1f}'.format(self.data.times[0]))
    self.tmax.setText('{:2.1f}'.format(self.data.times[-1]))

    if self.ui.psdMethod.currentText() == 'welch':
        self.ui.labels.addWidget(QLabel('FFT points'))
        self.ui.labels.addWidget(QLabel('Length of segments (points)'))
        self.ui.labels.addWidget(QLabel('Overlapping of segments (points)'))
        self.n_fft = QLineEdit()
        self.n_per_seg = QLineEdit()
        self.n_overlap = QLineEdit()
        self.ui.lines.addWidget(self.n_fft)
        self.ui.lines.addWidget(self.n_per_seg)
        self.ui.lines.addWidget(self.n_overlap)
        self.n_fft.setText(str(min(len(self.data.times), 2048)))
        self.n_per_seg.setText(str(int(int(self.n_fft.text()) / 2)))
        self.n_overlap.setText(str(int(int(self.n_fft.text()) / 4)))
    if self.ui.psdMethod.currentText() == 'multitaper':
        self.ui.labels.addWidget(QLabel('Bandwidth (Hz)'))
        self.bandwidth = QLineEdit()
        self.ui.lines.addWidget(self.bandwidth)
        self.bandwidth.setText('4')


# ---------------------------------------------------------------------
def _init_tfr_parameters(self):
    """Set the parameters in the parameters text slot
    """
    clear_layout(self.ui.labels)
    clear_layout(self.ui.lines)
    self.ui.labels.addWidget(QLabel('Fmin (Hz)'))
    self.ui.labels.addWidget(QLabel('Fmax (Hz)'))
    self.fmin = QLineEdit()
    self.fmax = QLineEdit()
    self.ui.lines.addWidget(self.fmin)
    self.ui.lines.addWidget(self.fmax)

    if self.data.info['lowpass'] is not None:
        self.fmax.setText('{:2.1f}'.format(self.data.info['lowpass']))
    else:
        self.fmax.setText('{:2.1f}'.format(self.data.info['sfreq'] / 2))

    if self.data.info['highpass'] is not None:
        self.fmin.setText('{:2.1f}'.format(self.data.info['highpass']))
    else:
        self.fmin.setText('0')

    if self.ui.tfrMethodBox.currentText() == 'multitaper':
        self.ui.labels.addWidget(QLabel('Frequency Step (Hz)'))
        self.tfr_param = QComboBox()
        self.tfr_param.addItem('Time Window (s)')
        self.tfr_param.addItem('Number of cycles')
        self.ui.labels.addWidget(self.tfr_param)
        self.ui.labels.addWidget(QLabel('Time Bandwidth (s.Hz)'))
        self.fstep = QLineEdit()
        self.time_bandwidth = QLineEdit()
        self.cycles = QLineEdit()
        self.ui.lines.addWidget(self.fstep)
        self.ui.lines.addWidget(self.cycles)
        self.ui.lines.addWidget(self.time_bandwidth)
        self.fstep.setText('1')
        self.cycles.setText('0.5')
        self.time_bandwidth.setText('4')
    if self.ui.tfrMethodBox.currentText() == 'morlet':
        self.ui.labels.addWidget(QLabel('Frequency Step (Hz)'))
        self.tfr_param = QComboBox()
        self.tfr_param.addItem('Time Window (s)')
        self.tfr_param.addItem('Number of cycles')
        self.ui.labels.addWidget(self.tfr_param)
        self.fstep = QLineEdit()
        self.cycles = QLineEdit()
        self.ui.lines.addWidget(self.fstep)
        self.ui.lines.addWidget(self.cycles)
        self.fstep.setText('1')
        self.cycles.setText('0.5')
    if self.ui.tfrMethodBox.currentText() == 'stockwell':
        self.ui.labels.addWidget(QLabel('Width'))
        self.ui.labels.addWidget(QLabel('FFT points'))
        self.width = QLineEdit()
        self.n_fft = QLineEdit()
        self.ui.lines.addWidget(self.width)
        self.ui.lines.addWidget(self.n_fft)
        self.width.setText('1')
        self.n_fft.setText(str(min(len(self.data.times), 2048)))


# ---------------------------------------------------------------------
def _save_matrix(self):
    """Save the matrix containing the PSD
    """
    n_files = len(self.filePaths)
    if n_files == 1:
        print('Saving one file ...', end='')
        if self.type == 'epochs':
            self.init_epochs_psd()
        if self.type == 'raw':
            self.init_raw_psd()
        self.psd.save_avg_matrix_sef(self.savepath)
        print('done !')

    else:
        from os.path import basename, splitext, join

        print('Batch Processing of {} files'
              .format(len(self.filePaths)))
        n = 0
        for path in self.filePaths:
            print('Saving file {} out of {} ...'
                  .format(n+1, n_files), end='')
            file_name = splitext(basename(path))[0]
            self.ui.dataFilesBox.setCurrentIndex(0)
            if self.type == 'epochs':
                self.init_epochs_psd()
            if self.type == 'raw':
                self.init_raw_psd()

            savepath = join(self.savepath, file_name + '-PSD.sef')
            self.psd.save_avg_matrix_sef(savepath)
            print('done !')
            n += 1


# ---------------------------------------------------------------------
def _read_psd_parameters(self):
    """Read parameters from txt file and sets it up in params"""

    try:
        self.params = {}
        self.params['fmin'] = float(self.fmin.text())
        self.params['fmax'] = float(self.fmax.text())
        self.params['tmin'] = float(self.tmin.text())
        self.params['tmax'] = float(self.tmax.text())
        if self.ui.psdMethod.currentText() == 'multitaper':
            self.params['bandwidth'] = float(self.bandwidth.text())
        if self.ui.psdMethod.currentText() == 'welch':
            self.params['n_fft'] = int(self.n_fft.text())
            self.params['n_per_seg'] = int(self.n_per_seg.text())
            self.params['n_overlap'] = int(self.n_overlap.text())

    except Exception as e:  # Print exception for parameters
        print(e)


# ---------------------------------------------------------------------
def _read_tfr_parameters(self):
    """Read parameters from txt file and sets it up in params"""

    try:
        self.params = {}
        self.params['fmin'] = float(self.fmin.text())
        self.params['fmax'] = float(self.fmax.text())
        if self.ui.tfrMethodBox.currentText() == 'multitaper':
            self.params['freq_step'] = float(self.fstep.text())
            if self.tfr_param.currentText == 'Time Window (s)':
                self.params['time_window'] = float(self.cycles.text())
                self.params['n_cycles'] = None
            else:
                self.params['n_cycles'] = float(self.cycles.text())
                self.params['time_window'] = None
            self.params['time_bandwidth'] = float(self.time_bandwidth.text())
        if self.ui.tfrMethodBox.currentText() == 'morlet':
            self.params['freq_step'] = float(self.fstep.text())
            if self.tfr_param.currentText == 'Time Window (s)':
                self.params['time_window'] = float(self.cycles.text())
                self.params['n_cycles'] = None
            else:
                self.params['n_cycles'] = float(self.cycles.text())
                self.params['time_window'] = None
        if self.ui.tfrMethodBox.currentText() == 'stockwell':
            self.params['width'] = float(self.width.text())
            self.params['n_fft'] = int(self.n_fft.text())
            self.params['time_window'] = None
            self.params['n_cycles'] = None

    except Exception as e:  # Print exception for parameters
        print(e)


# ---------------------------------------------------------------------
def _init_epochs_psd(self):
    """Initialize the instance of EpochsPSD."""
    from .epochs_psd import EpochsPSD

    if self.ui.psdMethod.currentText() == 'welch':
        n_fft = self.params['n_fft']
        kwds = dict(epochs=self.data,
                    fmin=self.params['fmin'],
                    fmax=self.params['fmax'],
                    tmin=self.params['tmin'],
                    tmax=self.params['tmax'],
                    method='welch',
                    n_fft=n_fft,
                    n_per_seg=self.params.get('n_per_seg', n_fft),
                    n_overlap=self.params.get('n_overlap', 0),
                    type=self.ui.typeBox.currentText())

    if self.ui.psdMethod.currentText() == 'multitaper':
        kwds = dict(epochs=self.data,
                    fmin=self.params['fmin'],
                    fmax=self.params['fmax'],
                    tmin=self.params['tmin'],
                    tmax=self.params['tmax'],
                    method='multitaper',
                    bandwidth=self.params.get('bandwidth', 4),
                    type=self.ui.typeBox.currentText())

    calc = CalcDialog(self, "Calculating PSD",
                      "Calculating Power Spectrum Density.")
    pool = mp.Pool(1)
    psd = EpochsPSD()
    res = pool.apply_async(func=psd.init,
                           kwds=kwds,
                           callback=lambda x: calc.accept())

    if not calc.exec_():
        pool.terminate()

    self.psd = res.get(timeout=1)


# ---------------------------------------------------------------------
def _init_raw_psd(self):
    """Initialize the instance of RawPSD."""
    from .raw_psd import RawPSD

    if self.ui.psdMethod.currentText() == 'welch':
        kwds = dict(raw=self.data,
                    fmin=self.params['fmin'],
                    fmax=self.params['fmax'],
                    tmin=self.params['tmin'],
                    tmax=self.params['tmax'],
                    method='welch',
                    n_fft=self.params.get('n_fft', 2048),
                    n_per_seg=self.params.get('n_per_seg', 2048),
                    n_overlap=self.params.get('n_overlap', 0),
                    type=self.ui.typeBox.currentText())

    if self.ui.psdMethod.currentText() == 'multitaper':
        kwds = dict(raw=self.data,
                    fmin=self.params['fmin'],
                    fmax=self.params['fmax'],
                    tmin=self.params['tmin'],
                    tmax=self.params['tmax'],
                    method='multitaper',
                    bandwidth=self.params.get('bandwidth', 4),
                    type=self.ui.typeBox.currentText())

    calc = CalcDialog(self, "Calculating PSD",
                      "Calculating Power Spectrum Density.")
    pool = mp.Pool(1)
    psd = RawPSD()
    res = pool.apply_async(func=psd.init,
                           kwds=kwds,
                           callback=lambda x: calc.accept())

    if not calc.exec_():
        pool.terminate()

    self.psd = res.get(timeout=1)


# ---------------------------------------------------------------------
def _open_epochs_psd_visualizer(self):
    """Open PSD visualizer for epochs data
    """
    from ..app.epochs_psd import EpochsPSDWindow

    _init_epochs_psd(self)
    psdVisualizer = EpochsPSDWindow(self.psd, parent=None)
    psdVisualizer.setWindowModality(Qt.WindowModal)
    psdVisualizer.setWindowTitle(self.windowTitle())
    psdVisualizer.exec()


# ---------------------------------------------------------------------
def _open_raw_psd_visualizer(self):
    """Open PSD Visualizer for raw type data
    """
    from ..app.raw_psd import RawPSDWindow

    _init_raw_psd(self)

    psdVisualizer = RawPSDWindow(self.psd, parent=None)
    psdVisualizer.setWindowModality(Qt.WindowModal)
    psdVisualizer.setWindowTitle(self.windowTitle())
    psdVisualizer.exec()


# ---------------------------------------------------------------------
def _init_avg_tfr(self):
    """Init tfr from parameters
    """
    from .avg_epochs_tfr import AvgEpochsTFR
    from .util import float_, int_
    from numpy import arange

    fmin = self.params['fmin']
    fmax = self.params['fmax']
    step = self.params.get('freq_step', 1)
    freqs = arange(fmin, fmax, step)
    if self.params['time_window'] is not None:
        n_cycles = self.params['time_window'] * freqs
    else:
        n_cycles = self.params['n_cycles']
    n_fft = self.params.get('n_fft', None)

    calc = CalcDialog(self, "Calculating Time-Frequency",
                      "Calculating Time-Frequency.")
    pool = mp.Pool(1)

    avgTFR = AvgEpochsTFR()
    args = (self.data, freqs, n_cycles)
    kwds = dict(method=self.ui.tfrMethodBox.currentText(),
                time_bandwidth=self.params.get('time_bandwidth', 4),
                width=self.params.get('width', 1),
                n_fft=n_fft, type=self.ui.typeBox.currentText())

    res = pool.apply_async(func=avgTFR.init,
                           args=args,
                           kwds=kwds,
                           callback=lambda x: calc.accept())

    if not calc.exec_():
        pool.terminate()

    self.avgTFR = res.get(timeout=1)


# ---------------------------------------------------------------------
def _open_tfr_visualizer(self):
    """Open TFR Visualizer
    """
    from ..app.avg_epochs_tfr import AvgTFRWindow
    try:
        _init_avg_tfr(self)
        tfrVisualizer = AvgTFRWindow(self.avgTFR, parent=None)
        tfrVisualizer.setWindowModality(Qt.WindowModal)
        tfrVisualizer.setWindowTitle(self.windowTitle())
        tfrVisualizer.exec()

    except Exception as e:
        print(e)
