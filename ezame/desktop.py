import os, sys, io, subprocess, tempfile
import gettext
_ = gettext.gettext
from configparser import ConfigParser

langs = []
languages = []
for envar in ('LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG'):
	val = os.environ.get(envar)
	if val:
		languages = val.split(':')
		break
if languages:
	for lang in languages:
		pos = lang.find('.')
		if pos >= 0:
			lang = lang[:pos]
		if not(lang in langs): langs.append(lang)
		pos = lang.find('@')
		if pos >= 0:
			lang = lang[:pos]
			if not(lang in langs): langs.append(lang)
		pos = lang.find('_')
		if pos >= 0:
			lang = lang[:pos]
			if not(lang in langs): langs.append(lang)
languages = None

class DE(object):
	def __init__(self, filename = None):
		self.filename = filename
		self.default_section = "Desktop Entry"
		self.content = ConfigParser(strict = False, comment_prefixes = ('#'), inline_comment_prefixes = None, delimiters = ('='), interpolation=None, default_section = None)
		self.content.BOOLEAN_STATES = {'true': True, 'false': False}
		self.content.optionxform = str
		self.content.add_section(self.default_section)
		if filename and os.path.exists(filename):
			try:
				self.content.read([filename])
			except:
				df = open(filename, "r")
				self.faulty_text = df.read()
			#filename, ext = os.path.splitext(filename)
			#print(self.filename)

	def get(self, key, group = None, locale = False):
		if not group: group = self.default_section
		if locale:
			try:
				for lang in langs:
					langkey = "%s[%s]" % (key, lang)
					for (k, v) in self.content.items(group, raw = True):
						if langkey == k:
							key = langkey
							raise
			except: pass
			try:
				value = self.content.get(group, key, raw = True)
				if value == "": return ""
				if self.get('X-Ubuntu-Gettext-Domain')!="": #for Ubuntu systems
					gettext.textdomain(self.get('X-Ubuntu-Gettext-Domain'))
				if isinstance(_(value), str): #gettext can return a info list
					return _(value)
				else:
					return value
			except: return ""
		else:
			try: return self.content.get(group, key, raw = True)
			except: return ""

	def getboolean(self, key, group = None):
		if not group: group = self.default_section
		try: return self.content.getboolean(group, key, raw = True)
		except: return False

	def getlist(self, key, group = None, locale = False):
		if not group: group = self.default_section
		try: return [x for x in self.get(key, group, locale).split(";") if x]
		except: return []
		
	def set(self, key, text, group = None, locale = False):
		if not group: group = self.default_section
		if locale:
			for lang in langs:
				langkey = "%s[%s]" % (key, lang)
				if langkey in self.content.items(group, raw = True):
					key = langkey
					break
		self.content.set(group, key, text)

	def read(self, filename = None):
		self.__init__(filename)

	def read_string(self, string):
		self.content.read_string(string)

	def as_string(self):
		text = ""
		if self.items():
			for group in self.items():
				text += "[%s]\n" % (group)
				for (key, value) in self.items(group):
					text += "%s=%s\n" % (key, value)
				text += "\n"
		return text

	def items(self, section = None):
		if section: return self.content.items(section, raw = True)
		else: return self.content.sections()

	def removeKey(self, key, group = None):
		if not group: group = self.default_section
		self.content.remove_option(group, key)

	def write(self, filename = None):
		if filename:
			self.filename = filename
		if self.filename:
			for group in self.items():
				for key, value in self.items(group):
					if not value: self.content.remove_option(group, key)
			td = tempfile.TemporaryDirectory()
			f = open(os.path.join(td.name, os.path.basename(self.filename)), "w")
			self.content.write(f, space_around_delimiters=False)
			f.close()
			command = ["desktop-file-validate", f.name]
			p = subprocess.Popen(command, stdout=subprocess.PIPE)
			if p.wait() == 0:
				command = ["desktop-file-install", "--dir="+ os.path.dirname(self.filename), f.name]
				p = subprocess.Popen(command)
				if p.wait() != 0:
					command = ["gksudo", "-D", "Ezame", "desktop-file-install --dir="+ os.path.dirname(self.filename) + " " + f.name]
					p = subprocess.Popen(command)
					p.wait()
			else:
				return '\n'.join(line.split(": ", maxsplit=1)[-1] for line in p.communicate()[0].decode("utf-8").split('\n'))
			os.remove(f.name)
