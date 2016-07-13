#!/usr/bin/env python
from sys import argv
import sys
import os
import math
import numpy as np
from skimage import transform
from PyQt4 import QtGui, QtCore
import qimage2ndarray

class mrc(object):
    def __init__(self, x = 0, y = 0, z = 0, data = 0):
        self.nx = x
        self.ny = y
        self.nz = z
        self.data = data

    def readFromFile(self, filename, startSlice=1, numSlices=1000000000):
        with open(filename, 'r') as file:
            a = np.fromfile(file, dtype=np.int32, count=10)
            shouldSwap = 0
            if abs(a[0] > 100000):
                a.byteswap()
                shouldSwap = 1

            mode = a[3]

            b = np.fromfile(file, dtype=np.float32, count=12)
            if shouldSwap:
                b.byteswap()

            mi = b[9]
            ma = b[10]
            mv = b[11]


            c = np.fromfile(file, dtype=np.int32, count=30)
            if shouldSwap:
                c.byteswap()

            d = np.fromfile(file, dtype=np.uint8, count=8)
            if shouldSwap:
                d.byteswap()

            e = np.fromfile(file, dtype=np.int32, count = 2)
            if shouldSwap:
                e.byteswap()

            ns = min(e[1],10)
            for i in range(1,11):
                g = np.fromfile(file, dtype=np.uint8, count = 80)

            self.nx = a[0]
            self.ny = a[1]
            self.nz = a[2]

            datatype = np.float32
            if mode == 0:
                datatype = np.int8
            elif mode == 1:
                datatype = np.int16
            elif mode == 2:
                datatype = np.float32
            elif mode == 6:
                datatype = np.uint16


            if c[1] > 0:
                extraHeader = np.fromfile(file, dtype=np.uint8, count = c[1])

            nz = self.nz
            if startSlice > 1:
                discard = np.fromfile(file, dtype=datatype, count = (startSlice - 1) * self.nx * self.ny)
                nz = min(self.nz - (startSlice - 1), numSlices)

            self.nz = nz
            ndata = self.nx * self.ny * self.nz

            originalData = np.fromfile(file, dtype=datatype, count=ndata)
            if shouldSwap:
                originalData.byteswap()
            originalData.resize((self.nx, self.ny, self.nz))
            # swappedData = originalData.transpose((1, 0, 2))
            swappedData = originalData
            self.data = swappedData.astype(np.int32)

    def calculateStatistics(self):
        return (self.data.mean(), self.data.std(), self.data.min(), self.data.max())

    def getImageContrast(self, sigmaContrast):
        (avg, stddev, minval, maxval) = self.calculateStatistics()
        if sigmaContrast > 0:
            minval = avg - sigmaContrast * stddev
            maxval = avg + sigmaContrast * stddev
            newData = self.data
            self.data.clip(minval, maxval, newData)
            self.data = newData

    def extract2DBox(self, x, y, z, boxsize):
        newData = np.ndarray(shape=(boxsize,boxsize,1), dtype=np.float32)
        newData.fill(0);
        xo = x - boxsize / 2
        yo = y - boxsize / 2

        for x in range(0, boxsize):
            if (x+xo >= 0) and (x+xo < self.nx):
                for y in range(0, boxsize):
                    if (y+yo >= 0) and (y+yo < self.ny):
                        newData[x,y,0] = self.data[x+xo,y+yo,z]

        return mrc(boxsize, boxsize, 1, newData)

    def x(self):
        return self.nx

    def y(self):
        return self.ny

    def get2DPoint(self, x, y):
        return self.data[x, y, 0]

    def generateImage(self, scale=1.0):
        if (scale != 1.0):
          self.data = transform.rescale(self.data, scale)
          self.nx = self.data.shape[0]
          self.ny = self.data.shape[1]
        im = qimage2ndarray.array2qimage(self.data, normalize=True)
        return im

#   Better to do this and use the contrast of the entire image, rather than just extracted box...
    def generateImageOf2DBox(self, xc, yc, zc, boxsize):
        (avg, stddev, minval, maxval) = self.calculateStatistics()
        range = maxval - minval
        step = range / 255.0
        
        xo = xc - boxsize / 2
        yo = yc - boxsize / 2
        
        if ((xo >= 0) and (xo + boxsize < self.nx) and (yo >= 0) and (yo + boxsize < self.ny)):
            newData = self.data[xo:xo+boxsize, yo:yo+boxsize, zc:zc+1]
        else:
            extractX = boxsize
            extractY = boxsize
            offsetX = 0
            offsetY = 0
            if xo < 0:
                extractX += xo
                offsetX = xo * -1
                xo = 0
            elif xo + boxsize > self.nx:
                extractX = self.nx - xo
            if yo < 0:
                extractY += yo
                offsetY = yo * -1
                yo = 0
            elif yo + boxsize > self.ny:
                extractY = self.ny - yo
            print('Xo: ' + str(xo) + ' exX: ' + str(extractX) + ' ofX: ' + str(offsetX) + ' Yo: ' + str(yo) + ' exY: ' + str(extractY) + ' ofY: ' + str(offsetY))
            box = self.data[xo:xo+extractX, yo:yo+extractY, zc:zc+1]
            newData = np.ndarray(shape=(boxsize,boxsize,1), dtype=np.float32)
            newData.fill(minval + range/2);
            newData[offsetX:offsetX+extractX, offsetY:offsetY+extractY] = box


        im = QtGui.QImage(boxsize - 1, boxsize - 1, QtGui.QImage.Format_RGB32)
        for x in xrange(0, boxsize - 1):
            for y in xrange(0, boxsize - 1):
                intval = int(math.floor((newData[x,y,0] - minval) / step))
                RGBval = 255 << 24 | intval << 16 | intval << 8 | intval
                im.setPixel(x, y, RGBval)
        return im

class mrcView(QtGui.QWidget):

    def __init__(self):
        super(mrcView, self).__init__()
        self.scale = 1.0
        self.sigmaContrast = 0
        self.mView = 0
        self.initUI()
        self.currentMRCFile = 0
        self.newRootExt = ''
        self.origRootExt = ''
        self.im = 0
        self.newPicks = []
        self.origPicks = []
        self.boxsize = 100
        self.mouseStart = 0
        self.transferPickStart = 0
        self.micrographName = ''
        self.leftButtonDown = False
        self.mouseMoveRect = 0
        self.modifiedPicks = False

    def initUI(self):
        self.setMinimumSize(300,300)

        self.show()

    def setScale(self, scale):
      self.scale = scale

    def setSigmaContrast(self, sc):
      self.sigmaContrast = sc

    def setNewPickRootName(self, newName):
      self.newRootExt = newName

    def setOrigRootName(self, origName):
      self.origRootExt = origName

    def setBoxSize(self, boxsize):
      self.boxsize = boxsize
    
    def getModifiedPicks(self):
      return self.modifiedPicks

    def mousePressEvent(self, event):
      if event.button() == QtCore.Qt.LeftButton:
        self.mouseStart = (event.x(), event.y())
        self.leftButtonDown = True
      if event.button() == QtCore.Qt.RightButton:
        self.transferPickStart = (event.x(), event.y())

    def mouseMoveEvent(self, event):
      if self.leftButtonDown:
        self.mouseMoveRect = (event.x(), event.y())
        self.update()

    def mouseReleaseEvent(self, event):
      if event.button() == QtCore.Qt.LeftButton:
        self.leftButtonDown = False
        updatedPicks = []
        left = right = bottom = top = 0
        if (event.y() > self.mouseStart[1]):
          bottom = event.y()
          top = self.mouseStart[1]
        else:
          bottom = self.mouseStart[1]
          top = event.y()
        if (event.x() < self.mouseStart[0]):
          left = event.x()
          right = self.mouseStart[0]
        else:
          left = self.mouseStart[0]
          right = event.x()
        # print 'l: ' + str(left) + 'r: ' + str(right) + 't: ' + str(top) + 'b: ' + str(bottom)
        for pick in self.newPicks:
          px = pick[0] * self.scale
          py = pick[1] * self.scale
          if not ((px > left) and (px < right) and (py < bottom) and (py > top)):
            updatedPicks.append(pick)
          else:
            self.modifiedPicks = True
        self.newPicks = updatedPicks
        self.update()

      dist = (self.scale * self.boxsize * 0.5)**2
      if event.button() == QtCore.Qt.RightButton and event.x() == self.transferPickStart[0] and event.y() == self.transferPickStart[1]:
        pick = [p for p in self.origPicks if (p[0] * self.scale - event.x())**2 + (p[1] * self.scale - event.y())**2 < dist]
        if pick:
          self.newPicks.append(pick[0])
          self.origPicks.remove(pick[0])
          self.modifiedPicks = True
          self.update()


    def savePicks(self):
      m = self.micrographName
      star_name = m[0:str(m).find('.mrc')] + self.newRootExt
      try:
          star = open(star_name, 'w')
      except IOError:
          print('Can not save %s'%m)
      else:
        star.write('\n')
        star.write('data_\n')
        star.write('\n')
        star.write('loop_ \n')
        star.write('_rlnCoordinateX #1 \n')
        star.write('_rlnCoordinateY #2 \n')
        star.write('_rlnAnglePsi #3 \n')
        star.write('_rlnClassNumber #4 \n')
        star.write('_rlnAutopickFigureOfMerit #5 \n')
        for pick in self.newPicks:
          star.write('%f\t%f\t%f\t%d\t%f\n'%(pick[0], pick[1], pick[2], pick[3], pick[4]))
        star.write('\n')
        star.close()
        self.modifiedPicks = False
        print('Saved %s with %d particles'%(m,len(self.newPicks)))

    def setMRC(self, m):
      self.modifiedPicks = False
      self.micrographName = m
      self.currentMRCFile = mrc()
      self.currentMRCFile.readFromFile(m)
      self.currentMRCFile.getImageContrast(self.sigmaContrast)
      image = self.currentMRCFile.generateImage(scale=self.scale)
      # self.mView.setPixmap(QtGui.QPixmap.fromImage(image))
      self.im = image
      self.setMinimumSize(image.size())

      self.newPicks = []
      star_name = m[0:str(m).find('.mrc')] + self.newRootExt
      try:
          star = open(star_name, 'r')
      except IOError:
          print('No data found for %s'%star_name)
      else:
        for l in range(0,9):
          star.readline()
        for line in star:
          if line.strip():
            fields = line.split()
            xc = int(float(fields[0]))
            yc = int(float(fields[1]))
            psi = int(float(fields[2]))
            cn = int(float(fields[3]))
            fom = float(fields[4])
            self.newPicks.append((xc, yc, psi, cn, fom))
        star.close()
      self.update()

      self.origPicks = []
      star_name = m[0:str(m).find('.mrc')] + self.origRootExt
      try:
          star = open(star_name, 'r')
      except IOError:
          print('No data found for %s'%star_name)
      else:
        for l in range(0,9):
          star.readline()
        for line in star:
          if line.strip():
            fields = line.split()
            xc = int(float(fields[0]))
            yc = int(float(fields[1]))
            psi = int(float(fields[2]))
            cn = int(float(fields[3]))
            fom = float(fields[4])
            if (xc, yc, psi, cn, fom) not in self.newPicks:
              self.origPicks.append((xc, yc, psi, cn, fom))
        star.close()
      self.update()


    def paintEvent(self, e):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.drawImage(QtCore.QPoint(0,0), self.im)
        qp.setPen(QtGui.QColor(0,255,0))
        r = self.boxsize * self.scale * 0.5
        for pick in self.newPicks:
          qp.drawEllipse(QtCore.QPoint(pick[0]*self.scale,pick[1]*self.scale), r, r)
        qp.setPen(QtGui.QColor(255,0,0))
        if self.leftButtonDown:
          qp.drawRect(self.mouseStart[0], self.mouseStart[1], self.mouseMoveRect[0] - self.mouseStart[0], self.mouseMoveRect[1] - self.mouseStart[1])
        for pick in self.origPicks:
          qp.drawEllipse(QtCore.QPoint(pick[0]*self.scale,pick[1]*self.scale), r, r)
        qp.end()


class MainWindow(QtGui.QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        self.initUI()

    def initUI(self):
        self.widget = MainWidget()
        self.setCentralWidget(self.widget)

        self.statusbar = self.statusBar()
        self.widget.msg2Statusbar[str].connect(self.statusbar.showMessage)

        self.resize(300, 300)
        self.setWindowTitle('Compare Picked Particles')
        self.show()

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Escape:
          self.close()
        if e.key() == QtCore.Qt.Key_P:
          self.widget.loadPrevMicrograph()
        if e.key() == QtCore.Qt.Key_N:
          self.widget.loadNextMicrograph()
        if e.key() == QtCore.Qt.Key_S:
          self.widget.savePicks()

class MainWidget(QtGui.QWidget):
    
    msg2Statusbar = QtCore.pyqtSignal(str)

    def __init__(self):
        super(MainWidget, self).__init__()
        self.mrcView = 0
        self.micrographs = {}
        self.newRootExt = ''
        self.origRootExt = ''
        self.boxsize = 0
        self.scale = 1.0
        self.sigmaContrast = 0
        self.currentMRCIndex = -1
        self.pickInputList = []
        self.currentMRCFile = 0
        self.apix = 1.0
        self.initUI()
    
    def initUI(self):
        
        savebtn = QtGui.QPushButton('Save', self)
        savebtn.clicked.connect(self.saveButtonClicked)
                
        qbtn = QtGui.QPushButton('Quit', self)
        qbtn.clicked.connect(QtCore.QCoreApplication.instance().quit)

        self.listWidget = QtGui.QListWidget()
        self.listWidget.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.listWidget.itemSelectionChanged.connect(self.checkForChangedPicks)
        self.listWidget.setMinimumWidth(400)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(savebtn)
        vbox.addWidget(self.listWidget)
        vbox.addWidget(qbtn)
        
        self.mrcView = mrcView()
        
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.mrcView)
        hbox.addLayout(vbox)
        
        self.setLayout(hbox)
        
        self.show()

    def checkForChangedPicks(self):
      if self.mrcView.getModifiedPicks():
        msg = QtGui.QMessageBox()
        msg.setIcon(QtGui.QMessageBox.Warning)

        msg.setText("Current image picks have changed")
        msg.setInformativeText("Do you wish to save these changes?")
        msg.setWindowTitle("Image picks have changed")
        msg.setStandardButtons(QtGui.QMessageBox.Save | QtGui.QMessageBox.Discard)
        msg.setDefaultButton(QtGui.QMessageBox.Save)
        ret = msg.exec_()
        if ret == QtGui.QMessageBox.Save:
          self.mrcView.savePicks()
      
      self.micrographSelected()


    def micrographSelected(self):
      selection = self.listWidget.selectedItems()
      self.currentMRCIndex = self.listWidget.row(selection[0])
      m = selection[0].text()
      self.setFocus()
      self.msg2Statusbar.emit('Image ' + str(self.currentMRCIndex + 1) + '/' + str(len(self.micrographs)) + ' ' + m)
      self.mrcView.setMRC(m)

    def setImage(self, image):
        self.mView.setPixmap(QtGui.QPixmap.fromImage(image))

    def savePicks(self):
      self.mrcView.savePicks()

    def setMicrographs(self, list):
      self.micrographs = list
      for m in self.micrographs.keys():
          item = QtGui.QListWidgetItem()
          item.setText(m)
          self.listWidget.addItem(item)
      self.listWidget.sortItems(QtCore.Qt.AscendingOrder)
      self.currentMRCIndex = 0;
      firstItem = self.listWidget.item(0)
      self.listWidget.setItemSelected(firstItem, True)

    def loadNextMicrograph(self):
      self.currentMRCIndex += 1
      nextItem = self.listWidget.item(self.currentMRCIndex);
      self.listWidget.setItemSelected(nextItem, True)      

    def loadPrevMicrograph(self):
      self.currentMRCIndex -= 1
      nextItem = self.listWidget.item(self.currentMRCIndex);
      self.listWidget.setItemSelected(nextItem, True)            

    def setNewPickRootName(self, newName):
      self.newRootExt = newName
      self.mrcView.setNewPickRootName(newName)
    
    def setOrigRootName(self, origName):
      self.origRootExt = origName
      self.mrcView.setOrigRootName(origName)

    def setBoxSize(self, boxsize):
      self.boxsize = boxsize
      self.mrcView.setBoxSize(boxsize)
    
    def setScale(self, scale):
        self.scale = scale
        self.mrcView.setScale(scale)
    
    def setSigmaContrast(self, sc):
        self.sigmaContrast = sc
        self.mrcView.setSigmaContrast(sc)

    def saveButtonClicked(self):
      self.savePicks()

    def nButtonClicked(self):
        self.loadNextBox(isParticle=0)

    def loadNextBox(self, isParticle = 0):
        shouldLoadMRC = 0
        
        if self.currentMRCIndex < 0:
            shouldLoadMRC = 1
        else:
            currentString = self.pickInputList[self.currentBoxIndex]
            self.autopickOutString += currentString[0:len(currentString) - 1]
            if isParticle:
                self.autopickOutString += 'P\n'
            else:
                self.autopickOutString += 'N\n'
            self.currentBoxIndex = self.currentBoxIndex + 1
        
            if self.currentBoxIndex == len(self.pickInputList):
                shouldLoadMRC = 1
                self.currentBoxIndex = 0
                pickOutputName = self.micrographs[self.currentMRCIndex][0:self.micrographs[self.currentMRCIndex].find('.mrc')] + self.outputRootName
                with open(pickOutputName, 'w') as outputFile:
                    outputFile.write(self.autopickOutString)

        if shouldLoadMRC:
            self.currentMRCIndex = self.currentMRCIndex + 1
            pickInputName = self.micrographs[self.currentMRCIndex][0:self.micrographs[self.currentMRCIndex].find('.mrc')] + self.inRootExt
            #            print pickInputName
            self.autopickOutString = '';
            with open(pickInputName, 'r') as pickInputFile:
                for l in range(0,9):
                    self.autopickOutString += pickInputFile.readline()
                for line in pickInputFile:
                    if line.strip():
                        self.pickInputList.append(line)
            
            self.currentMRCFile = mrc()
            self.currentMRCFile.readFromFile(self.micrographs[self.currentMRCIndex])
            self.currentMRCFile.getImageContrast(self.sigmaContrast)
            

        

        newBoxString = self.pickInputList[self.currentBoxIndex]
        fields =  newBoxString.split()
        xc = int(float(fields[0]))
        yc = int(float(fields[1]))
        
        image = self.currentMRCFile.generateImage()
        if self.scale != 1.0:
            scaledImage = image.scaledToWidth(self.boxsize * self.scale)
        else:
            scaledImage = image
        self.setImage(scaledImage)


def main():
    try:
        starFileName = str(sys.argv[1])
        newPickRootName = str(sys.argv[2])
        origPickRootName = str(sys.argv[3])
        boxsize = int(sys.argv[4])
        sigmaContrast = float(sys.argv[5])
        scale = float(sys.argv[6])
    except:
        print '\nUsage: pickComparitor.py starFileName newPickRoot originalPickRoot boxsize sigmaContrast scale\n'
        raise SystemExit

#   Get list of Images for source of training material

    micrograph_data = {}
    searchFields = ['_rlnMicrographName']
    searchDict = {}
    with open(starFileName, 'r') as starFile:
      for l in range(0,15):
        line = starFile.readline()
        if line.strip():
          fields = line.split()
          if fields[0] in searchFields:
            searchDict[fields[0]] = int(fields[1][1:]) - 1
      for line in starFile:
        if line.strip():
          fields = line.split()
          mrc_name = fields[searchDict['_rlnMicrographName']]
          micrograph_data[mrc_name] = mrc_name

    app = QtGui.QApplication(sys.argv)
    wi = MainWindow()
    wi.widget.setScale(scale)
    wi.widget.setSigmaContrast(sigmaContrast)
    wi.widget.setNewPickRootName(newPickRootName)
    wi.widget.setOrigRootName(origPickRootName)
    wi.widget.setBoxSize(boxsize)
    wi.widget.setMicrographs(micrograph_data)
    sys.exit(app.exec_())



if __name__ == '__main__':
    main()
