#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from ezame.ordde import DE
filename =  sys.argv[1]
string = sys.argv[2]
Entry = DE()
Entry.parseString(string)
Entry.write(filename)
