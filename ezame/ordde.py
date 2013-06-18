import os, io
from collections import OrderedDict
from xdg.DesktopEntry import DesktopEntry
from xdg.IniFile import IniFile
from xdg.Exceptions import (debug)
from xdg.Exceptions import ParsingError

class IF(IniFile):
	def __init__(self, filename=None):
		self.content = OrderedDict()
		if filename:
			self.parse(filename)

	def parse(self, filename, headers=None):
		content = self.content
		if not os.path.isfile(filename):
			raise ParsingError("File not found", filename)
		try:
			fd = io.open(filename, 'r', encoding='utf-8', errors='replace')
		except IOError as e:
			if debug:
				raise e
			else:
				return
		for line in fd:
			line = line.strip()
			if not line:
				continue
			elif line[0] == '#':
				continue
			elif line[0] == '[':
				currentGroup = line.lstrip("[").rstrip("]")
				if debug and self.hasGroup(currentGroup):
					raise DuplicateGroupError(currentGroup, filename)
				else:
					content[currentGroup] = OrderedDict()
			else:
				try:
					key, value = line.split("=", 1)
				except ValueError:
					raise ParsingError("Invalid line: " + line, filename)
				
				key = key.strip() # Spaces before/after '=' should be ignored
				try:
					if debug and self.hasKey(key, currentGroup):
						raise DuplicateKeyError(key, currentGroup, filename)
					else:
						content[currentGroup][key] = value.strip()
				except (IndexError, UnboundLocalError):
					raise ParsingError("Parsing error on key, group missing", filename)
		fd.close()
		self.filename = filename
		self.tainted = False
		if headers:
			for header in headers:
				if header in content:
					self.defaultGroup = header
					break
		else:
			raise ParsingError("[%s]-Header missing" % headers[0], filename)

	def parseString(self, string, headers=None):
		content = self.content
		content.clear()
		for line in string.split('\n'):
			line = line.strip()
			if not line:
				continue
			elif line[0] == '#':
				continue
			elif line[0] == '[':
				currentGroup = line.lstrip("[").rstrip("]")
				content[currentGroup] = OrderedDict()
			else:
				try:
					key, value = line.split("=", 1)
				except ValueError: pass
				key = key.strip()
				try:
					content[currentGroup][key] = value.strip()
				except (IndexError, UnboundLocalError): pass
		if headers:
			for header in headers:
				if header in content:
					self.defaultGroup = header
					break
		else:
			pass

	def addGroup(self, group):
		if self.hasGroup(group):
			if debug:
				raise DuplicateGroupError(group, self.filename)
		else:
			self.content[group] = OrderedDict()
			self.tainted = True

class DE(DesktopEntry, IF):
	def __init__(self, filename=None):
		self.content = OrderedDict()
		if filename and os.path.exists(filename):
			self.parse(filename)
		elif filename:
			self.new(filename)
	
	def parse(self, file):
		IF.parse(self, file, ["Desktop Entry", "KDE Desktop Entry"])
        
	def parseString(self, string):
		IF.parseString(self, string, ["Desktop Entry", "KDE Desktop Entry"])

	def new(self, filename):
		if os.path.splitext(filename)[1] == ".desktop":
			type = "Application"
		elif os.path.splitext(filename)[1] == ".directory":
			type = "Directory"
		else:
			raise ParsingError("Unknown extension", filename)
		self.content = OrderedDict()
		self.addGroup(self.defaultGroup)
		self.set("Type", type)
		self.filename = filename
