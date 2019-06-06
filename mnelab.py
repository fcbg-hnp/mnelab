import sys
import matplotlib
from PyQt5.QtWidgets import QApplication
import multiprocessing as mp
import matplotlib.pyplot as plt
from mnelab import MainWindow, Model

plt.style.use('ggplot')

if __name__ == "__main__":
    mp.set_start_method("spawn")  # required for Linux/macOS
    matplotlib.use("Qt5Agg")
    app = QApplication(sys.argv)
    app.setApplicationName("MNELAB")
    app.setOrganizationName("cbrnr - FCBG")
    model = Model()
    view = MainWindow(model)
    model.view = view
    if len(sys.argv) > 1:  # open files from command line arguments
        for f in sys.argv[1:]:
            model.load(f)
    view.show()
    sys.exit(app.exec_())
