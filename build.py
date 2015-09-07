"""
    LIC - Instruction Book Creation software
    Copyright (C) 2010 Remi Gagne
    Copyright (C) 2015 Jeremy Czajkowski

    This file (build.py) is part of LIC.

    LIC is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the Creative Commons License
    along with this program.  If not, see http://creativecommons.org/licenses/by-sa/3.0/
"""

# A fundamental difference in packaging on win32 vs. osx: this win32 script will
# export the code to build from SVN.  osx script will only build the code in
# the currently checked out project.  This is because pysvn doesn't yet work
# correctly on osx.  Boo.
  
import errno
import os
import shutil
import subprocess
import sys
import zipfile

def Win32PythonPath():
    python_home = os.environ.get("PYTHONHOME","C:\Python27")
    if not python_home:
        print "Environment variable %PYTHONHOME% not defined or not accessible"
    return python_home

def perr(s):
    print s

def zipDir(zip_file, zip_dir, root_len):
    z = zipfile.ZipFile(zip_file, 'w')
    for base, unused, files in os.walk(zip_dir):
        for f in files:
            fn = os.path.join(base, f)
            z.write(fn, fn[root_len:])
    z.close()

def createOSXDist():

    import shutil
    from src.Lic import __version__ as lic_version
    from src.Lic import _debug as lic_debug

    if lic_debug and raw_input('Trying to build from DEBUG!!  Proceed? y/n: ').lower() != 'y':
        return
    
    if not sys.platform.startswith('darwin'):
        return perr("Must use OSX to create OSX distribution")
  
    root = "/Users/remig/Code/pywork"
    pyinstaller_path = os.path.join(root, 'pyinstaller')
    src_root = os.path.join(root, 'lic', 'src', 'Lic.py')
    app_root = os.path.join(root, 'LicApp')
    lic_root = os.path.join(app_root, 'Lic.app')
    mac_root = os.path.join(app_root, 'MacLic.app')
    spec_file = os.path.join(app_root, 'Lic.spec')

    if not os.path.isdir(pyinstaller_path):
        return perr("Could not find pyinstaller in %s" % pyinstaller_path)

    if os.path.isdir(app_root):
        return perr("Delete %s before proceeding" % app_root)

    print "Creating OSX Distribution"
    subprocess.call(['%s/Makespec.py' % pyinstaller_path, '--onefile', '--out=%s' % app_root, src_root])

    if not os.path.isfile(spec_file):
        return perr("Failed to create Spec file - something went horribly awry.  Good luck!")

    f = open(spec_file, 'a')
    f.write("\n")
    f.write("import sys\n")
    f.write("if sys.platform.startswith('darwin'):\n")
    f.write("    app = BUNDLE(exe, appname='Lic', version='%s')\n" % lic_version)
    f.write("\n")
    f.close()

    subprocess.call(['%s/Build.py' % pyinstaller_path, spec_file])

    resources = os.path.join(mac_root, 'Contents', 'Resources')
    os.rmdir(resources)
    shutil.copytree('/Library/Frameworks/QtGui.framework/Resources', resources)

    inf_file = os.path.join(mac_root, 'Contents', 'Info.plist')
    fin = open(inf_file, 'r')
    fou = open(inf_file + '_new', 'w')

    nextLine = False
    for line in fin:
        line = line.replace('MacLic', 'Lic')
        if nextLine and line.count('1') > 0:
            line = line.replace('1', '0')
        nextLine = line.count('LSBackgroundOnly') > 0
        fou.write(line)
    fin.close()
    fou.close()

    os.rename(inf_file + '_new', inf_file)
    os.rename(mac_root, lic_root)

    zipName = root + '/lic_%s_osx.zip' % lic_version
    zipDir(zipName, lic_root, len(app_root) + 1)

    print "OSX Distribution created: %s" % zipName

def createSvnExport(root):

    from src.Lic import __version__ as lic_version, _debug as lic_debug
    src_root = os.path.join(root)
    new_src_root = os.path.join(root, "lic_%s_src" % lic_version)
    
    if sys.platform != 'win32':
        return perr("Must use win32 to create source distribution")
 
    if os.path.isdir(new_src_root):
        return perr("Delete %s root folder before proceeding" % new_src_root)
  
    try:
        shutil.copytree(src_root, new_src_root)
    except OSError, exc: # python >2.5
        if exc.errno == errno.ENOTDIR:
            shutil.copy(src_root, new_src_root)
        else: raise

    return new_src_root, lic_version, lic_debug
    
def createSourceDist(root, src_root):

    if sys.platform != 'win32':
        return perr("Must use win32 to create source distribution")

    if not os.path.isdir(src_root):
        return perr("Source root %s does not exist!! Failed to create Source Distribution." % src_root)

    print "Zipping source folder"
    zipName = src_root + '.zip'
    zipDir(zipName, src_root, len(root) + 1)
    
    print "Source Distribution created: %s" % zipName
    
def createWin32Dist(root, src_root, lic_version):

    if sys.platform != 'win32':
        return perr("Must use win32 to create win32 distribution")

    if not os.path.isdir(src_root):
        return perr("Source root %s does not exist!! Failed to create Win32 Distribution." % src_root)

    lic_exec_name = 'licreator'
    pyinstaller_path = Win32PythonPath() + r"\Lib\site-packages\pyinstaller"
    if not os.path.isdir(pyinstaller_path):
        return perr("Could not find pyinstaller in %s" % pyinstaller_path)

    build_root = os.path.join(root, 'lic_%s_pyinst' % lic_version)
    spec_file = os.path.join(build_root, '%s.spec' % lic_exec_name)
    if not os.path.isdir(build_root):
        os.mkdir(build_root)

    print "Creating Win32 Specification file"
    args  = [Win32PythonPath() + '\Scripts\pyi-makespec.exe'
            ,'--onefile'
            ,'--windowed'
            ,'--icon=%s' % os.path.join(src_root,'images', 'lic_logo.ico')
            ,'--name=%s' % lic_exec_name
            ,'--specpath=%s' % build_root
            ,'%s' % os.path.join(src_root, 'src', 'Lic.py')
             ]
    subprocess.call(' '.join(args))

    if not os.path.isfile(spec_file):
        return perr("Failed to create Spec file - something went horribly awry.\nPut Lic.spec file at lic_%s_pyinst. Good luck! " % lic_version)

    print "Creating Win32 Binary Distribution"
    subprocess.call('%s %s' % (Win32PythonPath()+'\Scripts\pyinstaller.exe', spec_file))

    print "Win32 Distribution created" 

def main():

    if sys.platform.startswith('darwin'):
        createOSXDist()

    elif sys.platform.startswith('win32'):
        
        root = os.path.dirname(os.path.abspath(__file__))
        res = createSvnExport(root)
        if res is None:
            return
 
        src_root, lic_version, lic_debug = res
    
        createSourceDist(root, src_root)
        createWin32Dist(root, src_root, lic_version)
    else:
        return perr("Cannot run build script on %s" % sys.platform)

if __name__ == '__main__':
    main()
