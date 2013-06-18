#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, glob
local = (len(sys.argv) > 1) and (sys.argv[1] == 'local')
python3 = not (sys.version_info < (3, 0))
from gi.repository import Gtk, Gdk, GdkPixbuf, Pango
import subprocess
if python3: import configparser
else: import ConfigParser
if local: from ordde import DE
else: from ezame.ordde import DE
from xdg.BaseDirectory import *
from xdg.IconTheme import *
from xdg.Menu import *
import gettext
#print(xdg_config_dirs)
if local: glade_path = 'ezame.glade'
else: glade_path = os.path.join(sys.prefix, 'share', 'ezame', 'ezame.glade')
mod_path = os.path.dirname(os.path.abspath(__file__))
LOCALE_DOMAIN = 'ezame'
gettext.textdomain(LOCALE_DOMAIN)
_ = gettext.gettext

class Ezame(object):

	def gtk_main_quit(self, *args):
		if python3:
			self.config['window'] = {'width': self.window.get_size()[0], 'height': self.window.get_size()[1]}
			self.config['paned'] = {'position': self.paned.get_position()}
		else:
			self.config.set('window','width',self.window.get_size()[0])
			self.config.set('window','height',self.window.get_size()[1])
			self.config.set('paned','position',self.paned.get_position())
		if not os.path.exists(os.path.dirname(self.config_file)): os.mkdir(os.path.dirname(self.config_file))
		with open(self.config_file, 'w') as config_file: self.config.write(config_file)
		self.desktree.disconnect(self.id_desktree_cursor_changed)
		Gtk.main_quit(*args)

	def on_Ruser_clicked(self, obj):
		if obj.get_active():
			if self.deskstore[self.desktree.get_cursor()[0]][3] == "":
				if "/applications/" in self.deskstore[self.desktree.get_cursor()[0]][4]: folder = "applications"
				else: folder = "desktop-directories"
				new_file = os.path.join(os.path.join(self.local_dir, folder), os.path.basename(self.deskstore[self.desktree.get_cursor()[0]][4]))
				self.Entry.write(new_file)
				self.deskstore[self.desktree.get_cursor()[0]][3] = new_file
				self.deskstore[self.desktree.get_cursor()[0]][5] = self.load_icon("user-home")
				self.change_tree("update")
			self.update_info()

	def on_Rsystem_clicked(self, obj):
		if obj.get_active():
			self.update_info()

	def on_Bundo_clicked(self, obj):
		self.update_info()

	def on_Bsave_clicked(self, obj):
		for group in self.Entry.content:
			for key in self.Entry.content[group]:
				if self.Entry.content[group][key] == "":
					self.Entry.removeKey(key, group)
		if self.Rsystem.get_active():
			if python3: pyexec = 'python3'
			else: pyexec = 'python'
			if local: cmd = ['gksudo', '-D', 'Ezame', '-s', pyexec, 'sudo.py', self.Entry.filename, self.entry_text()]
			else: cmd = ['gksudo', '-D', 'Ezame', '-s', pyexec, os.path.join(mod_path, 'sudo.py'), self.Entry.filename, self.entry_text()]
			subprocess.call(cmd)
		else:
			try: self.Entry.write()
			except: pass
		self.update_info()

	def change_key(self, key, text, locale = False, group = None):
		if not group: group = self.Entry.defaultGroup
		if locale:
			for lang in xdg.Locale.langs:
				langkey = "%s[%s]" % (key, lang)
				if langkey in self.Entry.content[group]: key = langkey
		self.Entry.set(key, text, group)
		self.update_objects()

	def on_Entry_changed(self, obj):
		if obj.is_focus():
			locale = getattr(obj, 'locale', False)
			group = getattr(obj, 'group', None)
			self.change_key(obj.key, obj.get_text(), locale, group)

	def on_Switch_notify(self, obj, active):
		if self.Entry:
			self.Entry.set(obj.key, str(obj.get_active()).lower())
			self.update_objects()
			
	def on_Bactionadd_clicked(self, obj):
		dialog = NewAction()
		dialog.Waction.set_transient_for(self.window)
		response = dialog.Waction.run()
		if response == Gtk.ResponseType.OK:
			dialog.Waction.hide()
			action = dialog.Eaction.get_text()
			self.Entry.addGroup(" ".join(("Desktop Action", action)))
			actions = self.Entry.getActions()
			actions.append(action)
			self.Entry.set("Actions", ";".join(actions))	
		dialog.Waction.destroy()
		self.update_objects(True, True)

	def on_Bactionremove_clicked(self, obj):
		try:
			sel_action = self.Nactions.get_tab_label_text(self.Nactions.get_nth_page(self.Nactions.get_current_page()))
			self.Entry.removeGroup(" ".join(("Desktop Action", sel_action)))
			actions = self.Entry.getActions()
			self.Entry.set("Actions", ";".join(action for action in actions if action != sel_action))
		except: pass
		self.update_objects(True, True)

	def on_BFileChooser_clicked(self, obj):
		def add_filters(dialog):
			filter_text = Gtk.FileFilter()
			filter_text.set_name(_("Image files")) #Imagens
			filter_text.add_mime_type("image/*")
			dialog.add_filter(filter_text)
			filter_any = Gtk.FileFilter()
			filter_any.set_name(_("Any files")) #Todos os Ficheiros
			dialog.add_filter(filter_any)
		dialog = Gtk.FileChooserDialog(obj.msg, self.window, obj.action, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
		if obj == self.Bicon: add_filters(dialog)
		response = dialog.run()
		if response == Gtk.ResponseType.OK:
			obj.entry.grab_focus()
			obj.entry.set_text(dialog.get_filename())
		dialog.destroy()

	def on_categtreecellrenderertoggle_toggled(self, cell, path, model, *ignore):
		model[model.get_iter(path)][0] = not model[model.get_iter(path)][0]
		categories = self.Entry.getCategories()
		if model[model.get_iter(path)][0]:
			categs = eval(model[model.get_iter(path)][3])
			for categ in categs: categories.append(categ)
			categs = eval(model[model.get_iter(path)][4])
			for categ in categs:
				if categ in categories: categories.remove(categ)
		else:
			categs = eval(model[model.get_iter(path)][3])
			for categ in categs:
				if categ in categories: categories.remove(categ)
		self.Entry.set("Categories",";".join(categories))			
		self.update_objects()

	def save_des(self):
		if self.Ronlyshowin.get_active():
			show_selected = "OnlyShowIn"
			show_removed = "NotShowIn"
		else:
			show_selected = "NotShowIn"
			show_removed = "OnlyShowIn"
		self.Entry.set(show_selected, ";".join(row[1] for row in self.destore if row[0]))
		self.Entry.removeKey(show_removed)
		self.update_objects()
		
	def on_Rshowin__clicked(self, obj):
		if obj.is_focus():
			self.save_des()

	def on_Mnew_activate(self, obj):
		def iterate(treeiter, filename):
			found = None
			while treeiter != None:
				if self.deskstore.iter_has_child(treeiter):
					childiter = self.deskstore.iter_children(treeiter)
					cursor = iterate(childiter, filename)
					if cursor != None: found = cursor
				if self.deskstore[treeiter][3] == filename:
					found = treeiter
					break
				treeiter = self.deskstore.iter_next(treeiter)
			return found
		dialog = NewEntry()
		dialog.Winput.set_transient_for(self.window)
		dialog.Cinputtype.append_text(_("Application"))
		dialog.Cinputtype.append_text(_("Link"))
		#if self.desktop != "Unity": dialog.Cinputtype.append_text(_("Directory"))
		dialog.Cinputtype.set_active(0)
		response = dialog.Winput.run()
		if response == Gtk.ResponseType.OK:
			dialog.Winput.hide()
			filetype = dialog.Cinputtype.get_active()
			if filetype == 0:
				ext = "desktop"
				type = "Application"
				folder = "applications"
			elif filetype == 1:
				ext = "desktop"
				type = "Link"
				folder = "applications"
			else:
				ext = "directory"
				type = "Directory"
				folder = "desktop-directories"
			filename = os.path.join(os.path.join(self.local_dir, folder), os.path.splitext(os.path.basename(dialog.Einputfile.get_text()))[0] + "." + ext)
			self.Entry = DE(filename)
			self.Entry.set("Type", type)
			self.Entry.write()
			os.chmod(filename, 0o755)
			self.load_menu()
			try:
				rootiter = self.deskstore.get_iter_first()
				found = iterate(rootiter, filename)
				path = self.deskstore.get_path(found)
				self.desktree.expand_to_path(path)
				self.desktree.set_cursor(path)
				self.desktree.scroll_to_cell(path)
			except: pass
		dialog.Winput.destroy()

	def on_Mdelete_activate(self, obj):
		os.remove(self.deskstore[self.desktree.get_cursor()[0]][3])
		if self.deskstore[self.desktree.get_cursor()[0]][4] == "":
			self.change_tree("delete")
		else:
			self.deskstore[self.desktree.get_cursor()[0]][3] = ""
			self.deskstore[self.desktree.get_cursor()[0]][5] = None
			self.change_tree("update")
		self.update_info()

	def on_Mrefresh_activate(self, obj):	
		self.load_menu()

	def on_Mclipboard_activate(self, obj):
		focused = self.window.get_focus()
		try:
			if obj == self.Mcut: focused.cut_clipboard()
			elif obj == self.Mcopy: focused.copy_clipboard()
			elif obj == self.Mpaste: focused.paste_clipboard()
		except: pass

	def on_Mpreferences_activate(self, obj):
		dialog = Preferences()
		dialog.Wpreferences.set_transient_for(self.window)
		dialog.Rcinnamon.set_sensitive(os.path.isfile("/etc/xdg/menus/cinnamon-applications.menu"))
		dialog.Rxfce.set_sensitive(os.path.isfile("/etc/xdg/menus/xfce-applications.menu"))
		dialog.Rlxde.set_sensitive(os.path.isfile("/etc/xdg/menus/lxde-applications.menu"))
		if self.desktop == "Unity": dialog.Rubuntu.set_active(True)
		elif self.desktop == "Cinnamon": dialog.Rcinnamon.set_active(True)
		elif self.desktop == "XFCE": dialog.Rxfce.set_active(True)
		elif self.desktop == "LXDE": dialog.Rlxde.set_active(True)
		else: dialog.Rclassic.set_active(True)
		response = dialog.Wpreferences.run()
		if response == Gtk.ResponseType.OK:
			if dialog.Rubuntu.get_active(): self.desktop = "Unity"
			elif dialog.Rcinnamon.get_active(): self.desktop = "Cinnamon"
			elif dialog.Rxfce.get_active(): self.desktop = "XFCE"
			elif dialog.Rlxde.get_active(): self.desktop = "LXDE"
			else: self.desktop = "Classic"
			dialog.Wpreferences.hide()
			while Gtk.events_pending(): Gtk.main_iteration()
			self.load_menu()
		dialog.Wpreferences.destroy()

	def on_Mabout_activate(self, obj):
		builder = Gtk.Builder()
		builder.set_translation_domain(LOCALE_DOMAIN)
		builder.add_from_file(glade_path)
		self.Wabout = builder.get_object("Wabout")	
		self.Wabout.run()
		self.Wabout.destroy()

	def on_showtreecellrenderertoggle_toggled(self, cell, path, model, *ignore):
		model[model.get_iter(path)][0] = not model[model.get_iter(path)][0]
		self.save_des()

	def on_desktop_buffer_changed(self, obj):
		if self.desktop_view.is_focus():
			self.Entry.parseString(self.desktop_buffer.get_text(self.desktop_buffer.get_start_iter(), self.desktop_buffer.get_end_iter(), False))
			self.update_objects(False, True)

	def on_desktree_cursor_changed(self, widget):
		self.desktree.grab_focus()
		if self.deskstore[self.desktree.get_cursor()[0]][3] == "":
			self.Rsystem.set_active(True)
		else:
			self.Ruser.set_active(True)
		self.update_info()

	def update_info(self):
		if self.Rsystem.get_active():
			desktop_file_path = self.deskstore[self.desktree.get_cursor()[0]][4]
		else:
			desktop_file_path = self.deskstore[self.desktree.get_cursor()[0]][3]
		self.Rsystem.set_sensitive(not self.deskstore[self.desktree.get_cursor()[0]][4] == "")
		if desktop_file_path == "":
			self.Entry = None
			self.disable_all()
		else:
			self.Entry = DE(desktop_file_path)
			self.update_objects(True, True)

	def getMenu(self, menu, path):
		array = path.split("/", 1)
		for submenu in menu.Submenus:
			if (submenu.getName()) == array[0]:
				if len(array) > 1:
					return self.getMenu(submenu, array[1])
				else:
					return submenu

	def getMenuEntry(self, menu, desktopfileid):
		for menuentry in menu.MenuEntries:
			if menuentry.DesktopFileID == desktopfileid:
				return menuentry
		for submenu in menu.Submenus:
			menuentry = self.getMenuEntry(submenu, desktopfileid)
			if menuentry: return menuentry

	def DesktopFileID(self, desktop_file_path):
		head, DesktopFileID = os.path.split(desktop_file_path)
		while True:
			head, tail = os.path.split(head)
			if tail != "applications" and head != "": DesktopFileID = tail + "-" + DesktopFileID
			else: break
		return DesktopFileID

	def update_objects(self, update_editor=True, update_actions=False):
		Entry = self.Entry
		self.enable_all()
		self.Mdelete.set_sensitive(self.Ruser.get_active())
		self.Efile.set_text(Entry.filename)
		self.Ltype.set_text(Entry.getType())
		self.Ename.set_text(Entry.getName())
		self.Egenericname.set_text(Entry.getGenericName())
		self.Snodisplay.set_active(Entry.getNoDisplay())
		try:
			if self.deskstore[self.desktree.get_cursor()[0]][8] != "": self.deskstore[self.desktree.get_cursor()[0]][0] = self.getMenuEntry(self.menu, self.deskstore[self.desktree.get_cursor()[0]][8]).DesktopEntry.getName()
			else: self.deskstore[self.desktree.get_cursor()[0]][0] = Entry.getName()
			if self.deskstore[self.desktree.get_cursor()[0]][0] == "": self.deskstore[self.desktree.get_cursor()[0]][0] = Entry.getName() # for new entries that don't have registered DesktopFileID
		except: pass
		self.deskstore[self.desktree.get_cursor()[0]][2] = self.load_icon(Entry.getIcon())
		self.deskstore[self.desktree.get_cursor()[0]][6] = not self.Snodisplay.get_active()
		self.Eexec.set_text(Entry.getExec())
		self.Epath.set_text(Entry.getPath())
		self.Eicon.set_text(Entry.getIcon())
		self.Ecomment.set_text(Entry.getComment())
		self.Eurl.set_text(Entry.getURL())

		categories = Entry.getCategories()
		for row in self.categstore: row[0] = eval(row[2])

		if Entry.getNotShowIn():
			self.Rnotshowin.set_active(True)
			des = Entry.getNotShowIn()
		elif Entry.getOnlyShowIn():
			self.Ronlyshowin.set_active(True)
			des = Entry.getOnlyShowIn()
		else: des = []
		self.destore.clear()
		for de in self.de_list: self.destore.append([False, de])
		for de in des:
			exist = False
			for row in self.destore:
				if de == row[1]: exist = True
			if not exist: self.destore.append([False, de])
		for row in self.destore: row[0] = row[1] in des

		self.Eversion.set_text(Entry.getVersionString())
		self.Shidden.set_active(Entry.getHidden())
		self.Etryexec.set_text(Entry.getTryExec())
		self.Sterminal.set_active(Entry.getTerminal())
		try:
			if self.Emimetypes.get_text()[-1] != ";": self.Emimetypes.set_text(";".join(Entry.getMimeTypes()))
		except: self.Emimetypes.set_text(";".join(Entry.getMimeTypes()))
		try:
			if self.Ekeywords.get_text()[-1] != ";": self.Ekeywords.set_text(";".join(Entry.getKeywords()))
		except: self.Ekeywords.set_text(";".join(Entry.getKeywords()))
		self.Sstartupnotify.set_active(Entry.getStartupNotify())
		self.Estartupwmclass.set_text(Entry.getStartupWMClass())
		if update_editor:
			self.desktop_buffer.set_text(self.entry_text())
			self.text_format()
		if update_actions:
			for child in self.Nactions.get_children(): self.Nactions.remove(child)
			for (group, content) in self.Entry.content.items():
				if "Desktop Action" in group:
					self.insert_action(group)
			self.Nactions.show_all()

	def insert_action(self, group):
		label = Gtk.Label(" ".join(group.split()[2:]))
		Laname = Gtk.Label(_("Name"), halign=Gtk.Align.START)
		Laexec = Gtk.Label(_("Exec"), halign=Gtk.Align.START)
		Laicon = Gtk.Label(_("Icon"), halign=Gtk.Align.START)
		Eaname = Gtk.Entry()
		Eaname.key = "Name"
		Eaname.group = group
		Eaname.locale = True
		Eaname.set_hexpand(True)
		Eaname.set_text(self.Entry.get("Name", group))
		self.id_Eaname_changed = Eaname.connect("changed", self.on_Entry_changed)
		Eaexec = Gtk.Entry()
		Eaexec.key = "Exec"
		Eaexec.group = group
		Eaexec.set_hexpand(True)
		Eaexec.set_text(self.Entry.get("Exec", group))
		self.id_Eaexec_changed = Eaexec.connect("changed", self.on_Entry_changed)
		Baexec = Gtk.Button(stock = "gtk-open")
		Baexec.set_always_show_image(True)
		Baexec.msg = _("Choose a file")
		Baexec.action = Gtk.FileChooserAction.OPEN
		Baexec.entry = Eaexec
		self.id_Baexec_clicked = Baexec.connect("clicked", self.on_BFileChooser_clicked)
		boxexec = Gtk.Box()
		boxexec.pack_start(Eaexec, True, True, 0)
		boxexec.pack_start(Baexec, False, False, 0)
		Eaicon = Gtk.Entry()
		Eaicon.key = "Icon"
		Eaicon.group = group
		Eaicon.locale = True
		Eaicon.set_hexpand(True)
		Eaicon.set_text(self.Entry.get("Icon", group))
		self.id_Eaicon_changed = Eaicon.connect("changed", self.on_Entry_changed)
		Baicon = Gtk.Button(stock = "gtk-open")
		Baicon.set_always_show_image(True)
		Baicon.msg = _("Choose a file")
		Baicon.action = Gtk.FileChooserAction.OPEN
		Baicon.entry = Eaicon
		self.id_Baicon_clicked = Baicon.connect("clicked", self.on_BFileChooser_clicked)
		boxicon = Gtk.Box()
		boxicon.pack_start(Eaicon, True, True, 0)
		boxicon.pack_start(Baicon, False, False, 0)
		grid = Gtk.Grid(halign=Gtk.Align.FILL)
		grid.set_row_spacing(4)
		grid.set_column_spacing(4)
		grid.set_border_width(4)
		grid.set_hexpand(True)
		grid.add(Laname)
		grid.attach(Laexec, 0, 1, 1, 1)
		grid.attach(Laicon, 0, 2, 1, 1)
		grid.attach(Eaname, 1, 0, 1, 1)
		grid.attach(boxexec, 1, 1, 1, 1)
		grid.attach(boxicon, 1, 2, 1, 1)
		self.Nactions.append_page(grid, label)

	def entry_text(self):
		text = ""
		if self.Entry.defaultGroup:
			text += "[%s]\n" % self.Entry.defaultGroup
			if self.Entry.content:
				for (key, value) in self.Entry.content[self.Entry.defaultGroup].items():
					text += "%s=%s\n" % (key, value)
				text += "\n"
		for (name, group) in self.Entry.content.items():
			if name != self.Entry.defaultGroup:
				text += "[%s]\n" % name
				for (key, value) in group.items():
					text += "%s=%s\n" % (key, value)
				text += "\n"
		return text

	def load_objects(self, builder):
		self.window = builder.get_object("window")
		self.deskstore = builder.get_object("deskstore")
		self.destore = builder.get_object("destore")
		self.categstore = builder.get_object("categstore")
		self.desktree = builder.get_object("desktree")
		self.desktreecol1 = builder.get_object("desktreecol1")
		self.desktreecol1.set_resizable(True)
		self.desktreecol2 = builder.get_object("desktreecol2")
		self.categtree = builder.get_object("categtree")
		self.showtree = builder.get_object("showtree")
		self.showtreeselection = builder.get_object("showtreeselection")
		self.paned = builder.get_object("paned")
		self.scrolledwindowprop = builder.get_object("scrolledwindowprop")
		self.scrolledwindowmore = builder.get_object("scrolledwindowmore")
		self.scrolledwindowactions = builder.get_object("scrolledwindowactions")
		self.scrolledwindoweditor = builder.get_object("scrolledwindoweditor")
		self.desktop_buffer = builder.get_object("desktop_buffer")
		self.Efile = builder.get_object("Efile")
		self.Ltype = builder.get_object("Ltype")
		self.Ename = builder.get_object("Ename")
		self.Ename.key = "Name"
		self.Ename.locale = "True"
		self.Egenericname = builder.get_object("Egenericname")
		self.Egenericname.key = "GenericName"
		self.Egenericname.locale = "True"
		self.Snodisplay = builder.get_object("Snodisplay")
		self.Snodisplay.key = "NoDisplay"
		self.Eexec = builder.get_object("Eexec")
		self.Eexec.key = "Exec"
		self.Lexec = builder.get_object("Lexec")
		self.Epath = builder.get_object("Epath")
		self.Epath.key = "Path"
		self.Lpath = builder.get_object("Lpath")
		self.Eicon = builder.get_object("Eicon")
		self.Eicon.key = "Icon"
		self.Eicon.locale = "True"
		self.Licon = builder.get_object("Eicon")
		self.Bexec = builder.get_object("Bexec")
		self.Bexec.msg = _("Choose a file")
		self.Bexec.action = Gtk.FileChooserAction.OPEN
		self.Bexec.entry = self.Eexec
		self.Bpath = builder.get_object("Bpath")
		self.Bpath.msg = _("Choose a folder")
		self.Bpath.action = Gtk.FileChooserAction.SELECT_FOLDER
		self.Bpath.entry = self.Epath
		self.Bicon = builder.get_object("Bicon")
		self.Bicon.msg = _("Choose a icon")
		self.Bicon.action = Gtk.FileChooserAction.OPEN
		self.Bicon.entry = self.Eicon
		self.Ecomment = builder.get_object("Ecomment")
		self.Ecomment.key = "Comment"
		self.Ecomment.locale = "Comment"
		self.Eurl = builder.get_object("Eurl")
		self.Eurl.key = "Url"
		self.Lurl = builder.get_object("Lurl")
		self.Ronlyshowin = builder.get_object("Ronlyshowin")
		self.Rnotshowin = builder.get_object("Rnotshowin")
		self.categtreecellrenderertoggle = builder.get_object("categtreecellrenderertoggle")
		self.showtreecellrenderertoggle = builder.get_object("showtreecellrenderertoggle")
		self.Eversion = builder.get_object("Eversion") #more
		self.Eversion.key = "Version"
		self.Shidden = builder.get_object("Shidden")
		self.Shidden.key = "Hidden"
		self.Etryexec = builder.get_object("Etryexec")
		self.Etryexec.key = "TryExec"
		self.Ltryexec = builder.get_object("Ltryexec")
		self.Btryexec = builder.get_object("Btryexec")
		self.Btryexec.msg = _("Choose a file")
		self.Btryexec.action = Gtk.FileChooserAction.OPEN
		self.Btryexec.entry = self.Etryexec
		self.Sterminal = builder.get_object("Sterminal")
		self.Sterminal.key = "Terminal"
		self.Lterminal = builder.get_object("Lterminal")
		self.Lmimetypes = builder.get_object("Lmimetypes")
		self.Emimetypes = builder.get_object("Emimetypes")
		self.Emimetypes.key = "MimeType"
		self.Lkeywords = builder.get_object("Lkeywords")
		self.Ekeywords = builder.get_object("Ekeywords")
		self.Ekeywords.key = "Keywords"
		self.Lstartupnotify = builder.get_object("Lstartupnotify")
		self.Sstartupnotify = builder.get_object("Sstartupnotify")
		self.Sstartupnotify.key = "StartupNotify"
		self.Lstartupwmclass = builder.get_object("Lstartupwmclass")
		self.Estartupwmclass = builder.get_object("Estartupwmclass")
		self.Estartupwmclass.key = "StartupWMClass"
		self.desktop_view = builder.get_object("desktop_view")
		self.desktop_buffer = builder.get_object("desktop_buffer")
		self.Box_buttons = builder.get_object("Box_buttons")
		self.Ruser = builder.get_object("Ruser")
		self.Rsystem = builder.get_object("Rsystem")
		self.Bundo = builder.get_object("Bundo")
		self.Bsave = builder.get_object("Bsave")
		self.Mnew = builder.get_object("Mnew")
		self.Msave = builder.get_object("Msave")
		self.Mdelete = builder.get_object("Mdelete")
		self.Mrefresh = builder.get_object("Mrefresh")
		self.Mquit = builder.get_object("Mquit")	
		self.Mundo = builder.get_object("Mundo")	
		self.Mcut = builder.get_object("Mcut")	
		self.Mcopy = builder.get_object("Mcopy")	
		self.Mpaste = builder.get_object("Mpaste")	
		self.Mpreferences = builder.get_object("Mpreferences")	
		self.Mabout = builder.get_object("Mabout")	
		self.Bactionadd = builder.get_object("Bactionadd")	
		self.Bactionremove = builder.get_object("Bactionremove")	
		self.Nactions = builder.get_object("Nactions")	


	def load_prefs(self):
		self.de_list = ["GNOME", "KDE",  "LXDE", "MATE", "Razor", "ROX", "TDE", "Unity", "XFCE", "Cinnamon", "Old"]
		self.desktop = os.environ.get('XDG_CURRENT_DESKTOP')
		if self.desktop == "GNOME" and os.environ.get('MDMSESSION') != None and os.path.isfile("/etc/xdg/menus/cinnamon-applications.menu"): self.desktop = "Cinnamon"
		self.icon_size = 22
		for path in xdg_data_dirs:
			if "/." in path: self.local_dir = path
			if not "/." in path: self.system_dir = path
		for path in xdg_data_dirs:
			if "/usr/share" == path: self.system_dir = path
		self.default_theme = Gtk.IconTheme.get_default()
		self.tag_bold = self.desktop_buffer.create_tag("bold", weight=Pango.Weight.BOLD)
		self.tag_red = self.desktop_buffer.create_tag("red", foreground="red")
		
		for path in xdg_config_dirs:
			if "/." in path: self.config_file = os.path.join(os.path.join(path, "ezame"), "preferences")
		try:
			if python3: self.config = configparser.ConfigParser()
			else: self.config = ConfigParser.ConfigParser()
			self.config.read(self.config_file)
			if python3:
				self.window.resize(int(self.config['window']['width']), int(self.config['window']['height']))
				self.paned.set_position(int(self.config['paned']['position']))
			else:
				self.window.resize(int(self.config.get('window','width')), int(self.config.get('window','height')))
				self.paned.set_position(int(self.config.get('paned','position')))
		except: pass

	def load_signals(self):
		self.window.connect("delete-event", self.gtk_main_quit)
		self.id_desktree_cursor_changed = self.desktree.connect("cursor-changed", self.on_desktree_cursor_changed)
		self.id_Ename_changed = self.Ename.connect("changed", self.on_Entry_changed)
		self.id_Egenericname_changed = self.Egenericname.connect("changed", self.on_Entry_changed)
		self.id_Snodisplay_notify = self.Snodisplay.connect("notify::active", self.on_Switch_notify)
		self.id_Eexec_changed = self.Eexec.connect("changed", self.on_Entry_changed)
		self.id_Epath_changed = self.Epath.connect("changed", self.on_Entry_changed)
		self.id_Eicon_changed = self.Eicon.connect("changed", self.on_Entry_changed)
		self.id_Ecomment_changed = self.Ecomment.connect("changed", self.on_Entry_changed)
		self.id_Eurl_changed = self.Eurl.connect("changed", self.on_Entry_changed)
		self.id_Eversion_changed = self.Eversion.connect("changed", self.on_Entry_changed) #More...
		self.id_Shidden_notify = self.Shidden.connect("notify::active", self.on_Switch_notify)
		self.id_Etryexec_changed = self.Etryexec.connect("changed", self.on_Entry_changed)
		self.id_Sterminal_notify = self.Sterminal.connect("notify::active", self.on_Switch_notify)
		self.id_Emymetypes_changed = self.Emimetypes.connect("changed", self.on_Entry_changed)
		self.id_Ekeywords_changed = self.Ekeywords.connect("changed", self.on_Entry_changed)
		self.id_Sstartupnotify_notify = self.Sstartupnotify.connect("notify::active", self.on_Switch_notify)
		self.id_Estartupwmclass_changed = self.Estartupwmclass.connect("changed", self.on_Entry_changed)
		self.id_Bexec_clicked = self.Bexec.connect("clicked", self.on_BFileChooser_clicked)
		self.id_Bpath_clicked = self.Bpath.connect("clicked", self.on_BFileChooser_clicked)
		self.id_Bicon_clicked = self.Bicon.connect("clicked", self.on_BFileChooser_clicked)
		self.id_Btryexec_clicked = self.Btryexec.connect("clicked", self.on_BFileChooser_clicked)
		self.id_Ronlyshowin_clicked = self.Ronlyshowin.connect("clicked", self.on_Rshowin__clicked)
		self.id_Rnotshowin_clicked = self.Rnotshowin.connect("clicked", self.on_Rshowin__clicked)
		self.id_categtreecellrenderertoggle_toggled = self.categtreecellrenderertoggle.connect("toggled", self.on_categtreecellrenderertoggle_toggled, self.categstore)
		self.id_showtreecellrenderertoggle_toggled = self.showtreecellrenderertoggle.connect("toggled", self.on_showtreecellrenderertoggle_toggled, self.destore)
		self.id_desktop_buffer_changed = self.desktop_buffer.connect("changed", self.on_desktop_buffer_changed)
		self.id_Ruser_clicked = self.Ruser.connect("clicked", self.on_Ruser_clicked)
		self.id_Rsystem_clicked = self.Rsystem.connect("clicked", self.on_Rsystem_clicked)
		self.id_Bundo_clicked = self.Bundo.connect("clicked", self.on_Bundo_clicked)
		self.id_Bsave_clicked = self.Bsave.connect("clicked", self.on_Bsave_clicked)
		self.id_Mnew_activate = self.Mnew.connect("activate", self.on_Mnew_activate)
		self.id_Msave_activate = self.Msave.connect("activate", self.on_Bsave_clicked)
		self.id_Mdelete_activate = self.Mdelete.connect("activate", self.on_Mdelete_activate)
		self.id_Mrefresh_activate = self.Mrefresh.connect("activate", self.on_Mrefresh_activate)
		self.id_Mquit_activate = self.Mquit.connect("activate", self.gtk_main_quit)
		self.id_Mundo_activate = self.Mundo.connect("activate", self.on_Bundo_clicked)
		self.id_Mcut_activate = self.Mcut.connect("activate", self.on_Mclipboard_activate)
		self.id_Mcopy_activate = self.Mcopy.connect("activate", self.on_Mclipboard_activate)
		self.id_Mpaste_activate = self.Mpaste.connect("activate", self.on_Mclipboard_activate)
		self.id_Mpreferences_activate = self.Mpreferences.connect("activate", self.on_Mpreferences_activate)
		self.id_Mabout_activate = self.Mabout.connect("activate", self.on_Mabout_activate)
		self.id_Bactionadd_clicked = self.Bactionadd.connect("clicked", self.on_Bactionadd_clicked)
		self.id_Bactionremove_clicked = self.Bactionremove.connect("clicked", self.on_Bactionremove_clicked)

	def enable_all(self):
		self.scrolledwindoweditor.set_sensitive(True)
		self.scrolledwindowactions.set_sensitive(True)
		self.scrolledwindowmore.set_sensitive(True)
		self.scrolledwindowprop.set_sensitive(True)
		self.categtree.set_sensitive(True)
		self.showtree.set_sensitive(True)
		self.Rnotshowin.set_sensitive(True)
		self.Ronlyshowin.set_sensitive(True)			
		self.Box_buttons.set_sensitive(True)
		self.Mundo.set_sensitive(True)
		self.Msave.set_sensitive(True)
		app = self.Entry.getType() == "Application"
		link = self.Entry.getType() == "Link"
		self.Eurl.set_visible(link)
		self.Lurl.set_visible(link)
		self.scrolledwindowactions.set_visible(app)
		self.Eexec.set_visible(app)			
		self.Lexec.set_visible(app)
		self.Bexec.set_visible(app)
		self.Epath.set_visible(app)
		self.Lpath.set_visible(app)
		self.Bpath.set_visible(app)
		self.categtree.set_sensitive(app)
		self.Etryexec.set_visible(app) #more
		self.Ltryexec.set_visible(app)
		self.Btryexec.set_visible(app)
		self.Sterminal.set_visible(app)
		self.Lterminal.set_visible(app)
		self.Lmimetypes.set_visible(app)
		self.Emimetypes.set_visible(app)
		self.Lkeywords.set_visible(app)
		self.Ekeywords.set_visible(app)
		self.Lstartupnotify.set_visible(app)
		self.Sstartupnotify.set_visible(app)
		self.Lstartupwmclass.set_visible(app)
		self.Estartupwmclass.set_visible(app)

	def disable_all(self):
		self.scrolledwindoweditor.set_sensitive(False)
		self.scrolledwindowactions.set_sensitive(False)
		self.scrolledwindowmore.set_sensitive(False)
		self.scrolledwindowprop.set_sensitive(False)
		self.categtree.set_sensitive(False)
		self.showtree.set_sensitive(False)
		self.Rnotshowin.set_sensitive(False)
		self.Ronlyshowin.set_sensitive(False)
		self.Box_buttons.set_sensitive(False)			
		self.Mundo.set_sensitive(False)
		self.Msave.set_sensitive(False)
		self.Mdelete.set_sensitive(False)
		self.desktop_buffer.set_text("")
		self.Efile.set_text("")
		self.Ltype.set_text("")
		self.Ename.set_text("")
		self.Egenericname.set_text("")
		self.Snodisplay.set_active(False)
		self.Eexec.set_text("")
		self.Epath.set_text("")
		self.Eicon.set_text("")
		self.Ecomment.set_text("")
		self.Eurl.set_text("")
		self.Rnotshowin.set_active(False)
		self.Ronlyshowin.set_active(False)
		self.Eversion.set_text("") #more
		self.Shidden.set_active(False)
		self.Etryexec.set_text("")
		self.Sterminal.set_active(False)
		self.Emimetypes.set_text("")
		self.Ekeywords.set_text("")
		self.Sstartupnotify.set_active(False)
		self.Estartupwmclass.set_text("")
		for categ in self.categstore: categ[0] = False
		self.Ronlyshowin.set_active(True)
		for de in self.destore: de[0] = False

	def text_format(self):
		def search_and_mark(text, tag, start):
			end = self.desktop_buffer.get_end_iter()
			match = start.forward_search(text, 0, end)
			if match != None:
				match_start, match_end = match
				self.desktop_buffer.apply_tag(tag, match_start, match_end)
				search_and_mark(text, tag, match_end)

		keywords_list = ["[Desktop Entry]", "Type=", "Name=", "Icon=", "MimeType=", "Exec=", "TryExec=", "NoDisplay=", "Actions=", "StartupNotify=", "Encoding=", "Comment=", "Categories=", "StartupWMClass=", "Terminal=", "GenericName=", "Path=", "Version=", "OnlyShowIn=", "NotShowIn=", "Keywords="]
		search_and_mark(";", self.tag_red, self.desktop_buffer.get_start_iter())
		for word in keywords_list:
			search_and_mark(word, self.tag_bold, self.desktop_buffer.get_start_iter())
		
	def change_tree(self, action):
		def iterate(treeiter, filename, action):
			while treeiter != None:
				deleted = False
				if self.deskstore.iter_has_child(treeiter):
					childiter = self.deskstore.iter_children(treeiter)
					iterate(childiter, filename, action)
				if self.deskstore[treeiter][3] == filename or self.deskstore[treeiter][4] == filename:
					if action == "update":
						self.deskstore[treeiter] = self.deskstore[self.desktree.get_cursor()[0]][:]
					elif action == "delete":
						self.deskstore.remove(treeiter)
						deleted = True
				if not deleted: treeiter = self.deskstore.iter_next(treeiter)

		path = self.desktree.get_cursor()[0]
		rootiter = self.deskstore.get_iter_first()
		if self.deskstore[self.desktree.get_cursor()[0]][4] == "": 
			filename = self.deskstore[self.desktree.get_cursor()[0]][3]
		else:
			filename = self.deskstore[self.desktree.get_cursor()[0]][4]
		iterate(rootiter, filename, action)
		try: self.desktree.set_cursor(path)
		except: pass

	def load_icon(self, icon):
		if self.default_theme.lookup_icon(icon, self.icon_size, 0):
			pixbuf = self.default_theme.load_icon(icon, self.icon_size, 0).scale_simple(self.icon_size, self.icon_size, GdkPixbuf.InterpType.BILINEAR)
		else:
			try:
				pixbuf = GdkPixbuf.Pixbuf.new_from_file(getIconPath(icon)).scale_simple(self.icon_size, self.icon_size, GdkPixbuf.InterpType.BILINEAR)
			except:
				pixbuf = None
				#pass
		return pixbuf

	def load_menu(self):
		self.desktree.grab_focus()
		load = Loading()
		load.Wloading.set_transient_for(self.window)
		load.Wloading.show()
		while Gtk.events_pending(): Gtk.main_iteration()
		self.desktree.disconnect(self.id_desktree_cursor_changed)
		self.desktree.freeze_child_notify()
		self.desktree.set_model(None)
		self.desktree.set_visible(False)
		self.deskstore.clear()
		self.categstore.clear()
		self.deskstore.set_default_sort_func(lambda *unused: 0)
		self.deskstore.set_sort_column_id(-1, Gtk.SortType.ASCENDING)
		self.categstore.set_sort_column_id(1, Gtk.SortType.ASCENDING)
		self.disable_all()
		if self.desktop == "Unity":
			self.load_unity_menu()
		else: #Others
			self.load_freedesktop()
		self.desktree.set_model(self.deskstore)
		self.desktree.set_visible(True)
		self.desktree.thaw_child_notify()
		self.id_desktree_cursor_changed = self.desktree.connect("cursor-changed", self.on_desktree_cursor_changed)
		load.Wloading.destroy()

	def load_freedesktop(self):
		def load_submenu(menu, parent):
			for entry in menu.Entries:
				if isinstance(entry, Menu):
					try:
						menuName = entry.getName()
						if "/." in entry.Directory.DesktopEntry.filename:
							local = entry.Directory.DesktopEntry.filename
							system = ""
							local_icon = self.load_icon("user-home")
						else:
							local = ""
							system = entry.Directory.DesktopEntry.filename
							local_icon = None
						treeiter = self.deskstore.append(parent,[menuName, menuName, self.load_icon(entry.getIcon()), local, system, local_icon, not entry.Directory.DesktopEntry.getNoDisplay(), True, entry.getPath()])
					except: pass
					try: load_submenu(entry, treeiter)
					except: pass
				elif isinstance(entry, MenuEntry):
					try:
						if "/." in entry.DesktopEntry.filename:
							local = entry.DesktopEntry.filename
							system = ""
							local_icon = self.load_icon("user-home")
						else:
							local = ""
							system = entry.DesktopEntry.filename
							local_icon = None
						treeiter = self.deskstore.append(parent,[entry.DesktopEntry.getName(), entry.DesktopEntry.getName(), self.load_icon(entry.DesktopEntry.getIcon()), local, system, local_icon, not entry.DesktopEntry.getNoDisplay(), True, self.DesktopFileID(entry.DesktopEntry.filename)])
					except: pass
				elif isinstance(entry, Separator):
					try: treeiter = self.deskstore.append(parent,["-" * 300, "", None, "", "", None, True, True, str(entry)])
					except: pass
			
		menus = {
		"AudioVideo":				["'AudioVideo' in categories", "['AudioVideo']", "[]"],
		"Audio":					["'Audio' in categories and 'AudioVideo' in categories", "['Audio', 'AudioVideo']", "[]"],
		"Video":					["'Video' in categories and 'AudioVideo' in categories", "['Video', 'AudioVideo']", "[]"],
		"Development":				["'Development' in categories", "['Development']", "[]"],
		"Education":				["'Education' in categories", "['Education']", "[]"],
		"Game":						["'Game' in categories", "['Game']", "[]"],
		"Graphics":					["'Graphics' in categories", "['Graphics']", "[]"],
		"Network":					["'Network' in categories", "['Network']", "[]"],
		"Office":					["'Office' in categories", "['Office']", "[]"],
		"Science":					["'Science' in categories", "['Science']", "[]"],
		"Settings":					["'Settings' in categories", "['Settings']", "[]"],
		"System":					["'System' in categories", "['System']", "[]"],
		"Utility":					["'Utility' in categories", "['Utility']", "[]"]
		}

		for menuName in menus:
			self.categstore.append([False, menuName, menus[menuName][0], menus[menuName][1], menus[menuName][2]])
		if self.desktop == "Cinnamon":
			try: self.menu = parse("cinnamon-applications.menu")
			except: self.menu = parse()
		elif self.desktop == "XFCE":
			try: self.menu = parse("xfce-applications.menu")
			except: self.menu = parse()
		elif self.desktop == "LXDE":
			try: self.menu = parse("lxde-applications.menu")
			except: self.menu = parse()
		else: self.menu = parse()
		load_submenu(self.menu, None)

	def load_deskfiles(self):
		desk_system = []
		desk_user = []
		desk_files = []
		for path in xdg_data_dirs:
			path = os.path.join(path, "applications")
			for desk_file in glob.glob(os.path.join(path, "*.desktop")):
				if "/." in desk_file: desk_user.append(desk_file)
				else: desk_system.append(desk_file)
		for user_file in desk_user:
			have_system = False
			for system_file in desk_system:
				if os.path.basename(system_file) == os.path.basename(user_file):
					desk_files.append((user_file, system_file))
					desk_system.remove(system_file)
					have_system = True
					break
			if not have_system: desk_files.append((user_file, ""))
		for system_file in desk_system: desk_files.append(("", system_file))
		return desk_files

	def load_unity_menu(self):
		def read_entry(desk_file):
			if desk_file[0] == "":
				Entry = DE(desk_file[1])
				local_icon = None
			else:
				Entry = DE(desk_file[0])
				local_icon = self.load_icon("user-home")
			return Entry, local_icon

		menus = {
		"Accessories":				["'Utility' in categories and not 'Accessibility' in categories", "['Utility']", "['Accessibility']"],
		"Education":				["'Education' in categories and not 'Science' in categories", "['Education']", "['Science']"],
		"Games":					["'Game' in categories", "['Game']", "[]"],
		"Graphics":					["'Graphics' in categories", "['Graphics']", "[]"],
		"Internet":					["'Network' in categories", "['Network']", "[]"],
		"Fonts":					["'Fonts' in categories", "['Fonts']", "[]"],
		"Office":					["'Office' in categories", "['Office']", "[]"],
		"Media":					["'AudioVideo' in categories", "['AudioVideo']", "[]"],
		"Customization":			["'Settings' in categories", "['Settings']", "[]"],
		"Accessibility":			["'Accessibility' in categories and not 'Settings' in categories", "['Accessibility']", "['Settings']"],
		"Developer":				["'Development' in categories", "['Development']", "[]"],
		"Science & Engineering":	["'Science' in categories or 'Engineering' in categories", "['Science', 'Engineering']", "[]"],
		"System":					["'System' in categories or 'Security' in categories", "['System', 'Security']", "[]"]
		}

		try: self.menu = parse("unity-lens-applications.menu")
		except: self.menu = parse()
		desk_files = self.load_deskfiles()
		gettext.textdomain('unity')
		menuName = "All"
		rootiter = self.deskstore.append(None, [_(menuName), "0", self.load_icon("applications-other"), "", "", None, True, False, _(menuName)])
		for desk_file in desk_files:
			try:
				Entry, local_icon = read_entry(desk_file)
				try: name = self.getMenuEntry(self.menu, self.DesktopFileID(Entry.filename)).DesktopEntry.getName()
				except: name = Entry.getName()
				treeiter = self.deskstore.append(rootiter,[name, name, self.load_icon(Entry.getIcon()), desk_file[0], desk_file[1], local_icon, not Entry.getNoDisplay(), True, self.DesktopFileID(Entry.filename)])
			except: pass
		gettext.textdomain('unity-lens-applications')
		for menuName in menus:
			self.categstore.append([False, _(menuName), menus[menuName][0], menus[menuName][1], menus[menuName][2]])
			menuiter = self.deskstore.append(None, [_(menuName), _(menuName), self.load_icon("applications-other"), "", "", None, True, False, _(menuName)])
			for desk_file in desk_files:
				try:
					Entry, local_icon = read_entry(desk_file)
					categories = Entry.getCategories()
					if eval(menus[menuName][0]): treeiter = self.deskstore.append(menuiter, [Entry.getName(), Entry.getName(), self.load_icon(Entry.getIcon()), desk_file[0], desk_file[1], local_icon, not Entry.getNoDisplay(), True, self.DesktopFileID(Entry.filename)])
				except: pass
		gettext.textdomain(LOCALE_DOMAIN)
		self.deskstore.set_sort_column_id(1, Gtk.SortType.ASCENDING)

	def __init__(self):
		builder = Gtk.Builder()
		builder.set_translation_domain(LOCALE_DOMAIN)
		builder.add_from_file(glade_path)
		self.load_objects(builder)
		self.load_prefs()
		self.load_signals()
		self.Entry = None
		self.window.show()
		self.load_menu()
		self.disable_all()

class NewEntry:
	def __init__(self):
		builder = Gtk.Builder()
		builder.set_translation_domain(LOCALE_DOMAIN)
		builder.add_from_file(glade_path)
		self.Winput = builder.get_object("Winput")
		self.Binputok = builder.get_object("Binputok")
		self.Einputfile = builder.get_object("Einputfile")
		self.Cinputtype = builder.get_object("Cinputtype")
		self.id_Einputfile_changed = self.Einputfile.connect("changed", self.on_Einputfile_changed)

	def on_Einputfile_changed(self, obj):
		self.Binputok.set_sensitive(not self.Einputfile.get_text() == "")

class NewAction:
	def __init__(self):
		builder = Gtk.Builder()
		builder.set_translation_domain(LOCALE_DOMAIN)
		builder.add_from_file(glade_path)
		self.Waction = builder.get_object("Waction")
		self.Bactionok = builder.get_object("Bactionok")
		self.Eaction = builder.get_object("Eaction")
		self.id_Eaction_changed = self.Eaction.connect("changed", self.on_Eaction_changed)

	def on_Eaction_changed(self, obj):
		self.Bactionok.set_sensitive(not self.Eaction.get_text() == "")

class Preferences:
	def __init__(self):
		builder = Gtk.Builder()
		builder.set_translation_domain(LOCALE_DOMAIN)
		builder.add_from_file(glade_path)
		self.Wpreferences = builder.get_object("Wpreferences")
		self.Rubuntu = builder.get_object("Rubuntu")
		self.Rclassic = builder.get_object("Rclassic")
		self.Rcinnamon = builder.get_object("Rcinnamon")
		self.Rxfce = builder.get_object("Rxfce")
		self.Rlxde = builder.get_object("Rlxde")

class Loading:
	def __init__(self):
		builder = Gtk.Builder()
		builder.set_translation_domain(LOCALE_DOMAIN)
		builder.add_from_file(glade_path)
		self.Wloading = builder.get_object("Wloading")

if __name__ == "__main__":
	app = Ezame()
	Gtk.main()
	
