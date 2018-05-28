# coding: utf-8

from PyQt5.QtWidgets import QWidget, QPushButton, QFileDialog, QHBoxLayout, QVBoxLayout, QLineEdit, QStatusBar, QProgressBar
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QThread
from modules.PdfHandler import PdfHandler


class MainWindow(QWidget):

    def __init__(self):
        super(MainWindow, self).__init__()
        self.create_elements()
        self.set_property()
        self.add_elements()
        self.clean_file_selection()
        self.add_connect()
        self.STOP = False

    def create_elements(self):
        self.mainLayout = QVBoxLayout()
        self.fileLayout = QHBoxLayout()
        self.fileLine = QLineEdit()
        self.fileButton = QPushButton('Open')
        self.unselectButton = QPushButton('Clean Selections')
        self.inverseButton = QPushButton('Inverse')
        self.fileDialog = QFileDialog(self)
        self.inverseThread = InverseThread(self)
        self.statusBar = QStatusBar(self)
        self.progressBar = QProgressBar()

    def set_property(self):
        # set main window properties
        self.setWindowTitle('Pdf Inverse')
        self.resize(600, 200)

        # set widget properties
        self.fileButton.setToolTip('Click here to open one or more pdf files ro inverse color')
        self.inverseButton.setToolTip('Click here to start inverse')
        self.fileLine.setReadOnly(True)
        self.statusBar.setSizeGripEnabled(False)

    def add_elements(self):
        self.setLayout(self.mainLayout)
        self.mainLayout.addLayout(self.fileLayout)
        self.fileLayout.addWidget(self.fileLine)
        self.fileLayout.addWidget(self.fileButton)
        self.fileLayout.addWidget(self.unselectButton)
        self.mainLayout.addWidget(self.inverseButton)
        self.mainLayout.addWidget(self.progressBar)

    def add_connect(self):
        self.fileButton.clicked.connect(self.open_file_dialog)
        self.unselectButton.clicked.connect(self.clean_file_selection)
        self.inverseButton.clicked.connect(self.inverse)

    @pyqtSlot()
    def open_file_dialog(self):
        self.pdf_path.extend(self.fileDialog.getOpenFileNames(self, 'Choose files to inverse', '.', '*.pdf')[0])
        self.fileLine.setText(str(self.pdf_path))
        self.inverseThread.set_pdf_path(self.pdf_path)

    @pyqtSlot()
    def clean_file_selection(self):
        self.pdf_path = []
        self.fileLine.setText(str(self.pdf_path))
        self.inverseThread.set_pdf_path(self.pdf_path)

    @pyqtSlot()
    def inverse(self):
        self.fileButton.setEnabled(False)
        self.unselectButton.setEnabled(False)
        self.inverseButton.setText('Processing...Click to stop')
        self.inverseButton.clicked.disconnect(self.inverse)
        self.inverseButton.clicked.connect(self.stop)
        self.inverseThread.start()

    @pyqtSlot()
    def stop(self):
        self.STOP = True
        self.inverseButton.clicked.disconnect(self.stop)
        self.inverseButton.clicked.connect(self.inverse)
        self.inverseButton.setEnabled(False)
        self.inverseButton.setText('Stopping...')

class InverseThread(QThread):
    signal = pyqtSignal(int)

    def __init__(self, window):
        super(InverseThread, self).__init__()
        self.window = window
        self.pdfHandler = PdfHandler(window)

    def set_task(self, task):
        self.task = task

    def set_pdf_path(self, pdf_path):
        self.pdf_path = pdf_path

    def run(self):
        for pdf_path in self.pdf_path:
            self.window.progressBar.setValue(0)
            self.pdfHandler.run(pdf_path, self.stop)
            self.pdf_path.remove(pdf_path)
            self.window.statusBar.showMessage('{} inverse Done'.format(pdf_path))
        self.end()

    def end(self):
        self.stop()

    def stop(self):
        self.window.fileButton.setEnabled(True)
        self.window.inverseButton.setEnabled(True)
        self.window.unselectButton.setEnabled(True)
        self.window.inverseButton.setText('Inverse')
        self.window.progressBar.setValue(0)