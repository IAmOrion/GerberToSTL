#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  GerberToSTL.py
#  
#  Created by IAmOrion aka James Tanner
#  This is basically just an app version of https://solder-stencil.me by Robert Kirberich
#  https://github.com/kirberich/gerber_to_scad
#
#  This is my first time ever attempting a Python GUI.  I'm doing so because at the time of creating this, I have no idea how to convert Robert's code into 
#  something I could use in Visual Studio or C/C++ etc.  (Although Python does have the advantage of being cross compatible!).
#  So please excuse the awful and probably sloppy coding :) 
#  
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  Requires: PYQT5, pcb-tools, solidpython, taskipy, scipy

import sys
import os.path
import gerber
import subprocess
import time
import tempfile

from GerberToSTL_UI import *

from sys import platform
from random import randint

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from GTS.conversion import process_gerber

# Global Variables aka Definitions

DEBUG=False
SCAD_BINARY=""
SCAD_BINARY_FOUND=False
OS=""
FILE_OUTLINE=""
FILE_OTHER=""
NO_FILE="No File Selected"
CONVERT_BTN_TEXT="Convert To STL"
LOADING_TEXT="Converting to STL"
CONVERT_SUCCESS=False

class LoadingExtension(object):
	def startLoading(self, timeout=0):
		window = self.window()
		if not hasattr(window, '_loader'):
			window._loader = Loader(window)
		window._loader.start(timeout)

	def finishedLoading(self):
		if hasattr(self.window(), '_loader'):
			self.window()._loader.stop()

class GerberToSTL(QMainWindow, Ui_GerberToSTL):
	def __init__ (self, parent=None):
		super().__init__(parent)
		self.setupUi(self)
		self.btnOpenOutline.clicked.connect(self.OpenOutline)
		self.btnOpenOther.clicked.connect(self.OpenOther)
		self.inputPCB.clicked.connect(self.SelectedPCB)
		self.inputSolderStencil.clicked.connect(self.SelectedSolderStencil)
		self.btnConvertToSTL.clicked.connect(self.ConvertToSTL)
		
		global OS, SCAD_BINARY, SCAD_BINARY_FOUND
		
		if self.inputPCB.isChecked:
			self.SelectedPCB()
		elif self.inputSolderStencil.isChecked:
			self.SelectedSolderStencil()
		
		if platform == "linux" or platform == "linux2":
			# Linux
			OS = "lin"
		elif platform == "darwin":
			# macOS
			OS = "mac"
			SCAD_BINARY="/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
		elif platform == "win32":
			# Windows
			OS = "win"
			SCAD_BINARY_X86="C:\\Program Files (x86)\\OpenSCAD\\openscad.exe"
			SCAD_BINARY="C:\\Program Files\\OpenSCAD\\openscad.exe"
		
		if OS == "mac":
			SCAD_BINARY_FOUND = os.path.isfile(SCAD_BINARY)
		elif OS == "win":
			SCAD_BINARY_FOUND = os.path.isfile(SCAD_BINARY_X86)
			if SCAD_BINARY_FOUND:
				SCAD_BINARY = SCAD_BINARY_X86
			elif not SCAD_BINARY_FOUND:
				SCAD_BINARY_FOUND = os.path.isfile(SCAD_BINARY)

		if DEBUG:
			print("OpenSCAD Found: {}".format(SCAD_BINARY_FOUND))
			if SCAD_BINARY_FOUND:
				print(SCAD_BINARY)
			else:
				if DEBUG:
					print("OpenSCAD not found!")
				self.btnConvertToSTL.setEnabled(False)
				self.btnConvertToSTL.setText("OpenSCAD NOT FOUND!")
		
	def OpenOutline(self):
		global FILE_OUTLINE
		if DEBUG:
			print("You clicked on Open Outline")
		options = QFileDialog.Options()
		options |= QFileDialog.DontUseNativeDialog
		fileNameOutline, _ = QFileDialog.getOpenFileName(None,"Select Outline/Contour", "","Outline/Contour File (*.gm1);;All Files (*)", options=options)
		if fileNameOutline:
			if DEBUG:
				print(fileNameOutline)
			FILE_OUTLINE=fileNameOutline
			self.lblOutlineFile.setText(FILE_OUTLINE)
		else:
			FILE_OUTLINE=""
			self.lblOutlineFile.setText(NO_FILE)

	def OpenOther(self):
		global FILE_OTHER
		if DEBUG:
			print("You clicked on Open Other")
		options = QFileDialog.Options()
		options |= QFileDialog.DontUseNativeDialog
		if self.inputPCB.isChecked():
			fileNameOther, _ = QFileDialog.getOpenFileName(None,"Select Mask", "","Mask Top File (*.gts);;Mask Bottom File (*.gbs);;All Files (*)", options=options)
		elif self.inputSolderStencil.isChecked():
			fileNameOther, _ = QFileDialog.getOpenFileName(None,"Select Paste Mask", "","Paste Mask Top File (*.gtp);;Paste Mask Bottom File (*.gbp);;All Files (*)", options=options)
		if fileNameOther:
			if DEBUG:
				print(fileNameOther)
			FILE_OTHER=fileNameOther
			self.lblOtherFile.setText(FILE_OTHER)
		else:
			FILE_OTHER=""
			self.lblOtherFile.setText(NO_FILE)
		
	def SelectedPCB(self):
		if DEBUG:
			print("You Selected PCB")
			
		self.inputIncludeLedge.setChecked(False)
		self.inputIncludeLedge.setEnabled(False)
		self.inputThickness.setProperty("value", 1.6)
		self.inputHeight.setProperty("value", 0.0)
		self.inputHeight.setEnabled(False)
		self.inputGap.setProperty("value", 0.0)
		self.inputGap.setEnabled(False)
		
	def SelectedSolderStencil(self):
		if DEBUG:
			print("You Selected Solder Stencil")
			
		self.inputIncludeLedge.setChecked(True)
		self.inputIncludeLedge.setEnabled(True)
		self.inputThickness.setProperty("value", 0.2)
		self.inputHeight.setProperty("value", 1.2)
		self.inputHeight.setEnabled(True)
		self.inputGap.setProperty("value", 0.0)
		self.inputGap.setEnabled(True)
		
	def MessageBox(self, MessageBoxTitle="Default Title", MessageBoxMessage="Default Message", MessageIcon="i"):
		# MessageIcon options = i, w, c, q - being Information, Warning, Critical, Question 
		if DEBUG:
			print("MessageBox - Title: " + MessageBoxTitle + ", Message: " + MessageBoxMessage + ", MessageIcon: " + MessageIcon)
		
		msg = QMessageBox()
		
		match MessageIcon:
			case 'i':
				msg.setIcon(QMessageBox.Information)	
			case 'w':
				msg.setIcon(QMessageBox.Warning)
			case 'c':
				msg.setIcon(QMessageBox.Critical)	
			case 'q':
				msg.setIcon(QMessageBox.Question)
			case _:
				msg.setIcon(QMessageBox.Critical)

		# setting MESSAGE for Message Box
		msg.setText(MessageBoxMessage)

		# setting TITLE for Message Box
		msg.setWindowTitle(MessageBoxTitle)

		# declaring buttons on Message Box
		# msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
		msg.setStandardButtons(QMessageBox.Ok)

		# start the app
		retval = msg.exec_()
		
	def isProcessing(self):
		self.btnConvertToSTL.setText("Processing")
		self.btnConvertToSTL.setEnabled(False)
		LoadingExtension.startLoading(self)
		
	def isDone(self):
		self.btnConvertToSTL.setText(CONVERT_BTN_TEXT)
		self.btnConvertToSTL.setEnabled(True)
		LoadingExtension.finishedLoading(self)
		
		if DEBUG:
			print("Convert Success: {}".format(CONVERT_SUCCESS))

		if CONVERT_SUCCESS:
			saveFilename = QFileDialog.getSaveFileName(None, "Save STL", save_filename, "STL File (*.stl)")[0]
			
			if saveFilename:
				if DEBUG:
					print("File saved to: " + saveFilename)
				saveFile = open(saveFilename,'w')
				saveFile.write(stl_data)
				saveFile.close()
			else:
				if DEBUG:
					print("User cancelled!")
				self.MessageBox("Save cancelled","You decided not to save the STL","w")
		else:
			self.MessageBox("Error converting files...","Unfortuantely something went wrong, please double check the files you've selected are Gerber Files","c")

	def ConvertToSTL(self):
		if DEBUG:
			print("You Clicked on ConvertToSTL")
			
		#self.btnConvertToSTL.setText("Processing...")
		#self.btnConvertToSTL.setEnabled(False)		
		
		if not (FILE_OUTLINE and FILE_OTHER):
			if DEBUG:
				print("You MUST select BOTH files!")
			self.MessageBox("Error...","You must select both an Outline and a Mask in order to generate your STL","i")
			self.btnConvertToSTL.setText(CONVERT_BTN_TEXT)
			self.btnConvertToSTL.setEnabled(True)	
		else:
			if DEBUG:
				print("Outline: " + FILE_OUTLINE)
				if self.inputPCB.isChecked():
					print("Mask Top: " + FILE_OTHER)
				elif self.inputSolderStencil.isChecked():
					print("Paste Mask Top: " + FILE_OTHER)
					
			self.thread = Thread(self)
			
			self.thread.tThickness = self.inputThickness.value()
			self.thread.tLedge = self.inputIncludeLedge.isChecked()
			self.thread.tHeight = self.inputHeight.value()
			self.thread.tGap = self.inputGap.value()
			self.thread.tHoleSize = self.inputIncreaseHoleSize.value()
			self.thread.tReplaceRegions = self.inputReplaceRegions.isChecked()
			self.thread.tFlip = self.inputFlip.isChecked()
			
			self.thread.started.connect(self.isProcessing)
			self.thread.finished.connect(self.isDone)
			
			self.thread.start()
				
class Thread(QThread):
	#progressChanged = pyqtSignal(int)
	
	def __init__(self, parent):
		super().__init__()
		self.window = parent
        
	def run(self):
		if DEBUG:
			print("Running Thread...")
			
		global CONVERT_SUCCESS
			
		# Processing Files!
		outline_file = open(FILE_OUTLINE, "r")
		other_file = open(FILE_OTHER, "r")
		
		outline = None
		other = None
		
		try:
			outline = gerber.loads(outline_file.read())
		except:
			if DEBUG:
				print("An exception occurred trying to open OUTLINE")
			pass
			
		try:
			other = gerber.loads(other_file.read())
		except:
			if DEBUG:
				print("An exception occurred trying to load OTHER")
			pass
		
		if outline and other:
			output = process_gerber(
				outline,
				other,
				self.tThickness,
				self.tLedge,
				self.tHeight,
				self.tGap,
				self.tHoleSize,
				self.tReplaceRegions,
				self.tFlip,
			)
			
			file_id = randint(1000000000, 9999999999)
			scad_filename = tempfile.gettempdir() + "/gerbertostl-{}.scad".format(file_id)
			stl_filename = tempfile.gettempdir() + "/gerbertostl-{}.stl".format(file_id)
			global save_filename
			save_filename = "gerbertostl-{}.stl".format(file_id)
			
			with open(scad_filename, "w") as scad_file:
				scad_file.write(output)
				
			p = subprocess.Popen(
				[
					SCAD_BINARY,
					"-o",
					stl_filename,
					scad_filename,
				]
			)
			p.wait()

			if p.returncode:
				if DEBUG:
					print("Failed to create an STL file from inputs")
			else:
				with open(stl_filename, "r") as stl_file:
					global stl_data
					stl_data = stl_file.read()
				os.remove(stl_filename)
				
			# Clean up temporary files
			os.remove(scad_filename)
			
			CONVERT_SUCCESS=True
		else:
			if DEBUG:
				print("There was an error with the selected files!")
			CONVERT_SUCCESS=False

		
class Loader(QWidget):
	def __init__(self, parent):
		super().__init__(parent)

		self.gradient = QtGui.QConicalGradient(.5, .5, 0)
		self.gradient.setCoordinateMode(self.gradient.ObjectBoundingMode)
		self.gradient.setColorAt(.25, QtCore.Qt.transparent)
		self.gradient.setColorAt(.75, QtCore.Qt.transparent)

		self.animation = QtCore.QVariantAnimation(
			startValue=0., endValue=1., 
			duration=1000, loopCount=-1, 
			valueChanged=self.updateGradient
			)

		self.stopTimer = QtCore.QTimer(singleShot=True, timeout=self.stop)

		self.focusWidget = None
		self.hide()
		parent.installEventFilter(self)

	def start(self, timeout=None):
		self.show()
		self.raise_()
		self.focusWidget = QtWidgets.QApplication.focusWidget()
		self.setFocus()
		if timeout:
			self.stopTimer.start(timeout)
		else:
			self.stopTimer.setInterval(0)

	def stop(self):
		self.hide()
		self.stopTimer.stop()
		if self.focusWidget:
			self.focusWidget.setFocus()
			self.focusWidget = None

	def updateGradient(self, value):
		self.gradient.setAngle(-value * 360)
		self.update()

	def eventFilter(self, source, event):
		# ensure that we always cover the whole parent area
		if event.type() == QtCore.QEvent.Resize:
			self.setGeometry(source.rect())
		return super().eventFilter(source, event)

	def showEvent(self, event):
		self.setGeometry(self.parent().rect())
		self.animation.start()

	def hideEvent(self, event):
		# stop the animation when hidden, just for performance
		self.animation.stop()

	def paintEvent(self, event):
		qp = QtGui.QPainter(self)
		qp.setRenderHints(qp.Antialiasing)
		color = self.palette().window().color()
		color.setAlpha(max(color.alpha() * .5, 128))
		qp.fillRect(self.rect(), color)

		text = LOADING_TEXT
		interval = self.stopTimer.interval()
		if interval:
			remaining = int(max(0, interval - self.stopTimer.remainingTime()) / interval * 100)
			textWidth = self.fontMetrics().width(text + ' 000%')
			text += ' {}%'.format(remaining)
		else:
			textWidth = self.fontMetrics().width(text)
		textHeight = self.fontMetrics().height()
		# ensure that there's enough space for the text
		if textWidth > self.width() or textHeight * 3 > self.height():
			drawText = False
			size = max(0, min(self.width(), self.height()) - textHeight * 2)
		else:
			size = size = min(self.height() / 3, max(textWidth, textHeight))
			drawText = True

		circleRect = QtCore.QRect(0, 0, size, size)
		circleRect.moveCenter(self.rect().center())

		if drawText:
			# text is going to be drawn, move the circle rect higher
			circleRect.moveTop(circleRect.top() - textHeight)
			middle = circleRect.center().x()
			qp.drawText(
				int(middle - textWidth / 2), int(circleRect.bottom() + textHeight), 
				textWidth, textHeight, 
				QtCore.Qt.AlignCenter, text)

		self.gradient.setColorAt(.5, self.palette().windowText().color())
		qp.setPen(QtGui.QPen(self.gradient, textHeight))
		qp.drawEllipse(circleRect)

	
if __name__ == "__main__":
	app = QApplication(sys.argv)
	#MainWindow = QMainWindow()
	#ui = GerberToSTL(MainWindow)
	#MainWindow.show()
	MainWindow=GerberToSTL()
	MainWindow.show()
	app.exec_()
