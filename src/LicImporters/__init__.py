"""
    Lic - Instruction Book Creation software
    Copyright (C) 2010 Remi Gagne

    This file (Importers.__init__.py) is part of Lic.

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

# Dictionary of all registered importers & the files they handle
# Each entry is the name of the importer module and a tuple of the file types it supports.
# First item in file type list should be a string representation of the importer itself.

Importers = {
"LDrawImporter": ("LDraw", "dat", "ldr", "mpd"),
"BuilderImporter": ("3D Builder", "l3b"),
#"LDDImporter":   ("LDD - NYI", "lxf"),
}

def getImporter(fileType):
    for importer, fileTypeList in Importers.items():
        fileTypeList = [f.lower() for f in fileTypeList]
        if fileType.lower() in fileTypeList:
            return importer
    return None

def getFileTypesString():
    return __fileTypes

def getFileTypesList():
    fileList = []
    for fileTypes in Importers.values():
        fileList += fileTypes[1:]
    return ['.' + f for f in fileList]

def __buildFileTypes():
    # (("LDraw", "mpd", "ldr", "dat"), ("LDD", "lxf"))
    # to
    # "LDD (*.lxf);;LDraw (*.mpd, *.ldr, *.dat)"

    formatString = ""
    for fileTypes in reversed(Importers.values()):
        formats = ['*.%s' % f.lower() for f in fileTypes[1:]]
        formatString += "%s (%s);;" % (fileTypes[0], " ".join(formats))
    return formatString[:-2]  # -2 to trim off trailing ;;

__fileTypes = __buildFileTypes()

