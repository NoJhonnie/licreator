"""
    Lic - Instruction Book Creation software
    Copyright (C) 2010 Remi Gagne

    This file (Importers.BuilderImporter.py) is part of Lic.

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

import logging
import os.path

import LDrawImporter


LDrawPath = None  # This will be set by the object calling this importer

def importModel(filename, instructions):
    BuilderImporter(filename, instructions)

def importPart(filename, instructions, abstractPart):
    BuilderImporter(filename, instructions, abstractPart)

def importColorFile(instructions):
    BuilderImporter.loadLDConfig(instructions)

class BuilderImporter(LDrawImporter.LDrawImporter):
    
    def __init__(self, filename, instructions, parent = None):
        LDrawImporter.LDrawImporter.__init__(self, filename, instructions, parent)


    def writeLogEntry(self, message):
        logging.warning('------------------------------------------------------\n BuilderImporter => %s' % message)        

Comment = '0'
PartCommand = '1'
LineCommand = '2'
TriangleCommand = '3'
QuadCommand = '4'
ConditionalLineCommand = '5'

StepCommand = 'STEP'
FileCommand = 'FILE'
BFCCommand = 'BFC'
lineTerm = '\n'

def LDToGLMatrix(matrix):
    return LDrawImporter.LDToGLMatrix(matrix)

def GLToLDMatrix(matrix):
    return LDrawImporter.GLToLDMatrix(matrix)

def createPartLine(color, matrix, filename):
    return LDrawImporter.createPartLine(color, matrix, filename)

def isPartLine(line):
    return LDrawImporter.isPartLine(line)

def lineToPart(line):
    return LDrawImporter.lineToPart(line)

def createSubmodelLines(filename):
    return LDrawImporter.createSubmodelLines(filename)

def isBFCLine(line):
    return LDrawImporter.isBFCLine(line)

def isPrimitiveLine(line):
    return LDrawImporter.isPrimitiveLine(line)

def lineToPrimitive(line):
    return LDrawImporter.lineToPrimitive(line)

def lineTypeToGLShape(command):
    return LDrawImporter.lineTypeToGLShape(command)

def isConditionalLine(line):
    return LDrawImporter.isConditionalLine(line)

def lineToConditionalLine(line):
    return LDrawImporter.lineToConditionalLine(line)

def isFileLine(line):
    return LDrawImporter.isFileLine(line)

def isStepLine(line):
    return LDrawImporter.isStepLine(line)

def createStepLine():
    return LDrawImporter.createStepLine()

class BuilderFile(object):

    def __init__(self, filename):
        """
        Create a new BuilderFile instance based on the passed in LDraw file string.
        
        Parameters:
            filename: l3b filename (string) to load into this BuilderFile.  Do not include any path
        """
        
        self.filename = filename      # filename, like 3057.dat
        self.name = ""                # coloquial name, like 2 x 2 brick
        self.isPrimitive = False      # Anything in the 'P' or 'Parts\S' directories
        
        self.lineList = []
        self.readFileToLineList()  # Read the file from disk, and copy it to the line list

    @staticmethod
    def getPartFilePath(filename):

        # Change hardcoded path separators in some LDraw lines to platform specific separator
        if (filename[:2] == 's\\'):
            filename = os.path.join('s', filename[2:])
        elif (filename[:3] == '48\\'):
            filename = os.path.join('48', filename[3:])

        # Build list of possible lookup paths
        pathList = [filename, 
                    os.path.join(LDrawPath, 'MODELS', filename),
                    os.path.join(LDrawPath, 'UNOFFICIAL', 'PARTS', filename),
                    os.path.join(LDrawPath, 'UNOFFICIAL', 'P', filename),
                    os.path.join(LDrawPath, 'PARTS', filename),
                    os.path.join(LDrawPath, 'P', filename)]

        for p in pathList:
            if os.path.isfile(p):
                return p
        return None
    
    def readFileToLineList(self):

        fullPath = BuilderFile.getPartFilePath(self.filename)
        f = file(fullPath)

        # Check if this part is an LDraw primitive
        sep = os.path.sep
        if (sep + 's' + sep in fullPath) or (sep + 'P' + sep in fullPath):
            self.isPrimitive = True

        # Copy the file into an internal array, for easier access
        i = 1
        for l in f:
            self.lineList.append([i] + l.split())
            i += 1
        f.close()
        
        self.name = ' '.join(self.lineList[0][2:])

    def getSubmodels(self, filename):
        
        # Loop through the file array searching for sub model FILE declarations
        submodels = [(filename, 0)]
        for i, l in enumerate(self.lineList[1:]):
            if isFileLine(l):
                submodels.append((' '.join(l[3:]), i+1))  # + 1 because we start at line 1 not 0
        
        # Fixup submodel list by calculating the ending line number from the file
        for i in range(0, len(submodels)-1):
            submodels[i] = (submodels[i][0], [submodels[i][1], submodels[i+1][1]])
        
        # Last submodel is special case: its ending line is end of file array
        submodels[-1] = (submodels[-1][0], [submodels[-1][1], len(self.lineList)])
        
        return dict(submodels)  # {filename: (start index, stop index)}
