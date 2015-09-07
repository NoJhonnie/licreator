"""
    LIC - Instruction Book Creation software
    Copyright (C) 2010 Remi Gagne
    Copyright (C) 2015 Jeremy Czajkowski

    This file (LicL3PWrapper.py) is part of LIC.

    LIC is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the Creative Commons License
    along with this program.  If not, see http://creativecommons.org/licenses/by-sa/3.0/
"""

import os  # For setting LDraw environment and process creation
import sys  # For detect platform and operating system     

import LicHelpers  # For writeLogEntry ,writeLogAccess
import config  # For path to l3p


def listToCSVStr(l):
    s = ''
    for i in l:
        s += str(i) + ','
    return s[:-1]
    
def boolToCommand(command, bool):
    if bool:
        return command
    return ''

def isExists():
    app = os.path.join(config.L3PPath ,'l3p.exe').replace("\\", "/")
    return os.path.exists(app)

def __getDefaultCommand():
    return dict({
        'camera position' : [20, -45, 0],
        'background' : [1.0, 1.0, 1.0],
        
        'seam width' : 0.5,
        'quality' : 3,
        'color' : 0,
        
        'overwrite' : True,
        'bumps' : True,
        'LGEO' : False,
    })

l3pCommands = {
    'inFile' : None,
    'outFile' : None,
    
    'camera position' : ['-cg', listToCSVStr],  # [20, -45, 0] = (lat, long, r)
    'background' : ['-b', listToCSVStr],   # [r, g, b] 0 <= r <= 1
    'light' : ['-lg', listToCSVStr],  # [45, -45, 0] = (lat, long, r)
    
    'seam width' : ['-sw', str],  # int
    'quality' : ['-q', str],  # int
    'color' : ['-c', str],  # LDraw Color code
    
    'overwrite' : ['', lambda b: boolToCommand('-o', b)], # Boolean
    'bumps' : ['', lambda b: boolToCommand('-bu', b)],    # Boolean
    'LGEO' : ['', lambda b: boolToCommand('-lgeo', b)],   # Boolean
}

os.environ['LDRAWDIR'] = config.LDrawPath
    
# d: {'camera position' : [20,-45,0], 'inputFile' : 'hello.dat'}
def __runCommand(d):
    
    l3pApp = os.path.join(config.L3PPath ,'l3p.exe').replace("\\", "/")
    if not os.path.isfile(l3pApp):
        error_message = "Error: Could not find L3P.exe in %s - aborting image generation" % os.path.dirname(l3pApp)
        LicHelpers.writeLogEntry(error_message)
        print error_message
        return
    
    args = [l3pApp]
    mode = os.P_WAIT
    for key, value in d.items():
        command = l3pCommands[key]
        if command:
            args.append(command[0] + command[1](value))
        else:
            if key == 'inFile':
                args.insert(1, value)  # Ensure input file is first command (after l3p.exe itself)
            else:
                args.append(value)
                
    if config.writeL3PActivity:                
        LicHelpers.writeLogAccess(" ".join(args))
    if sys.platform == 'win32':
        mode = os.P_DETACH
        
    os.spawnv(mode, l3pApp, args)

def createPovFromDat(datFile, color = None):
    
    rawFilename = os.path.splitext(os.path.basename(datFile))[0]
    povFile = os.path.join(config.povCachePath(), rawFilename)
    
    if color is None:
        povFile = "%s.pov" % povFile
    else:
        povFile = "{0}_{1}.pov" .format (povFile, color.code())
    
    if not os.path.isfile(povFile):
        l3pCommand = __getDefaultCommand()
        l3pCommand['inFile'] = "\"%s\"" % datFile.replace("\\", "/")
        l3pCommand['outFile'] = "\"%s\"" % povFile.replace("\\", "/")
        l3pCommand['color'] = 83
        if color:
            lDrawCode = color.code()
    # LDraw Internal Common Material Colours cause error, so we need change them to different color 
            if color.code() in [16,24]:
    # LEGOID 149 - Metallic Black
                lDrawCode = 83
            l3pCommand['color'] = lDrawCode
        __runCommand(l3pCommand)
        
    return povFile

        
