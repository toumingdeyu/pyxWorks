#!/usr/bin/python36

import sys

### pip install PyQtWebEngine

from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWebEngineWidgets import QWebEngineView

### SIMPLE WINDOW WITH CONTENT OF WEB PAGE

app = QApplication(sys.argv)
wv = QWebEngineView()
wv.load(QUrl("https://pypi.python.org/pypi/PyQt5"))
wv.show()
app.exec_()
