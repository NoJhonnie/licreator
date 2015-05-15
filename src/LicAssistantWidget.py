"""
    Lic - Instruction Book Creation software
    Copyright (C) 2015 Jeremy Czajkowski

    This file (LicAssistantWidget.py) is part of Lic.

    Lic is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Lic is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see http://www.gnu.org/licenses/
"""

import thread

from PyQt4.Qt import *  

from LicModel import Step, PLIItem, Part, PLI
from LicQtWrapper import ExtendedLabel
from LicUndoActions import MovePartsToStepCommand , AddRemovePageCommand
import LicGLHelpers
import os
import Image
import urllib2
import config
import tempfile
from LicCustomPages import Page
from LicHelpers import SUBWINDOW_BACKGROUND
from LicDialogs import MessageDlg
import LicHelpers


shortcuts = {
     1: ["Move vertically with 20 steps","Shift+Down | Up"]
    ,2: ["Move vertically with 5 steps","Ctrl+Down | Up"]
    ,3: ["Jump to next step on current page","Tab"]
    ,4: ["Move horizontally with 20 steps","Shift+Right | Left"]
    ,5: ["Move horizontally with 5 steps","Ctrl+Right | Left"]
    ,6: ["Jump to next page","PageDown"]
    ,7: ["Jump to previous page","PageUp"]
    ,8: ["Go to first or title page","Home"]
    ,9: ["Go to last page","End"]
    ,10:["Show or hide rules","F6"]
    ,11: ["Show or hide this pop-up window","F1"]
}

class LicWorker(QObject):
    """
    You can't move widgets into another thread - in order to keep user interface responsive, 
    Qt needs to do all GUI work inside main thread.
    
    If you have background work to do, then move background worker to other thread, and not the user interface.
    """       
    
    def __init__(self ,fnList=[]):
        QObject.__init__(self)  
        
        self._counter =0
        self._fn =fnList
        
        self._workerThread = QThread()        
        self._workerThread.started.connect(self._doLongWork)   
        self._workerThread.finished.connect(self._doFinishWork)             
        self._workerThread.terminated.connect(self._doFinishWork)             
    
    def start(self):
        self._workerThread.start()
        
    def terminate(self):
        self._workerThread.terminate()
        
    def _doFinishWork(self):
        self._counter =0  
        self._fn =[]
    
    def _doLongWork(self ,ident=0):
        try:
            self._fn[ident]()
        except:
            self._workerThread.terminate()
            pass
        else:
            #  Long running operations can call PySide.QtCore.QCoreApplication.processEvents()
            #  to keep the application responsive.
            #
            # This is necessary to handle self._fn content correctly. Like refresh pixmap in loop.
            QCoreApplication.processEvents()
        self._counter +=1
        
        if self._counter == self._fn.__len__():
            self._workerThread.quit()
        else:
            self._doLongWork(self._counter)

class LicDownloadAssistant(MessageDlg):
    repositoryHost = "https://raw.githubusercontent.com"
    fileToDownload = ["/Jeremy1980/licreator/master/.settings/codes.ini"]
    hasConnection  = False
    
    def __init__(self ,parent=None ,host=None):
        MessageDlg.__init__(self,parent)     
        self.reset()
        self.button1.setPixmap( QCommonStyle().standardIcon (QStyle.SP_BrowserReload).pixmap(16,16) )
        self.connect(self.button1,SIGNAL("clicked()"),self.reload)
        
        self.worker = LicWorker([self.job_1,self.job_2])
        self.host = host if isinstance(host, str) else self.repositoryHost

    def showEvent(self, *args, **kwargs):
        self.worker.start()
        return MessageDlg.showEvent(self, *args, **kwargs)
    
    def reset(self):
        self.setText("Waiting for connection...") 
        self.button1.hide()
        
    def reload(self):
        self.reset()
        try:
            del self.worker
            self.worker = LicWorker([self.job_1,self.job_2])
        finally:
            self.worker.start()
        
    def internet_on(self):
        """
         Using a numerical IP-address avoids a DNS lookup, which may block the urllib2.urlopen 
         call for more than a second. 
         By specifying the timeout=1 parameter, the call to urlopen will not take much longer 
         than 1 second even if the internet is not "on".
        """
        try:
            response=urllib2.urlopen(self.host,timeout=1)
            return True
        except urllib2.URLError as err: 
            pass
        return False

    def download_file(self,url):
        """
        File downloading from the web.
        Copy the contents of a file from a given URL
        to a local file.
        """
        webFile = urllib2.urlopen(url)
        basename = url.split('/')[-1]
        filename = os.path.join( config.grayscalePath() , basename ) 
        localFile = open(filename, 'w')
        localFile.write(webFile.read())
        webFile.close()
        localFile.close()
        return localFile.name

    def job_1(self):
        self.hasConnection = self.internet_on()
        if not self.hasConnection:
            self.setText("Connection can not been established.")
            self.button1.show()
            
    def job_2(self):
        destfile= ""
        if self.hasConnection:
            for srcfile in self.fileToDownload:
                try:
                    destfile = self.download_file(self.host +srcfile)
                except Exception ,ex:
                    LicHelpers.writeLogEntry(ex.message, self.__class__.__name__)
                else:
                    self.setText("Downloaded %s" % os.path.basename(destfile))
        

class LicShortcutAssistant(QWidget):

    _padding = 5
    _space = 10
    _authorinfo = "Created by: Jeremy Czajkowski <jeremy.cz@wp.pl>"

    def __init__(self ,parent=None):
        QWidget.__init__(self,parent,Qt.SubWindow)
        fontHeight = QPainter(self).fontMetrics().height()
        ht = shortcuts.__len__() *fontHeight +shortcuts.__len__() * self._space +100
        
        self.setGeometry(1,1,300,ht)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFocusProxy(parent)
        self.setMouseTracking(True)     
        
        self.license = QImage(":/lic_license")

    def paintEvent(self, event):
        p = QPainter(self)
        ht = p.fontMetrics().height()
        p.fillRect(self.rect(), QColor(SUBWINDOW_BACKGROUND))
        p.setPen(QPen(QBrush(QColor(Qt.black) ,Qt.Dense6Pattern ), 4.0))
        p.drawRect(self.rect())
        p.setPen(Qt.black)
        for n in shortcuts:
            y = self._space*n+ht*n
            try:
                p.drawText(QPointF(self._padding ,y-self._padding), shortcuts[n][0])
                p.drawText(QPointF(self._padding +200,y-self._padding), shortcuts[n][1])
            except:
                pass
            else:
                p.drawLine(self._padding ,y ,self.width()-self._padding ,y)
            
        y +=ht*2
        x = self.width()/2 -self._padding
        textWidth = p.fontMetrics().width(self._authorinfo)
        
        p.drawText(QPointF(x -textWidth/2 ,y) ,self._authorinfo)
        p.drawImage(QPointF(x -64 ,y+ht) , self.license)

class LicPlacementAssistant(QWidget):    
    
    _buttonTip = {
                    QStyle.SP_DialogCancelButton : "Release this item and close window"
                    ,QStyle.SP_DialogApplyButton : "Put this item on scene"
                    }
    _noPLIText = "non a PLI"
    _noMoveText= "You're still on the same page" 
    _noBlankText= "Page or Step can not be blank"
    _lockedPageText = "Stuff is locked on this page"
    _processingText = "Processing..."
      
    def __init__(self ,parent=None):
        QWidget.__init__(self,parent,Qt.SubWindow)

        x = parent.width()/2 -100 if parent else 1
        self.setGeometry(x,1,200,100)
        self.setBackgroundRole(QPalette.Base)
        self._item = None
        self.destItem = None
        
        warningFont = QFont("Times", 9)
        serifFont = QFont("Times", 12, QFont.Bold)
        serifFont.setCapitalization(QFont.SmallCaps)
        
        self._page = QLabel()
        self._thumbnail = QGraphicsPixmapItem()
        self._step = QLabel()
        self._warning = QLabel()
        
        view = QGraphicsView(QGraphicsScene(0,0,64,64),self)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        view.scene().addItem(self._thumbnail)
        
        self._apply = ExtendedLabel()
        self._apply.setPixmap(QCommonStyle().standardPixmap (QStyle.SP_DialogApplyButton))
        self._apply.setStatusTip(self._buttonTip[QStyle.SP_DialogApplyButton])
        self.connect(self._apply, SIGNAL('clicked()'), self.moveItemToStep)
        
        self._cancel = ExtendedLabel()
        self._cancel.move(0,0)
        self._cancel.setPixmap(QCommonStyle().standardPixmap (QStyle.SP_DialogCancelButton))
        self._cancel.setStatusTip(self._buttonTip[QStyle.SP_DialogCancelButton])
        self.connect(self._cancel, SIGNAL('clicked()'), self.close)
        
        self._page.setFont(serifFont)
        self._step.setFont(serifFont)

        self._warning.setFont(warningFont)
        self._warning.setStyleSheet("QLabel { color : red; }")
        
        actions = QVBoxLayout()
        actions.addWidget(self._cancel)
        actions.addWidget(self._apply)
        
        content = QHBoxLayout()
        content.addWidget(self._page)
        content.addWidget(view)
        content.addWidget(self._step)
        
        grid = QGridLayout()
        grid.addLayout(actions, 1, 0, Qt.AlignTop)
        grid.addLayout(content, 1, 1, Qt.AlignLeft)
        grid.addWidget(self._warning, 2, 1, Qt.AlignHCenter)
        self.setLayout(grid)

    def moveItemToStep(self):
        self._warning.clear()
        if self._item is not None:
            self.scene = self._item.scene()
            srcPage = self._item.getStep().parentItem()      
            try:
                self.destItem = self.scene.selectedItems()[0]
            except IndexError:
                self.destItem = None
            
            # Find Step assigned to currently selected item
            if self.destItem and self.destItem.__class__.__name__ != "Page":
                while self.destItem and not isinstance(self.destItem,Step):
                    try:
                        self.destItem = self.destItem.parent()
                    except:
                        break
            
            # Convert Page to first step on the list
            if self.destItem and self.destItem.__class__.__name__ == "Page":
                if srcPage.number == self.destItem.number:
                    self._warning.setText(self._noMoveText)
                else:
                    self.destItem = self.destItem.steps[0]
                    
            # Find the selected item's parent page, then flip to that page
            # Move Part into Step
            canMove = True
            if isinstance(self.destItem,Step):
                destPage = self.destItem.parentItem()
                
                if srcPage.number == destPage.number:
                    canMove = False
                    self._warning.setText(self._noMoveText)
                     
                if destPage.isLocked():
                    canMove = False
                    self._warning.setText(self._lockedPageText)
                    
                if destPage.isEmpty():
                    canMove = False
                    self._warning.setText(self._noBlankText)
                 
                if canMove:        
                    self._worker = LicWorker([self.job_1S ,self.job_2 ,self.job_3])
                    self._worker.start()

        
    def paintEvent(self, event):
    # prepare canvas
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(SUBWINDOW_BACKGROUND))
    # draw border
        p_old = p.pen()
        p_new = QPen(QBrush(QColor(Qt.black) ,Qt.Dense6Pattern ), 2.0)
        p.setPen(p_new)
        p.drawRect( QRectF(1, 1, self.width() -2, self.height() -2) )
        p.setPen(p_old)
            
    def closeEvent(self, event):
        self.window().setCursor(Qt.ArrowCursor)
        self.destItem = None
        return QWidget.closeEvent(self, event)
                    
    def job_1S(self):
        if self.destItem:
            self._warning.setText(self._processingText)
            self.window().setCursor(Qt.WaitCursor)
                            
            self.scene.setFocus(Qt.MouseFocusReason)
            self.scene.setFocusItem(self.destItem ,Qt.MouseFocusReason)
            self.destItem.setSelected(True)

    def job_2(self):
        if self.destItem:
            self.scene.undoStack.push(MovePartsToStepCommand([self._item], self.destItem))
        
    def job_3(self):
        self.close()      
                              
    def setItemtoMove(self ,part=None):
        self.destItem = None
        self._item = part
        step = part
        while step and not isinstance(step, Step):
            step = step.parent()
        self._step.setText( step.data(Qt.DisplayRole) )
        self._page.setText( step.parentItem().data(Qt.DisplayRole) )
        self._warning.clear()
        if part:
            pItem = None
            if step and step.hasPLI():
                for pliItem in step.pli.pliItems:
                    if pliItem.abstractPart.filename == part.abstractPart.filename:
                        pItem = pliItem
                        break
 
            sRect = self._thumbnail.scene().sceneRect()
            if isinstance(pItem, (Part,PLIItem)):
                a = pItem.abstractPart
                filename = os.path.join( config.grayscalePath() , os.path.splitext(a.filename)[0] +".png" ).lower() 
                if not os.path.exists(filename):
                    pRect = pItem.sceneBoundingRect().toRect()
                    wt = Page.PageSize.width()
                    ht = Page.PageSize.height()
                    mx = int(PLI.margin.x()/2)
                    bufferManager = LicGLHelpers.FrameBufferManager(wt, ht)
                    try:
                        bufferManager.bindMSFB()
                        LicGLHelpers.initFreshContext(True)                                   
                      
                        step.parentItem().drawGLItemsOffscreen(QRectF(0, 0, wt, ht), 1.0)
                        bufferManager.blitMSFB()
                        temp_data = bufferManager.readFB()                     
                        temp_cord = ( pRect.left() -mx ,pRect.top() -mx ,a.width +pRect.left() +mx ,a.height +pRect.top() +mx )
                        temp_name = tempfile.TemporaryFile() .name + ".png" .lower()
                        temp = Image.fromstring("RGBA", (wt, ht), temp_data)
                        temp = temp.transpose(Image.FLIP_TOP_BOTTOM)
                        temp = temp.crop(temp_cord)
                        temp.save(temp_name)
                    finally:
                        image = QImage(temp_name,"LA")
                        #convertToGrayscale
                        for i in range(0,image.width()):
                            for j in range(0,image.height()):
                                pix = image.pixel(i, j)
                                if pix > 0:
                                    color = qGray(pix)
                                    image.setPixel(i, j, qRgb(color, color, color))
                        #saveResult
                        image.save(filename,"PNG")
                        #cleanUp
                        bufferManager.cleanup()
                        os.remove(temp_name)
                else:        
                    image = QImage(filename,"LA")
                image = image.scaledToHeight(sRect.height(), Qt.SmoothTransformation)
            else:
                image = QImage(sRect.width(), sRect.height(), QImage.Format_Mono)
                painter = QPainter(image)
                painter.fillRect(sRect, Qt.white)
                painter.setFont(QFont("Helvetica [Cronyx]", 10, QFont.Bold))
                painter.drawLine(1,1,sRect.width()-1,sRect.height()-1)    
                painter.drawLine(sRect.width()-1,1,1,sRect.height()-1)
                painter.drawText(sRect , Qt.TextSingleLine | Qt.AlignVCenter , self._noPLIText)  
                painter.end()
                 
            self._thumbnail.setPixmap(QPixmap.fromImage(image))

        if not self.isVisible():
            self.show()
                    
class LicCleanupAssistant(QDialog):        
        
    _steps = ["Initialing","Remove blank pages","Remove empty steps","Merge pages with one step and one part","Calculate area of the parts list"]
    _iconsize = 16
    _defaulttitle = "Clean-up"
    
    def __init__(self ,pages ,view):
        QDialog.__init__(self, view, Qt.Dialog | Qt.WindowTitleHint | Qt.WindowModal)
        self.setWindowTitle(self._defaulttitle)
        self.setModal(True)
        self.setFixedHeight(32 +self._iconsize*self._steps.__len__())
        
        n = 0
        self._icons = []
        self._pages = pages
        self._pixmap = QCommonStyle().standardIcon (QStyle.SP_DialogApplyButton).pixmap(self._iconsize ,self._iconsize)
        grid = QGridLayout()
        for s in (self._steps):
            icon_box = QLabel()
            self._icons.append(icon_box)
            grid.addWidget(QLabel(s), n, 0, Qt.AlignLeft)
            grid.addWidget(icon_box, n, 1, Qt.AlignRight)
            n += 1
        self.setLayout(grid)
        
        self._icons[0].setPixmap(self._pixmap)
        self._icons[0].setMask(self._pixmap.mask())
        
        self.worker = LicWorker([self.job_1S,self.job_1,self.job2S,self.job_2,self.job_3S,self.job_4,self.job_postProcessed])
        
    def showEvent(self, event):
        thread.start_new_thread( self.worker.start , () )
        return QDialog.showEvent(self, event)
    
    def closeEvent(self, event):
        self.worker.terminate()
        return QDialog.closeEvent(self, event)
    
    def job_postProcessed(self):
        # clean-up post processed actions
        self.setWindowTitle(self._defaulttitle)
        self._pages = []
            
    def job_1(self):       
        """ Remove blank pages """    
        self.setWindowTitle(self._defaulttitle)
            
        if [] != self._pages:
            stack = self._pages[0].scene().undoStack
            stack.beginMacro("Remove blank pages")
            for p in self._pages:
                if p.isEmpty():
                    self._pages.remove(p)
                    stack.push(AddRemovePageCommand(p.scene() ,p ,False))
            stack.endMacro()
        
    def job_2(self):
        """ Merge pages with one step and one part """
        """ Remove empty steps """
        for p in reversed(self._pages):
            sp = None
            ly = None
            for ch in p.children: 
                if isinstance(ch, Step):  
                    if sp is None:
                        sp = ch.parentItem()
                        ly = sp.getCurrentLayout()
                    nparts = ch.csi.parts.__len__()
                    if nparts == 0:
                        ch.setSelected(False)
                        sp.removeStep(ch)
                        sp.revertToLayout(ly)
                    if nparts == 1:
                        self.setWindowTitle("{0} {1}".format(self._defaulttitle , p.data(Qt.DisplayRole)))
                        if ch.getPrevStep():
                            ch.mergeWithStepSignal(ch.getPrevStep())

    def job_1S(self):
        self._icons[1].setPixmap(self._pixmap)
        self._icons[1].setMask(self._pixmap.mask())  
 
    def job2S(self):
        self._icons[2].setPixmap(self._pixmap)
        self._icons[2].setMask(self._pixmap.mask())
                  
    def job_3S(self):    
        # work is done in step 2 so set visual signal here
        self._icons[3].setPixmap(self._pixmap)
        self._icons[3].setMask(self._pixmap.mask())  
        
    def job_4(self):
        self._icons[4].setPixmap(self._pixmap)    
        for p in self._pages:
            for ch in p.children: 
                if isinstance(ch, Step):  
                    self.setWindowTitle("{0} {1}".format(self._defaulttitle , ch.data(Qt.DisplayRole)))
                    if ch.hasPLI():
                        topLeft = PLI.margin
                        displacement = 0
                        for item in ch.pli.pliItems:
                            item.initLayout()
                            item.resetRect()   
                            item.setPos(topLeft)
                            item.moveBy(displacement+topLeft.x(),0)       
                            displacement += item.abstractPart.width
                        ch.pli.resetRect()
                            