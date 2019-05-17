import os
import time

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

import datetime
import mne

from .utils import _read, init_avg_tfr, init_epochs_psd, init_raw_psd
from ...tfr.app.avg_epochs_tfr import AvgTFRWindow
from ...tfr.app.raw_psd import RawPSDWindow
from ...tfr.app.epochs_psd import EpochsPSDWindow


def _batch_process(self):
    """Start batch process."""

    # Create log
    logpath = os.path.join(self.savePath, 'log.txt')
    exists = os.path.isfile(logpath)
    if exists:
        f = open(logpath, 'a')
        f.write('\n\n\n\n')
    else:
        f = open(logpath, 'w')

    now = datetime.datetime.now()
    f.write('Batch Processing - {}\n'.format(now.strftime("%Y-%m-%d %H:%M")))
    f.write('-------------------------------------------------------------\n')
    f.write('Number of files : {}\n'.format(len(self.fnames)))
    if self.ui.tfrBox.isChecked():
        f.write('TFR Parameters : {}\n'.format(self.tfr_params))
    if self.ui.psdBox.isChecked():
        f.write('PSD Parameters : {}\n'.format(self.psd_params))

    if len(self.fnames) > 0:
        progress = QProgressDialog("Running Batch Processing...",
                                   "Abort", 0, len(self.fnames),
                                   parent=self)
        progress.setWindowModality(Qt.WindowModal)

    for index, fname in enumerate(self.fnames):
        f.write('\nFile {}: {}\n'.format(index + 1, fname))
        progress.setValue(index)
        data, type = _read(fname)
        ending = ''
        if progress.wasCanceled():
            break

        # Filtering
        if self.ui.filterBox.isChecked():
            try:
                low = float(self.ui.low.text())
                high = float(self.ui.high.text())
                data.filter(low, high)
                ending = ending + '_filtered_{}-{}'.format(low, high)
                f.write('Filtered between {}-{} Hz\n'.format(low, high))
            except Exception as e:
                f.write('Error caught while filtering : ' + str(e) + '\n')
                print("Error while filtering...")
                print(e)

        # Resampling
        if self.ui.samplingBox.isChecked():
            try:
                sfreq = float(self.ui.sfreq.text())
                data.resample(sfreq)
                ending = ending + '_resampled_{}'.format(sfreq)
                f.write('Resampled to {} Hz\n'.format(sfreq))
            except Exception as e:
                f.write('Error caught while resampling : ' + str(e) + '\n')
                print("Error while resampling...")
                print(e)

        if (self.ui.filterBox.isChecked() or
                self.ui.samplingBox.isChecked()):
            name, format = os.path.splitext(os.path.basename(fname))
            save_name = os.path.join(self.savePath,
                                     name + ending + format)
            data.save(save_name, overwrite=True)
            f.write('file saved at {}\n'.format(save_name))

        # Computing tfr
        if self.ui.tfrBox.isChecked():
            try:
                name, format = os.path.splitext(os.path.basename(fname))
                save_name = os.path.join(self.savePath,
                                         name + '_tfr.h5')
                avgTfr = init_avg_tfr(data, self.tfr_params)
                avgTfr.tfr.save(save_name)
                f.write('Tfr saved at: {}\n'
                        .format(save_name))

                if index == 0:
                    mean_tfr = tfr
                else:
                    mean_tfr.tfr.data = tfr.tfr.data + mean_tfr.tfr.data
            except Exception as e:
                f.write('Error caught while computing time-frequency : '
                        + str(e) + '\n')
                print(name, (" time-frequency computing "
                             + "encountered a problem..."))
                print(e)

        # Computing PSD
        if self.ui.psdBox.isChecked():
            try:
                name, format = os.path.splitext(os.path.basename(fname))
                save_name = os.path.join(self.savePath,
                                         name + '_psd.h5')
                if type == 'raw' or type == 'evoked':
                    psd = init_raw_psd(data, self.psd_params)
                    psd.save_hdf5(save_name, overwrite=True)
                elif type == 'epochs':
                    psd = init_epochs_psd(data, self.psd_params)
                    psd.save_hdf5(save_name, overwrite=True)
                f.write('Psd saved at: {}\n'
                        .format(save_name))

                if index == 0:
                    mean_psd = psd
                else:
                    mean_psd.data = psd.data + mean_psd.data
            except Exception as e:
                f.write('Error caught while computing PSD : '
                        + str(e) + '\n')
                print(name, (" PSD computing "
                             + "encountered a problem..."))
                print(e)

    progress.setValue(len(self.fnames))

    if self.ui.psdBox.isChecked():
        try:
            mean_psd.data = mean_psd.data / len(self.fnames)
            mean_psd_name = os.path.join(self.savePath, 'mean_psd.h5')
            mean_psd.save_hdf5(mean_psd_name, overwrite=True)
            f.write('\nMean of PSD saved at: {}\n'.format(mean_psd_name))
            if type == 'raw' or typee == 'evoked':
                dialog = RawPSDWindow(mean_psd, parent=None)
                dialog.setWindowModality(Qt.WindowModal)
                dialog.setWindowTitle('Average PSD over batch')
                dialog.exec()
            else:
                dialog = EpochsPSDWindow(mean_psd, parent=None)
                dialog.setWindowModality(Qt.WindowModal)
                dialog.setWindowTitle('Average PSD over batch')
                dialog.exec()
        except Exception as e:
            print('Couldnt compute average')
            print(e)

    if self.ui.tfrBox.isChecked():
        try:
            mean_tfr.tfr.data = mean_tfr.tfr.data / len(self.fnames)
            mean_tfr_name = os.path.join(self.savePath, 'mean_tfr.h5')
            mean_tfr.save(mean_tfr_name, overwrite=True)
            f.write('\nMean of TFR saved at: {}\n'.format(mean_psd_name))
            dialog = AvgTFRWindow(mean_tfr, parent=None)
            dialog.setWindowModality(Qt.WindowModal)
            dialog.setWindowTitle('Average TFR over batch')
            dialog.exec()
        except Exception as e:
            print('Couldnt compute average')
            print(e)

    f.close()
