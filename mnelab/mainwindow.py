import multiprocessing as mp
from sys import version_info
from collections import Counter

import matplotlib.pyplot as plt
import mne

from PyQt5.QtCore import (pyqtSlot, QStringListModel, QModelIndex, QSettings,
                          QEvent, Qt, QObject)
from PyQt5.QtGui import QKeySequence, QDropEvent
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QSplitter,
                             QMessageBox, QListView, QAction, QLabel, QFrame,
                             QStatusBar, QToolBar)

from .tfr.backend.avg_epochs_tfr import AvgEpochsTFR
from .tfr.app.avg_epochs_tfr import AvgTFRWindow
from .tfr.backend.epochs_psd import EpochsPSD
from .tfr.app.epochs_psd import EpochsPSDWindow
from .tfr.backend.raw_psd import RawPSD
from .tfr.app.raw_psd import RawPSDWindow

from .utils.error import show_error
from .dialogs.calcdialog import CalcDialog
from .dialogs.filterdialog import FilterDialog
from .dialogs.findeventsdialog import FindEventsDialog
from .dialogs.pickchannelsdialog import PickChannelsDialog
from .dialogs.referencedialog import ReferenceDialog
from .dialogs.montagedialog import MontageDialog
from .dialogs.channelpropertiesdialog import ChannelPropertiesDialog
from .dialogs.runicadialog import RunICADialog

from .dialogs.eventsdialog import EventsDialog
from .widgets.infowidget import InfoWidget
from .dialogs.timefreqdialog import TimeFreqDialog
from .dialogs.psddialog import PSDDialog
from .dialogs.epochingdialog import EpochingDialog
from .dialogs.epochingdialog import EpochingDialog
from .dialogs.navepochsdialog import NavEpochsDialog
from .dialogs.resampledialog import ResampleDialog
from .dialogs.evokedstatesdialog import EvokedStatesDialog
from .dialogs.evokedtopodialog import EvokedTopoDialog
from .dialogs.batchdialog import BatchDialog

from .utils.ica_utils import plot_correlation_matrix as plot_cormat
from .utils.ica_utils import (plot_ica_components_with_timeseries,
                              plot_overlay)
from .model import (SUPPORTED_FORMATS, SUPPORTED_EXPORT_FORMATS,
                    LabelsNotFoundError, InvalidAnnotationsError)

__version__ = "0.1.0"

MAX_RECENT = 6  # maximum number of recent files


def read_settings():
    """Read application settings.

    Returns
    -------
    settings : dict
        The restored settings values are returned in a dictionary for further
        processing.
    """
    settings = QSettings()

    recent = settings.value("recent")
    if not recent:
        recent = []  # default is empty list

    statusbar = settings.value("statusbar")
    if statusbar is None:  # default is True
        statusbar = True

    geometry = settings.value("geometry")
    state = settings.value("state")

    return {"recent": recent, "statusbar": statusbar, "geometry": geometry,
            "state": state}


def write_settings(**kwargs):
    """Write application settings."""
    settings = QSettings()
    for key, value in kwargs.items():
        settings.setValue(key, value)


class MainWindow(QMainWindow):
    """MNELAB main window."""
    def __init__(self, model):
        """Initialize MNELAB main window.
        Parameters
        ----------
        model : mnelab.model.Model instance
            The main window needs to connect to a model containing all data
            sets. This decouples the GUI from the data (model/view).
        """
        super().__init__()

        self.model = model  # data model
        self.setWindowTitle("MNELAB")

        # restore settings
        settings = read_settings()
        self.recent = settings["recent"]  # list of recent files
        if settings["geometry"]:
            self.restoreGeometry(settings["geometry"])
        else:
            self.setGeometry(300, 300, 1000, 750)  # default window size
            self.move(QApplication.desktop().screen().rect().center() -
                      self.rect().center())  # center window
        if settings["state"]:
            self.restoreState(settings["state"])

        self.actions = {}  # contains all actions

        # initialize menus
        file_menu = self.menuBar().addMenu("&File")
        self.actions["open_file"] = file_menu.addAction(
            "&Open...",
            lambda: self.open_file(model.load, "Open raw", SUPPORTED_FORMATS),
            QKeySequence.Open)
        self.recent_menu = file_menu.addMenu("Open recent")
        self.recent_menu.aboutToShow.connect(self._update_recent_menu)
        self.recent_menu.triggered.connect(self._load_recent)
        if not self.recent:
            self.recent_menu.setEnabled(False)
        self.actions["close_file"] = file_menu.addAction(
            "&Close",
            self.model.remove_data,
            QKeySequence.Close)
        self.actions["close_all"] = file_menu.addAction(
            "Close all",
            self.close_all)
        file_menu.addSeparator()
        self.actions["import_bads"] = file_menu.addAction(
            "Import bad channels...",
            lambda: self.import_file(model.import_bads, "Import bad channels",
                                     "*.csv *.txt"))
        self.actions["import_events"] = file_menu.addAction(
            "Import events...",
            lambda: self.import_file(model.import_events, "Import events",
                                     "*.csv *.mrk"))
        self.actions["import_annotations"] = file_menu.addAction(
            "Import annotations...",
            lambda: self.import_file(model.import_annotations,
                                     "Import annotations", "*.csv *.mrk"))
        self.actions["import_ica"] = file_menu.addAction(
            "Import &ICA...",
            lambda: self.open_file(model.import_ica, "Import ICA",
                                   "*.fif *.fif.gz"))
        file_menu.addSeparator()
        self.actions["export_data"] = file_menu.addAction(
            "Export data...",
            lambda: self.export_file(model.export_data, "Export",
                                     SUPPORTED_EXPORT_FORMATS))
        self.actions["export_bads"] = file_menu.addAction(
            "Export &bad channels...",
            lambda: self.export_file(model.export_bads, "Export bad channels",
                                     "*.csv"))
        self.actions["export_events"] = file_menu.addAction(
            "Export &events...",
            lambda: self.export_file(model.export_events, "Export events",
                                     "*.csv"))
        self.actions["export_annotations"] = file_menu.addAction(
            "Export &annotations...",
            lambda: self.export_file(model.export_annotations,
                                     "Export annotations", "*.csv"))
        self.actions["export_ica"] = file_menu.addAction(
            "Export ICA...",
            lambda: self.export_file(model.export_ica,
                                     "Export ICA", "*.fif *.fif.gz"))
        self.actions["export_psd"] = file_menu.addAction(
            "Export Power Spectrum Density...",
            lambda: self.export_file(model.export_psd,
                                     "Export Power Spectrum Density", "*.hdf"))
        self.actions["export_tfr"] = file_menu.addAction(
            "Export Time-Frequency...",
            lambda: self.export_file(model.export_tfr,
                                     "Export Time-Frequency", "*.hdf"))
        file_menu.addSeparator()
        self.actions["quit"] = file_menu.addAction(
            "&Quit", self.close, QKeySequence.Quit)

        edit_menu = self.menuBar().addMenu("&Edit")
        self.actions["pick_chans"] = edit_menu.addAction(
            "Pick &channels...",
            self.pick_channels)
        self.actions["chan_props"] = edit_menu.addAction(
            "Edit channel &properties...",
            self.channel_properties)
        self.actions["set_montage"] = edit_menu.addAction(
            "Edit &montage...", self.set_montage)
        self.actions["events"] = edit_menu.addAction(
            "Edit &events...", self.edit_events)

        plot_menu = self.menuBar().addMenu("&Plot")
        self.actions["plot_raw"] = plot_menu.addAction(
            "Plot &Data...", self.plot_raw)
        self.actions["plot_image"] = plot_menu.addAction(
            "Plot data as &Image...", self.plot_image)
        self.actions["plot_states"] = plot_menu.addAction(
            "Plot &States...", self.plot_states)
        self.actions["plot_topomaps"] = plot_menu.addAction(
            "Plot &Topomaps...", self.plot_topomaps)
        self.actions["plot_montage"] = plot_menu.addAction(
            "Plot Current &montage", self.plot_montage)

        tools_menu = self.menuBar().addMenu("&Preprocessing")
        self.actions["filter"] = tools_menu.addAction(
            "&Filter data...", self.filter_data)
        self.actions["resample"] = tools_menu.addAction(
            "&Downsample...", self.resample)

        self.actions["interpolate_bads"] = tools_menu.addAction(
            "Interpolate bad channels...", self.interpolate_bads)
        self.actions["set_ref"] = tools_menu.addAction(
            "&Set reference...", self.set_reference)

        ica_menu = self.menuBar().addMenu("&ICA")
        self.actions["run_ica"] = ica_menu.addAction(
            "Run &ICA...", self.run_ica)
        ica_menu.addSeparator()
        self.actions["plot_ica_components"] = ica_menu.addAction(
            "Plot ICA &components...",
            self.plot_ica_components_with_timeseries)
        self.actions["plot_ica_sources"] = ica_menu.addAction(
            "Plot &ICA sources...", self.plot_ica_sources)
        self.actions["plot_correlation_matrix"] = ica_menu.addAction(
            "Plot correlation &matrix...", self.plot_correlation_matrix)
        self.actions["plot_overlay"] = ica_menu.addAction(
            "Plot overlay...", self.plot_ica_overlay)
        ica_menu.addSeparator()
        self.actions["apply_ica"] = ica_menu.addAction(
            "Apply &ICA...", self.apply_ica)

        freq_menu = self.menuBar().addMenu("&Frequencies")
        self.actions["plot_psd"] = freq_menu.addAction(
            "Compute &Power spectral density...", self.plot_psd)
        self.actions["plot_tfr"] = freq_menu.addAction(
            "Compute &Time-Frequency...", self.plot_tfr)
        freq_menu.addSeparator()
        self.actions["open_tfr"] = freq_menu.addAction(
            "&Open Time-Frequency file...", self.open_tfr)
        self.actions["open_psd"] = freq_menu.addAction(
            "&Open Power Spectrum Density file...",
            self.open_psd)

        events_menu = self.menuBar().addMenu("&Events")
        self.actions["plot_events"] = events_menu.addAction(
            "&Plot events...", self.plot_events)
        events_menu.addSeparator()
        self.actions["find_events"] = events_menu.addAction(
            "Find &events...", self.find_events)
        self.actions["add_events"] = events_menu.addAction(
            "Setup events as annotation...", self.add_events)

        epochs_menu = self.menuBar().addMenu("Epochs")
        self.actions["epoch_data"] = epochs_menu.addAction(
            "Cut data into epochs...", self.epoch_data)
        self.actions["evoke_data"] = epochs_menu.addAction(
            "Average epochs...", self.evoke_data)

        batch_menu = self.menuBar().addMenu("&Batch")
        self.actions["open_batch"] = batch_menu.addAction(
            "Open &Batch processing window", self.open_batch)

        view_menu = self.menuBar().addMenu("&View")
        self.actions["statusbar"] = view_menu.addAction(
            "Statusbar", self._toggle_statusbar)
        self.actions["statusbar"].setCheckable(True)

        help_menu = self.menuBar().addMenu("&Help")
        self.actions["about"] = help_menu.addAction("&About", self.show_about)
        self.actions["about_qt"] = help_menu.addAction(
            "About &Qt", self.show_about_qt)

        # actions that are always enabled
        self.always_enabled = ["open_file", "about", "about_qt", "quit",
                               "statusbar", "open_batch", "open_tfr",
                               "open_psd"]

        # set up data model for sidebar (list of open files)
        self.names = QStringListModel()
        self.names.dataChanged.connect(self._update_names)
        splitter = QSplitter()
        self.sidebar = QListView()
        self.sidebar.setFrameStyle(QFrame.NoFrame)
        self.sidebar.setFocusPolicy(Qt.NoFocus)
        self.sidebar.setModel(self.names)
        self.sidebar.clicked.connect(self._update_data)
        splitter.addWidget(self.sidebar)
        self.infowidget = InfoWidget()
        splitter.addWidget(self.infowidget)
        width = splitter.size().width()
        splitter.setSizes((width * 0.3, width * 0.7))
        self.setCentralWidget(splitter)

        self.status_label = QLabel()
        self.statusBar().addPermanentWidget(self.status_label)
        if settings["statusbar"]:
            self.statusBar().show()
            self.actions["statusbar"].setChecked(True)
        else:
            self.statusBar().hide()
            self.actions["statusbar"].setChecked(False)

        self.setAcceptDrops(True)
        self.data_changed()

    def data_changed(self):
        # update sidebar
        self.names.setStringList(self.model.names)
        self.sidebar.setCurrentIndex(self.names.index(self.model.index))

        # update info widget
        if self.model.data:
            self.infowidget.set_values(self.model.get_info())
        else:
            self.infowidget.clear()

        # update status bar
        if self.model.data:
            mb = self.model.nbytes / 1024 ** 2
            self.status_label.setText("Total Memory: {:.2f} MB".format(mb))
        else:
            self.status_label.clear()

        # toggle actions
        if len(self.model) == 0:  # disable if no data sets are currently open
            enabled = False
        else:
            enabled = True

        for name, action in self.actions.items():  # toggle
            if name not in self.always_enabled:
                action.setEnabled(enabled)

        if self.model.data:  # toggle if specific conditions are met
            if self.model.current["raw"]:
                raw = True
                evoked = False
                bads = bool(self.model.current["raw"].info["bads"])
                annot = self.model.current["raw"].annotations is not None
                events = self.model.current["events"] is not None
                self.actions["import_annotations"].setEnabled(True)
                self.actions["import_events"].setEnabled(True)
                self.actions["evoke_data"].setEnabled(False)
                self.actions["plot_image"].setEnabled(False)
                self.actions["plot_tfr"].setEnabled(False)
            else:
                raw = False
                annot = False
                events = False
                self.actions["find_events"].setEnabled(False)
                self.actions["import_annotations"].setEnabled(False)
                self.actions["import_events"].setEnabled(False)
                self.actions["plot_image"].setEnabled(True)
                if self.model.current["epochs"]:
                    evoked = False
                    bads = bool(self.model.current["epochs"].info["bads"])
                    self.actions["evoke_data"].setEnabled(True)
                else:
                    evoked = True
                    bads = bool(self.model.current["evoked"].info["bads"])
                    self.actions["evoke_data"].setEnabled(False)
            self.actions["export_bads"].setEnabled(enabled and bads)
            self.actions["export_events"].setEnabled(enabled and events)
            self.actions["export_annotations"].setEnabled(enabled and annot)
            montage = bool(self.model.current["montage"])
            self.actions["run_ica"].setEnabled(enabled and montage
                                               and not evoked)
            self.actions["plot_montage"].setEnabled(enabled and montage)
            self.actions["interpolate_bads"].setEnabled(enabled and montage)
            ica = bool(self.model.current["ica"])
            self.actions["export_ica"].setEnabled(enabled and ica)
            self.actions["plot_events"].setEnabled(raw and events)
            self.actions["plot_ica_components"].setEnabled(enabled and ica
                                                           and montage)
            self.actions["plot_ica_sources"].setEnabled(enabled and ica
                                                        and montage)
            self.actions["plot_correlation_matrix"].setEnabled(
                enabled and ica and montage)
            self.actions["plot_overlay"].setEnabled(
                enabled and ica and montage)
            self.actions["run_ica"].setEnabled(montage and not evoked)
            self.actions["apply_ica"].setEnabled(enabled and ica
                                                 and montage)
            self.actions["events"].setEnabled(enabled and events)
            self.actions["epoch_data"].setEnabled(enabled and events)
            self.actions["add_events"].setEnabled(enabled and events)
            self.actions["plot_states"].setEnabled(montage and evoked)
            self.actions["plot_topomaps"].setEnabled(montage and evoked)
            self.actions["export_tfr"].setEnabled(
                self.model.current["tfr"] is not None)
            self.actions["export_psd"].setEnabled(
                self.model.current["psd"] is not None)

        # add to recent files
        if len(self.model) > 0:
            self._add_recent(self.model.current["fname"])

    def open_file(self, f, text, ffilter):
        """Open file."""
        fname = QFileDialog.getOpenFileName(self, text, filter=ffilter)[0]
        if fname:
            f(fname)

    def export_file(self, f, text, ffilter):
        """Export to file."""
        # BUG on windows fname = QFileDialog.getSaveFileName(self,
        # text, filter=ffilter)[0]
        fname = QFileDialog.getSaveFileName(self, text, filter=ffilter)[0]
        if fname:
            f(fname)

    def import_file(self, f, text, ffilter):
        """Import file."""
        fname = QFileDialog.getOpenFileName(self, text, filter=ffilter)[0]
        if fname:
            try:
                f(fname)
            except LabelsNotFoundError as e:
                QMessageBox.critical(self, "Channel labels not found", str(e))
            except InvalidAnnotationsError as e:
                QMessageBox.critical(self, "Invalid annotations", str(e))

    def close_all(self):
        """Close all currently open data sets."""
        msg = QMessageBox.question(self, "Close all data sets",
                                   "Close all data sets?")
        if msg == QMessageBox.Yes:
            while len(self.model) > 0:
                self.model.remove_data()

    def pick_channels(self):
        """Pick channels in current data set."""
        if self.model.current["raw"]:
            channels = self.model.current["raw"].info["ch_names"]
        elif self.model.current["epochs"]:
            channels = self.model.current["epochs"].info["ch_names"]
        else:
            channels = self.model.current["evoked"].info["ch_names"]
        dialog = PickChannelsDialog(self, channels, selected=channels)
        if dialog.exec_():
            picks = [item.data(0) for item in dialog.channels.selectedItems()]
            drops = set(channels) - set(picks)
            if drops:
                self.auto_duplicate()
                self.model.drop_channels(drops)
                self.model.history.append(f"data.drop({drops})")

    def channel_properties(self):
        """Show channel properties dialog."""
        if self.model.current["raw"]:
            info = self.model.current["raw"].info
        elif self.model.current["epochs"]:
            info = self.model.current["epochs"].info
        else:
            info = self.model.current["evoked"].info
        dialog = ChannelPropertiesDialog(self, info)
        if dialog.exec_():
            dialog.model.sort(0)
            bads = []
            renamed = {}
            types = {}
            for i in range(dialog.model.rowCount()):
                new_label = dialog.model.item(i, 1).data(Qt.DisplayRole)
                old_label = info["ch_names"][i]
                if new_label != old_label:
                    renamed[old_label] = new_label
                new_type = dialog.model.item(i, 2).data(Qt.DisplayRole).lower()
                types[new_label] = new_type
                if dialog.model.item(i, 3).checkState() == Qt.Checked:
                    bads.append(info["ch_names"][i])
            self.model.set_channel_properties(bads, renamed, types)

    def set_montage(self):
        """Set montage."""
        montages = mne.channels.get_builtin_montages()
        # TODO: currently it is not possible to remove an existing montage
        dialog = MontageDialog(self, montages,
                               selected=self.model.current["montage"])
        if dialog.exec_():
            if dialog.montage_path == '':
                name = dialog.montages.selectedItems()[0].data(0)
                montage = mne.channels.read_montage(name)
                self.model.history.append("montage = mne.channels."
                                          + ("read_montage({})").format(name))
            else:
                from .utils.montage import xyz_to_montage
                montage = xyz_to_montage(dialog.montage_path)
                self.model.history.append("montage = xyz_to_montage({})"
                                          .format(dialog.montage_path))
            if self.model.current["raw"]:
                ch_names = self.model.current["raw"].info["ch_names"]
            elif self.model.current["epochs"]:
                ch_names = self.model.current["epochs"].info["ch_names"]
            elif self.model.current["evoked"]:
                ch_names = self.model.current["evoked"].info["ch_names"]
            # check if at least one channel name matches a name in the montage
            if set(ch_names) & set(montage.ch_names):
                self.model.set_montage(montage)
            else:
                QMessageBox.critical(self, "No matching channel names",
                                     "Channel names defined in the montage do "
                                     "not match any channel name in the data.")

    def edit_events(self):
        pos = self.model.current["events"][:, 0].tolist()
        desc = self.model.current["events"][:, 2].tolist()
        dialog = EventsDialog(self, pos, desc)
        if dialog.exec_():
            pass

    def plot_raw(self):
        """Plot data."""
        events = self.model.current["events"]
        if self.model.current["raw"]:
            nchan = self.model.current["raw"].info["nchan"]
            fig = self.model.current["raw"].plot(
                events=events, title=self.model.current["name"],
                scalings="auto", show=False)
            self.model.history.append("raw.plot(n_channels={})".format(nchan))
        elif self.model.current["epochs"]:
            nchan = self.model.current["epochs"].info["nchan"]
            fig = self.model.current["epochs"].plot(
                title=self.model.current["name"],
                scalings="auto", show=False)
            self.model.history.append(
                "epochs.plot(n_channels={})".format(nchan))
        elif self.model.current["evoked"]:
            nchan = self.model.current["evoked"].info["nchan"]
            fig = self.model.current["evoked"].plot(show=False, gfp=True,
                                                    spatial_colors=True,
                                                    selectable=False)
            self.model.history.append(
                "epochs.plot(n_channels={})".format(nchan))
        win = fig.canvas.manager.window
        win.setWindowTitle(self.model.current["name"])
        win.findChild(QStatusBar).hide()
        win.installEventFilter(self)  # detect if the figure is closed

        # prevent closing the window with the escape key
        try:
            key_events = fig.canvas.callbacks.callbacks["key_press_event"][8]
        except KeyError:
            pass
        else:  # this requires MNE >=0.15
            # This line causes bug... I don't know why exactly
            # AttributeError: '_StrongRef' object has no attribute 'func'
            #
            # key_events.func.keywords["params"]["close_key"] = None
            pass

        fig.show()

    def plot_image(self):
        if self.model.current["epochs"]:
            try:
                epochs = self.model.current["epochs"]
                dialog = NavEpochsDialog(None, epochs)
                dialog.setWindowModality(Qt.WindowModal)
                dialog.setWindowTitle(self.model.current["name"])
                dialog.exec()
            except Exception as e:
                print(e)
        elif self.model.current["evoked"]:
            fig = self.model.current["evoked"].plot_image(show=False)
            self.model.history.append("evoked.plot_image()")
            win = fig.canvas.manager.window
            win.findChild(QStatusBar).hide()
            win.setWindowTitle(self.model.current["name"])
            win.installEventFilter(self)  # detect if the figure is closed
            fig.show()

    def plot_states(self):
        if self.model.current["evoked"]:
            dialog = EvokedStatesDialog(None, self.model.current["evoked"])
            dialog.setWindowModality(Qt.NonModal)
            dialog.setWindowTitle(self.model.current["name"])
            dialog.show()

    def plot_topomaps(self):
        if self.model.current["evoked"]:
            dialog = EvokedTopoDialog(None, self.model.current["evoked"])
            dialog.setWindowModality(Qt.NonModal)
            dialog.setWindowTitle(self.model.current["name"])
            dialog.show()

    def plot_events(self):
        events = self.model.current["events"]
        fig = mne.viz.plot_events(events, show=False)
        win = fig.canvas.manager.window
        win.setWindowModality(Qt.WindowModal)
        win.setWindowTitle(self.model.current["name"])
        win.findChild(QStatusBar).hide()
        win.findChild(QToolBar).hide()
        fig.show()

    def plot_psd(self):
        """Plot power spectral density (PSD)."""
        if self.model.current["raw"]:
            raw = self.model.current["raw"]
            dialog = PSDDialog(None, raw)
            dialog.setWindowModality(Qt.WindowModal)
            dialog.setWindowTitle('PSD of ' + self.model.current["name"])
            dialog.exec_()
        elif self.model.current["epochs"]:
            epochs = self.model.current["epochs"]
            dialog = PSDDialog(None, epochs)
            dialog.setWindowModality(Qt.WindowModal)
            dialog.setWindowTitle('PSD of ' + self.model.current["name"])
            dialog.exec_()
        elif self.model.current["evoked"]:
            evoked = self.model.current["evoked"]
            dialog = PSDDialog(None, evoked)
            dialog.setWindowModality(Qt.WindowModal)
            dialog.setWindowTitle('PSD of ' + self.model.current["name"])
            dialog.exec_()

        try:
            psd = dialog.psd
        except Exception as e:
            psd = None
        if psd is not None:
            self.model.current["psd"] = psd
            self.data_changed()

    def open_psd(self):
        fname = QFileDialog.getOpenFileName(self, "Open TFR",
                                            filter="*.h5 *.hdf")[0]
        try:
            psd = EpochsPSD().init_from_hdf(fname)
            win = EpochsPSDWindow(psd, parent=None)
            win.setWindowTitle(fname)
            win.exec()
        except Exception as e:
            print(e)
            try:
                psd = RawPSD().init_from_hdf(fname)
                win = RawPSDWindow(psd, parent=None)
                win.setWindowModality(Qt.WindowModal)
                win.setWindowTitle(fname)
                win.exec()
            except Exception:
                pass

    def plot_tfr(self):
        """Plot Time-Frequency."""
        if self.model.current["epochs"]:
            data = self.model.current["epochs"]
        elif self.model.current["evoked"]:
            data = self.model.current["evoked"]
        dialog = TimeFreqDialog(None, data)
        dialog.setWindowModality(Qt.WindowModal)
        dialog.setWindowTitle('TFR of ' + self.model.current["name"])
        dialog.exec_()

        try:
            tfr = dialog.avgTFR
            self.data_changed()
        except Exception as e:
            tfr = None
        if tfr is not None:
            self.model.current["tfr"] = tfr
            self.data_changed()

    def open_tfr(self):
        try:
            fname = QFileDialog.getOpenFileName(self, "Open TFR",
                                                filter="*.h5 *.hdf")[0]
            avgTFR = AvgEpochsTFR().init_from_hdf(fname)
            win = AvgTFRWindow(avgTFR, parent=None)
            win.setWindowModality(Qt.WindowModal)
            win.setWindowTitle(fname)
            win.exec()
        except Exception as e:
            print(e)

    def plot_montage(self):
        """Plot current montage."""
        if self.model.current["raw"]:
            data = self.model.current["raw"]
        elif self.model.current["epochs"]:
            data = self.model.current["epochs"]
        elif self.model.current["evoked"]:
            data = self.model.current["evoked"]
        chans = Counter([mne.io.pick.channel_type(data.info, i)
                         for i in range(data.info["nchan"])])
        fig = plt.figure()
        types = []
        for type in chans.keys():
            if type in ['eeg', 'mag', 'grad']:
                types.append(type)

        for i, type in enumerate(types):
            ax = fig.add_subplot(1, len(types), i + 1)
            ax.set_title(type + '({} channels)'.format(chans[type]))
            data.plot_sensors(show_names=True, show=False,
                              ch_type=type, axes=ax, title='')
        win = fig.canvas.manager.window
        win.resize(len(types) * 600, 600)
        win.setWindowTitle(self.model.current["name"])
        win.findChild(QStatusBar).hide()
        win.findChild(QToolBar).hide()
        fig.show()

    def plot_ica_components_with_timeseries(self):
        if self.model.current["raw"]:
            try:
                fig = plot_ica_components_with_timeseries(
                                             self.model.current["ica"],
                                             inst=self.model.current["raw"])
            except Exception as e:
                QMessageBox.critical(self, "Unexpected error ", str(e))

        elif self.model.current["epochs"]:
            try:
                fig = plot_ica_components_with_timeseries(
                            self.model.current["ica"],
                            inst=self.model.current["epochs"])
            except Exception as e:
                try:
                    fig = self.model.current["ica"].plot_ica_components(
                                            inst=self.model.current["epochs"])
                except Exception as e:
                    QMessageBox.critical(self, "Unexpected error ", str(e))

    def plot_ica_sources(self):
        if self.model.current["raw"]:
            fig = (self.model.current["ica"]
                   .plot_sources(inst=self.model.current["raw"]))
        elif self.model.current["epochs"]:
            fig = (self.model.current["ica"]
                   .plot_sources(inst=self.model.current["epochs"]))
        win = fig.canvas.manager.window
        win.setWindowTitle("ICA Sources")
        win.findChild(QStatusBar).hide()
        win.installEventFilter(self)  # detect if the figure is closed

    def plot_correlation_matrix(self):
        if self.model.current["raw"]:
            try:
                plot_cormat(self.model.current["raw"],
                            self.model.current["ica"])
            except ValueError as e:
                QMessageBox.critical(
                 self, "Can't compute correlation with template ", str(e))
            except Exception as e:
                QMessageBox.critical(
                 self, "Unexpected error ", str(e))
        elif self.model.current["epochs"]:
            try:
                plot_cormat(self.model.current["epochs"],
                            self.model.current["ica"])
            except ValueError as e:
                QMessageBox.critical(
                    self, "Can't compute correlation with template ", str(e))
            except Exception as e:
                QMessageBox.critical(
                    self, "Unexpected error ", str(e))

    def plot_ica_overlay(self):
        if self.model.current["raw"]:
            plot_overlay(self.model.current["ica"],
                         self.model.current["raw"])
        elif self.model.current["epochs"]:
            plot_overlay(self.model.current["ica"],
                         self.model.current["epochs"])
        return()

    def run_ica(self):
        """Run ICA calculation."""
        try:
            import picard
            import mne.preprocessing.ICA
        except ImportError:
            have_picard = False
            import mne
        else:
            have_picard = True

        try:
            import sklearn  # required for FastICA
        except ImportError:
            have_sklearn = False
        else:
            have_sklearn = True
        if self.model.current["raw"]:
            data = self.model.current["raw"]
            inst_type = "raw"
        elif self.model.current["epochs"]:
            data = self.model.current["epochs"]
            inst_type = "epochs"
        nchan = len(mne.pick_types(data.info,
                                   meg=True, eeg=True, exclude='bads'))
        dialog = RunICADialog(self, nchan, have_picard, have_sklearn)

        if dialog.exec_():
            calc = CalcDialog(self, "Calculating ICA", "Calculating ICA.")
            method = dialog.method.currentText()
            exclude_bad_segments = dialog.exclude_bad_segments.isChecked()
            decim = int(dialog.decim.text())
            n_components = int(dialog.n_components.text())
            max_pca_components = int(dialog.max_pca_components.text())
            n_pca_components = int(dialog.pca_components.text())
            random_state = int(dialog.random_seed.text())
            max_iter = int(dialog.max_iter.text())
            ica = mne.preprocessing.ICA(
                method=dialog.methods[method],
                n_components=n_components,
                max_pca_components=max_pca_components,
                n_pca_components=n_pca_components,
                random_state=random_state,
                max_iter=max_iter)

            pool = mp.Pool(1)
            kwds = {"reject_by_annotation": exclude_bad_segments,
                    "decim": decim}
            res = pool.apply_async(func=ica.fit,
                                   args=(data,),
                                   kwds=kwds, callback=lambda x: calc.accept())
            if not calc.exec_():
                pool.terminate()
            else:
                self.auto_duplicate()
                self.model.current["ica"] = res.get(timeout=1)
                self.model.history.append(
                    "ica=ICA("
                    + ("method={} ,").format(dialog.methods[method])
                    + ("n_components={}, ").format(n_components)
                    + ("max_pca_components={}, ").format(max_pca_components)
                    + ("n_pca_components={}, ").format(n_pca_components)
                    + ("random_state={}, ").format(random_state)
                    + ("max_iter={})").format(max_iter))
                self.model.history.append(
                    "ica.fit("
                    + ("inst={}, ").format(inst_type)
                    + ("decim={}, ").format(decim)
                    + ("reject_by_annotation={})"
                       .format(exclude_bad_segments)))
                self.data_changed()

    def apply_ica(self):
        """Set reference."""
        self.auto_duplicate()
        self.model.apply_ica()

    def resample(self):
        """Resample data."""
        dialog = ResampleDialog(self)
        if dialog.exec_():
            sfreq = dialog.sfreq
            if sfreq is not None:
                self.auto_duplicate()
                if self.model.current['raw']:
                    self.model.current['raw'].resample(sfreq)
                elif self.model.current['epochs']:
                    self.model.current['epochs'].resample(sfreq)
                elif self.model.current['evoked']:
                    self.model.current['evoked'].resample(sfreq)
                self.model.current["name"] += " (resampled)"
                self.data_changed()

    def filter_data(self):
        """Filter data."""
        if self.model.current['raw']:
            israw = True
        else:
            israw = False
        dialog = FilterDialog(self, israw)
        if dialog.exec_():
            if dialog.low or dialog.high or dialog.notch_freqs:
                self.auto_duplicate()
                self.model.filter(dialog.low, dialog.high, dialog.notch_freqs)

    def find_events(self):
        info = self.model.current["raw"].info

        # use first stim channel as default in dialog
        default_stim = 0
        for i in range(info["nchan"]):
            if mne.io.pick.channel_type(info, i) == "stim":
                default_stim = i
                break
        dialog = FindEventsDialog(self, info["ch_names"], default_stim)
        if dialog.exec_():
            stim_channel = dialog.stimchan.currentText()
            consecutive = dialog.consecutive.isChecked()
            initial_event = dialog.initial_event.isChecked()
            uint_cast = dialog.uint_cast.isChecked()
            min_dur = dialog.minduredit.value()
            shortest_event = dialog.shortesteventedit.value()
            self.model.find_events(stim_channel=stim_channel,
                                   consecutive=consecutive,
                                   initial_event=initial_event,
                                   uint_cast=uint_cast,
                                   min_duration=min_dur,
                                   shortest_event=shortest_event)

    def interpolate_bads(self):
        """Interpolate bad channels."""
        self.auto_duplicate()
        self.model.interpolate_bads()

    def add_events(self):
        """Setup the events in the data as a STIM channel."""
        self.auto_duplicate()
        self.model.add_events()

    def epoch_data(self):
        """Cut raw data into epochs."""
        dialog = EpochingDialog(self, self.model.current["events"],
                                self.model.current["raw"])
        if dialog.exec_():
            selected = [int(item.text()) for item
                        in dialog.labels.selectedItems()]
            try:
                tmin = float(dialog.tmin.text())
                tmax = float(dialog.tmax.text())
            except ValueError as e:
                show_error('Unable to compute epochs...', info=str(e))
            else:
                if dialog.baseline.isChecked():
                    try:
                        a = float(float(dialog.a.text()))
                    except ValueError:
                        a = None

                    try:
                        b = float(float(dialog.b.text()))
                    except ValueError:
                        b = None

                    baseline = (a, b)
                else:
                    baseline = None

                self.auto_duplicate()
                self.model.epoch_data(selected, tmin, tmax, baseline)

    def evoke_data(self):
        """Compute the mean of epochs."""
        self.auto_duplicate()
        self.model.evoke_data()

    def set_reference(self):
        """Set reference."""
        dialog = ReferenceDialog(self)
        if dialog.exec_():
            self.auto_duplicate()
            if dialog.average.isChecked():
                self.model.set_reference("average")
            else:
                ref = [c.strip() for c in dialog.channellist.text().split(",")]
                self.model.set_reference(ref)

    def open_batch(self):
        """Open batch processing dialog."""
        dialog = BatchDialog(self)
        dialog.exec_()

    def show_about(self):
        """Show About dialog."""
        msg_box = QMessageBox(self)
        text = ("<h3>MNELAB</h3>"
                "<nobr><p>MNELAB is a graphical user interface for MNE.</p>"
                "</nobr>")
        msg_box.setText(text)

        mnelab_url = "github.com/cbrnr/mnelab"
        mne_url = "github.com/mne-tools/mne-python"

        text = (f'<nobr><p>This program uses MNE version {mne.__version__} '
                f'(Python {".".join(str(k) for k in version_info[:3])}).</p>'
                f'</nobr>'
                f'<nobr><p>MNELAB repository: '
                f'<a href=https://{mnelab_url}>{mnelab_url}</a></p></nobr>'
                f'<nobr><p>MNE repository: '
                f'<a href=https://{mne_url}>{mne_url}</a></p></nobr>'
                f'<p>Licensed under the BSD 3-clause license.</p>'
                f'<p>Copyright 2017-2019 by Clemens Brunner.</p>')
        msg_box.setInformativeText(text)
        msg_box.exec_()

    def show_about_qt(self):
        """Show About Qt dialog."""
        QMessageBox.aboutQt(self, "About Qt")

    def auto_duplicate(self):
        # if current data is stored in a file create a new data set
        if self.model.current["fname"]:
            self.model.duplicate_data()
        # otherwise ask the user
        else:
            msg = QMessageBox.question(self, "Overwrite existing data set",
                                       "Overwrite existing data set?")
            if msg == QMessageBox.No:  # create new data set
                self.model.duplicate_data()

    def _add_recent(self, fname):
        """Add a file to recent file list.

        Parameters
        ----------
        fname : str
            File name.
        """
        if fname in self.recent:  # avoid duplicates
            self.recent.remove(fname)
        self.recent.insert(0, fname)
        while len(self.recent) > MAX_RECENT:  # prune list
            self.recent.pop()
        write_settings(recent=self.recent)
        if not self.recent_menu.isEnabled():
            self.recent_menu.setEnabled(True)

    def _remove_recent(self, fname):
        """Remove file from recent file list.

        Parameters
        ----------
        fname : str
            File name.
        """
        if fname in self.recent:
            self.recent.remove(fname)
            write_settings(recent=self.recent)
            if not self.recent:
                self.recent_menu.setEnabled(False)

    @pyqtSlot(QModelIndex)
    def _update_data(self, selected):
        """Update index and information based on the state of the sidebar.

        Parameters
        ----------
        selected : QModelIndex
            Index of the selected row.
        """
        if selected.row() != self.model.index:
            self.model.index = selected.row()
            self.data_changed()

    @pyqtSlot(QModelIndex, QModelIndex)
    def _update_names(self, start, stop):
        """Update names in DataSets after changes in sidebar."""
        for index in range(start.row(), stop.row() + 1):
            self.model.data[index]["name"] = self.names.stringList()[index]

    @pyqtSlot()
    def _update_recent_menu(self):
        self.recent_menu.clear()
        for recent in self.recent:
            self.recent_menu.addAction(recent)

    @pyqtSlot(QAction)
    def _load_recent(self, action):
        self.model.load(action.text())

    @pyqtSlot()
    def _toggle_statusbar(self):
        if self.statusBar().isHidden():
            self.statusBar().show()
        else:
            self.statusBar().hide()
        write_settings(statusbar=not self.statusBar().isHidden())

    @pyqtSlot(QDropEvent)
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    @pyqtSlot(QDropEvent)
    def dropEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls():
            urls = mime.urls()
            for url in urls:
                self.model.load(url.toLocalFile())

    @pyqtSlot(QEvent)
    def closeEvent(self, event):
        """Close application.

        Parameters
        ----------
        event : QEvent
            Close event.
        """
        write_settings(geometry=self.saveGeometry(), state=self.saveState())
        if self.model.history:
            print("\nCommand History")
            print("===============")
            print("\n".join(self.model.history))
        QApplication.quit()

    def eventFilter(self, source, event):
        # currently the only source is the raw plot window
        if event.type() == QEvent.Close:
            self.data_changed()
        return QObject.eventFilter(self, source, event)
