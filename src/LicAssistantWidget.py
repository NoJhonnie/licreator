"""
    Lic - Instruction Book Creation software
    Copyright (C) 2010 Remi Gagne
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

from PyQt4.Qt import *

shortcuts = {
    1: ["Move vertically with 20 steps","Shift+Down | Up"]
    ,2: ["Move vertically with 5 steps","Ctrl+Down | Up"]
    ,3: ["Jump to next step on current page","Tab"]
    ,4: ["Move horizontally with 20 steps","Shift+Right | Left"]
    ,5: ["Move horizontally with 5 steps","Ctrl+Right | Left"]
    ,6: ["Jump to next page","PageDown"]
    ,7: ["Jump to previous page","PageUp"]
    ,8: ["Go to Title page","Home"]
    ,9: ["",""]
}

class LicShortcutAssistant(QWidget):

    _padding = 5
    _space = 10

    def __init__(self ,parent=None):
        QWidget.__init__(self,parent)
        self.setGeometry(QRect(parent.rect().width() -350 -1,1,350,220))
        self.setWindowFlags(Qt.SubWindow)
        self.setFocusPolicy(Qt.NoFocus);
        self.setFocusProxy(parent);
        self.setMouseTracking(True);      

    def paintEvent(self, event):
        p = QPainter(self)
        ht = p.fontMetrics().height()
        p.fillRect(self.rect(), QColor("#FFFACD"))
        p.setPen(Qt.black)
        for n in shortcuts:
            y = self._space*n+ht*n
            p.drawText(QPointF(self._padding ,y-5), shortcuts[n][0])
            p.drawText(QPointF(self._padding +200,y-5), shortcuts[n][1])
            p.drawLine(self._padding ,y ,self.width()-self._padding ,y)
        
        
        
        