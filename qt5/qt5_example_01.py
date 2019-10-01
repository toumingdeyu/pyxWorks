#!/usr/bin/python36


### pip install pyqt5 --no-cache-dir, pip install pyqt5.sip --no-cache-dir
import sys, os, io, paramiko, json , copy, six, collections 
 
from PyQt5.QtWidgets import *

### https://build-system.fman.io/pyqt5-tutorial

app = QApplication([])

window = QWidget()
layout = QVBoxLayout()
layout.addWidget(QLabel('Hello World!'))
layout.addWidget(QPushButton('Top'))
layout.addWidget(QPushButton('Bottom'))

window.setLayout(layout)
window.show()

app.exec_()
