"""
    LIC - Instruction Book Creation software
    Copyright (C) 2010 Remi Gagne
    Copyright (C) 2015 Jeremy Czajkowski

    This file (LicInstructions.py) is part of LIC.

    LIC is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the Creative Commons License
    along with this program.  If not, see http://creativecommons.org/licenses/by-sa/3.0/
"""

import sys

from PyQt4.QtCore import *

from LicCustomPages import *
from LicHelpers import LicColor, LicColorDict
from LicImporters import LDrawImporter
from LicModel import *


class Instructions(QObject):
    itemClassName = "Instructions"

    def __init__(self, parent, scene, glWidget):
        QObject.__init__(self, parent)

        self.scene = scene
        self.mainModel = None
        # Dict of all valid LicColor instances for this particular model, indexed by LDraw color code
        self.colorDict = LicColorDict()  
        # x = AbstractPart("3005.dat"); partDictionary[x.filename] == x
        self.partDictionary = {}      

        self.glContext = glWidget
        self.glContext.makeCurrent()
        
        self.setOrginalContent()

    def __getTemplate(self):
        return self.mainModel.template

    def __setTemplate(self, template):
        if (self.mainModel.template is None):
            self.mainModel.incrementRows(1)
        self.mainModel.template = template
        
    def __getModelcontent(self):
        return self.__modelcontent

    template = property(__getTemplate, __setTemplate)
    modelcontent = property(__getModelcontent)

    def clear(self):

        # Remove everything from the graphics scene
        if self.mainModel:
            self.mainModel.deleteAllPages(self.scene)

        self.mainModel = None
        self.partDictionary = {}
        Page.PageSize = Page.defaultPageSize
        Page.Resolution = Page.defaultResolution
        CSI.defaultScale = PLI.defaultScale = SubmodelPreview.defaultScale = 1.0
        CSI.defaultRotation = [20.0, 45.0, 0.0]
        PLI.defaultRotation = [20.0, -45.0, 0.0]
        CSI.highlightNewParts = False
        SubmodelPreview.defaultRotation = [20.0, 45.0, 0.0]
        LicGLHelpers.resetLightParameters()
        self.glContext.makeCurrent()

    def importModel(self, filename):

        # Create and fill with data main model instance
        self.mainModel = Mainmodel(self, self, filename)
        self.mainModel.appendBlankPage()
        self.mainModel.importModel()

        # Initializing Pages and Steps
        self.mainModel.syncPageNumbers()
        self.mainModel.addInitialPagesAndSteps()
                    
        submodelCount = self.mainModel.submodelCount()
        pageList = self.mainModel.getPageList()
        pageList.sort(key = lambda x: x._number)
        totalCount = len(self.partDictionary) + len(self.mainModel.getCSIList()) + submodelCount  # Rough count only

        yield totalCount  # Special first value is maximum number of progression steps in load process
        
        yield "Initializing GL display lists"
        for label in self.initGLDisplayLists():  # generate all part GL display lists on the general glWidget
            yield label

        for label in self.initPartDimensions():  # Calculate width and height of each abstractPart in the part dictionary
            yield label

        yield "Initializing CSI Dimensions"
        for label in self.initCSIDimensions():   # Calculate width and height of each CSI in this instruction book
            yield label

        yield "Initializing Submodel Images"
        self.mainModel.addSubmodelImages()
                
        yield "Laying out Pages"
        for page in pageList:
            page.initLayout()

        yield "Reconfiguring Page Layouts"
        self.mainModel.mergeInitialPages()
        self.mainModel.reOrderSubmodelPages()
        self.mainModel.syncPageNumbers()

        for page in pageList:
            for label in page.adjustSubmodelImages():
                yield label
            page.resetPageNumberPosition()

    def getQuantitativeSizeMeasure(self):  # Get some arbitrary measure of how big / complex this file is (useful for progress bars)
        count = len(self.partDictionary)
        count += self.mainModel.pageCount()
        count += len(self.mainModel.getCSIList()) * 2
        return count

    def getModelName(self):
        return self.mainModel.filename

    def getPageList(self):
        return self.mainModel.getFullPageList()

    def getProxy(self):
        return InstructionsProxy(self)
    
    def spawnNewPage(self, submodel, number, row):
        return Page(submodel, self, number, row)
    
    def spawnNewTitlePage(self):
        return TitlePage(self)

    def initGLDisplayLists(self):

        self.glContext.makeCurrent()

        # First initialize all abstractPart display lists
        for part in self.partDictionary.values():
            if part.glDispID == LicGLHelpers.UNINIT_GL_DISPID:
                yield "Initializing " + part.name
                part.createGLDisplayList()

        # Initialize the main model display list
        yield "Initializing Main Model GL display lists"
        self.mainModel.createGLDisplayList(True)
        self.mainModel.initSubmodelImageGLDisplayList()

        # Initialize all CSI display lists
        i = 0
        yield "Initializing CSI GL display lists"
        csiList = self.mainModel.getCSIList()
        for csi in csiList:
            yield "Initializing CSI " + str(i)
            csi.createGLDisplayList()
            i += 1

    def getPartDimensionListAndCount(self, reset = False):
        if reset:
            partList = [part for part in self.partDictionary.values() if (not part.isPrimitive)]
        else:
            partList = [part for part in self.partDictionary.values() if (not part.isPrimitive) and (part.width == part.height == -1)]
        partList.append(self.mainModel)

        partDivCount = 25
        partStepCount = int(len(partList) / partDivCount)
        return (partList, partStepCount, partDivCount)
    
    def initPartDimensions(self, reset = False):
        """
        Calculates each uninitialized part's display width and height.
        Creates GL buffer to render a temp copy of each part, then uses those raw pixels to determine size.
        """

        partList, partStepCount, partDivCount = self.getPartDimensionListAndCount(reset)
        currentPartCount = currentCount = 0

        if not partList:
            return    # If there's no parts to initialize, we're done here

        partList2 = []
        # Frame buffer sizes to try - could make configurable by user, if they've got lots of big submodels
        sizes = [128, 256, 512, 1024, 2048] 

        for size in sizes:

            # Create a new buffer tied to the existing GLWidget, to get access to its display lists
            pBuffer = QGLPixelBuffer(size, size, LicGLHelpers.getGLFormat(), self.glContext)
            pBuffer.makeCurrent()

            # Render each image and calculate their sizes
            for abstractPart in partList:

                if abstractPart.initSize(size, pBuffer):  # Draw image and calculate its size:                    
                    currentPartCount += 1
                    if not currentPartCount % partDivCount:
                        currentPartCount = 0
                        currentCount +=1
                        yield "Initializing Part Dimensions (%d/%d)" % (currentCount, partStepCount)
                else:
                    partList2.append(abstractPart)

            if len(partList2) < 1:
                break  # All images initialized successfully
            else:
                partList = partList2  # Some images rendered out of frame - loop and try bigger frame
                partList2 = []

    def setAllCSIDirty(self):
        csiList = self.mainModel.getCSIList()
        for csi in csiList:
            csi.isDirty = True
    
    def setOrginalContent(self ,name ="", content=[]):
        self.__modelcontent = {}
        self.__modelcontent["name"] = name
        self.__modelcontent["content"] = content
        
    def updateMainModel(self, updatePartList = True):
        if self.mainModel.hasTitlePage():
            self.mainModel.titlePage.submodelItem.resetPixmap()
        if updatePartList:
            self.mainModel.updatePartList()

    def initCSIDimensions(self, repositionCSI = False):

        self.glContext.makeCurrent()

        csiList = self.mainModel.getCSIList()
        if not csiList:
            return  # All CSIs initialized - nothing to do here

        csiList2 = []
        # Frame buffer sizes to try - could make configurable by user, 
        # if they've got lots of big submodels or steps
        sizes = [512, 1024, 2048] 

        for size in sizes:

            # Create a new buffer tied to the existing GLWidget, to get access to its display lists
            pBuffer = QGLPixelBuffer(size, size, LicGLHelpers.getGLFormat(), self.glContext)

            # Render each CSI and calculate its size
            for csi in csiList:
                pBuffer.makeCurrent()
                oldRect = csi.rect()
                result = csi.initSize(size, pBuffer)
                if result:
                    yield result
                    if repositionCSI:
                        newRect = csi.rect()
                        dx = oldRect.width() - newRect.width()
                        dy = oldRect.height() - newRect.height()
                        csi.moveBy(dx / 2.0, dy / 2.0)
                else:
                    csiList2.append(csi)

            if len(csiList2) < 1:
                break  # All images initialized successfully
            else:
                # Some images rendered out of frame - loop and try bigger frame
                csiList = csiList2  
                csiList2 = []

        self.glContext.makeCurrent()

    #TODO: Fix POV Export so it works with the last year's worth of updates
    
    def exportToPOV(self):
        #global submodelDictionary
        #for model in submodelDictionary.values():
        #    if model.used:
        #        model.createPng()
        self.mainModel.createPng()
        self.mainModel.exportImagesToPov()
        
    def exportImages(self, scaleFactor = 1.0):
        
        pagesToDisplay = self.scene.pagesToDisplay
        self.scene.clearSelection()
        self.scene.showOnePage()
        self.scene.setBackgroundBrush(QBrush(Qt.NoBrush))

        # Build the list of pages that need to be exported
        pageList = self.mainModel.getFullPageList()
        pageList.sort(key = lambda x: x._number)
        yield len(pageList) # Special first value is number of steps in export process

        currentPageNumber = self.scene.currentPage._number  # Store this so we can restore selection later
        bufferManager = None

        if scaleFactor > 1.0:  # Make part lines a bit thicker for higher res output
            lineWidth = LicGLHelpers.getLightParameters()[2]
            GL.glLineWidth(lineWidth * scaleFactor)

        try:
            w, h = int(Page.PageSize.width() * scaleFactor), int(Page.PageSize.height() * scaleFactor)
            bufferManager = LicGLHelpers.FrameBufferManager(w, h)

            # Render & save each page as an image
            for page in pageList:

                page.lockIcon.hide()
                exportedFilename = page.getGLImageFilename()

                bufferManager.bindMSFB()
                LicGLHelpers.initFreshContext(True)

                page.drawGLItemsOffscreen(QRectF(0, 0, w, h), scaleFactor)
                bufferManager.blitMSFB()
                data = bufferManager.readFB()

                # Create an image from raw pixels and save to disk - would be nice to create QImage directly here
                image = Image.fromstring("RGBA", (w, h), data)
                image = image.transpose(Image.FLIP_TOP_BOTTOM)
                image.save(exportedFilename)

                # Create new blank image
                image = QImage(w, h, QImage.Format_ARGB32)
                painter = QPainter()
                painter.begin(image)

                self.scene.selectPage(page._number)
                self.scene.renderMode = 'background'
                self.scene.render(painter, QRectF(0, 0, w, h))

                glImage = QImage(exportedFilename)
                painter.drawImage(QPoint(0, 0), glImage)

                self.scene.selectPage(page._number)
                self.scene.renderMode = 'foreground'
                self.scene.render(painter, QRectF(0, 0, w, h))
    
                painter.end()
                newName = page.getExportFilename()
                image.save(newName)

                yield newName
                page.lockIcon.show()    

        finally:
            if bufferManager is not None:
                bufferManager.cleanup()
            self.scene.renderMode = 'full'
            self.scene.setPagesToDisplay(pagesToDisplay)
            self.scene.selectPage(currentPageNumber)
            self.scene.setBackgroundBrush(Qt.gray)

    def exportToPDF(self):

        # Create an image for each page
        filename = os.path.join(config.pdfCachePath(), os.path.basename(self.mainModel.filename)[:-3] + "pdf")
        yield filename

        if sys.platform.startswith('darwin'):  # Temp workaround to PDF crash on OSX
            exporter = self.exportImages(2.0)
        else:
            exporter = self.exportImages(3.0)

        yield 2 * exporter.next()

        # Create Document settings
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFileName(filename)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setFullPage(True)
        printer.setResolution(Page.Resolution)
        printer.setPaperSize(QSizeF(Page.PageSize), QPrinter.DevicePixel)

        # Rendering
        pageFilenameList = []
        for pageFilename in exporter:
            fn = os.path.splitext(os.path.basename(pageFilename))[0].replace('_', ' ')
            yield "Rendering " + fn
            pageFilenameList.append(pageFilename)

        # Adding
        painter = QPainter()
        painter.begin(printer)
        for pageFilename in pageFilenameList:
            fn = os.path.splitext(os.path.basename(pageFilename))[0].replace('_', ' ')
            yield "Adding " + fn + " to PDF"
            image = QImage(pageFilename)
            painter.drawImage(QRectF(0.0, 0.0, Page.PageSize.width(), Page.PageSize.height()), image)
            if pageFilename != pageFilenameList[-1]:
                printer.newPage()
        painter.end()

    def updatePageNumbers(self, newNumber, increment = 1):
        if self.mainModel:
            self.mainModel.updatePageNumbers(newNumber, increment)

    def loadLDrawColors(self):
        self.colorDict = LicColorDict()
        LDrawImporter.importColorFile(self.getProxy())

class InstructionsProxy(object):

    def __init__(self, instructions):
        self.__instructions = instructions

    def createPart(self, fn, colorCode, matrix, invert = False, rgba = ()):

        partDictionary = self.__instructions.partDictionary
    # assigned custom color data <tuple>(r,g,b,a) ,otherwise stay <integer>colorCode AS IS
        if 16 == colorCode and rgba:
            color = LicColor(rgba[0],rgba[1],rgba[2],rgba[3] ,"Custom")
        else:
            color = self.__instructions.colorDict[colorCode]
        
        part = Part(fn, color, matrix, invert)

        if fn in partDictionary:
            part.abstractPart = partDictionary[fn]
        elif fn.upper() in partDictionary:
            part.abstractPart = partDictionary[fn.upper()]
        elif fn.lower() in partDictionary:
            part.abstractPart = partDictionary[fn.lower()]
        return part

    def createAbstractPart(self, fn):
        partDictionary = self.__instructions.partDictionary
        partDictionary[fn] = AbstractPart(fn)
        return partDictionary[fn]

    def createAbstractSubmodel(self, fn, parent = None):

        partDictionary = self.__instructions.partDictionary
        if parent is None:
            parent = self.__instructions.mainModel

        part = partDictionary[fn] = Submodel(parent, self.__instructions, fn)
        part.appendBlankPage()
        return part

    def addColor(self, colorCode, r = 1.0, g = 1.0, b = 1.0, a = 1.0, name = 'Black'):
        cd = self.__instructions.colorDict
        cd[colorCode] = None if r is None else LicColor(r, g, b, a, name, colorCode)

    def addPart(self, part, parent = None):
        if parent is None:
            parent = self.__instructions.mainModel

        parent.parts.append(part)

        if parent.isSubmodel:
            parent.pages[-1].steps[-1].addPart(part)

            if part.abstractPart.isSubmodel and not part.abstractPart.used:
                p = part.abstractPart
                p._parent = parent
                p._row = parent.pages[-1]._row
                p.used = True
                parent.pages[-1]._row += 1
                parent.submodels.append(p)

    def addPrimitive(self, shape, colorCode, points, parent = None):
        if parent is None:
            parent = self.__instructions.mainModel
        color = self.__instructions.colorDict[colorCode]
        primitive = Primitive(color, points, shape, parent.winding)
        parent.primitives.append(primitive)

    def addBlankPage(self, parent):
        if parent is None:
            parent = self.__instructions.mainModel
        if parent.isSubmodel:
            parent.appendBlankPage()
