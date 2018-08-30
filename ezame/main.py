#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, fnmatch
import xml.etree.ElementTree as ET
import subprocess, tempfile
import gettext
from gi.repository import Gtk, Gdk, GdkPixbuf, Pango
from configparser import ConfigParser
local = (len(sys.argv) > 1) and (sys.argv[1] == "local")
if local:
	from desktop import DE
	glade_path = "ezame.glade"
else:
	from ezame.desktop import DE
	glade_path = os.path.join(sys.prefix, "share", "ezame", "ezame.glade")
LOCALE_DOMAIN = "ezame"
gettext.textdomain(LOCALE_DOMAIN)
_ = gettext.gettext

#files
i_filename = 0
i_local = 1
i_system = 2

#desktop
d_item = 0
d_sort = 1
d_icon = 2
d_local_path = 3
d_system_path = 4
d_local_icon = 5
d_display = 6
d_display_visible = 7
d_menu_name = 8

class MyTreeBuilder(ET.TreeBuilder):
	def __init__(self):
		self.start("root", {})
	def comment(self, data):
		self.start(ET.Comment, {})
		self.data(data)
		self.end(ET.Comment)

class MyElementBuilder(ET.TreeBuilder):
	def comment(self, data):
		self.start(ET.Comment, {})
		self.data(data)
		self.end(ET.Comment)

class Ezame(object):

	def prettystring(self, tree, level=0):
		def indent(elem, level=0):
			i = "\n" + level*"\t"
			if len(elem):
				if not elem.text or not elem.text.strip():
					try: n = elem.text.count("\n")
					except:
						n = 1
						pass
					elem.text = n* "\n" + (level + 1)*"\t"
				if not elem.tail or not elem.tail.strip():
					try: n = elem.tail.count("\n")
					except:
						n = 1
						pass
					elem.tail = n* "\n" + level*"\t"
				for elem in elem:
					indent(elem, level+1)
				if not elem.tail or not elem.tail.strip():
					try: n = elem.tail.count("\n")
					except:
						n = 1
						pass
					elem.tail = n* "\n" + level*"\t"
			else:
				if level and (not elem.tail or not elem.tail.strip()):
					try: n = elem.tail.count("\n")
					except:
						n = 1
						pass
					elem.tail = n* "\n" + level*"\t"

		elem = ET.XML(ET.tostring(tree, encoding = "unicode"), parser=ET.XMLParser(target=MyElementBuilder()))
		indent(elem)
		return '\n'.join(line[1:] for line in ET.tostring(elem, encoding="unicode").split('\n')[1:-2]) 

	def gtk_main_quit(self, *args):
		self.config["window"] = {"width": self.window.get_size()[0], "height": self.window.get_size()[1]}
		self.config["paned"] = {"position": self.paned.get_position()}
		if not os.path.exists(os.path.dirname(self.config_file)): os.mkdir(os.path.dirname(self.config_file))
		with open(self.config_file, "w") as config_file: self.config.write(config_file)
		self.desktree.disconnect(self.id_desktree_cursor_changed)
		Gtk.main_quit(*args)

	def on_Ruser_clicked(self, obj):
		if obj.get_active():
			if self.deskstore[self.desktree.get_cursor()[0]][d_local_path] == "":
				dirs = []
				subdir = ""
				if "/applications/" in self.deskstore[self.desktree.get_cursor()[0]][d_system_path]: folder = "applications"
				else: folder = "desktop-directories"
				head, filename = os.path.split(self.deskstore[self.desktree.get_cursor()[0]][d_system_path])
				head, tail = os.path.split(head)
				while tail != folder:
					dirs.insert(0, tail)
					head, tail = os.path.split(head)
				if dirs: subdir = os.sep.join(dirs)
				directory = os.path.join(self.data_home, folder, subdir)
				if not os.path.exists(directory): os.makedirs(directory)
				new_file = os.path.join(directory, os.path.basename(self.deskstore[self.desktree.get_cursor()[0]][d_system_path]))
				self.Entry.write(new_file)
				self.deskstore[self.desktree.get_cursor()[0]][d_local_path] = new_file
				self.deskstore[self.desktree.get_cursor()[0]][d_local_icon] = self.load_icon("user-home")
				self.change_tree("update")
			self.update_info()

	def on_Rsystem_clicked(self, obj):
		if obj.get_active():
			self.update_info()

	def on_Bundo_clicked(self, obj):
		if self.pagenum < 4:
			menu_string = self.config.get("menus", self.menu_filename)
			td = tempfile.TemporaryDirectory()
			f = open(os.path.join(td.name, os.path.basename(self.menu_filename)), "w")
			f.write(menu_string)
			f.close()
			command = ["cp", f.name, self.menu_filename]
			p = subprocess.Popen(command)
			if p.wait() != 0:
				command = ["pkexec", "cp", f.name, self.menu_filename]
				p = subprocess.Popen(command)
				p.wait()
			self.load_menu()
		else:
			self.update_info()

	def on_Bsave_clicked(self, obj):
		if self.pagenum < 4:
			self.on_menu_view_focus_out_event(self.menu_view, None)
			self.on_menu_view_focus_out_event(self.appdir_view, None)
			self.on_menu_view_focus_out_event(self.directorydir_view, None)
			self.on_menu_view_focus_out_event(self.mergedir_view, None)
			self.on_menu_view_focus_out_event(self.mergefile_view, None)
			self.on_menu_view_focus_out_event(self.legacydir_view, None)
			self.on_menu_view_focus_out_event(self.include_view, None)
			self.on_menu_view_focus_out_event(self.exclude_view, None)
			self.on_menu_view_focus_out_event(self.defaultlayout_view, None)
			self.on_menu_view_focus_out_event(self.layout_view, None)
			
			menu_string ="<!DOCTYPE Menu PUBLIC \"-//freedesktop//DTD Menu 1.0//EN\"\n \"http://www.freedesktop.org/standards/menu-spec/1.0/menu.dtd\">\n\n" + self.prettystring(self.menu.getroot())
			td = tempfile.TemporaryDirectory()
			f = open(os.path.join(td.name, os.path.basename(self.menu_filename)), "w")
			f.write(menu_string)
			f.close()
			command = ["cp", f.name, self.menu_filename]
			p = subprocess.Popen(command)
			if p.wait() != 0:
				command = ["pkexec", "cp", f.name, self.menu_filename]
				p = subprocess.Popen(command)
				p.wait()
		else:
			if self.buffer_changed: self.on_desktop_view_focus_out_event(None, None)
			r = self.Entry.write()
			if r:
				md = Gtk.MessageDialog(type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE)
				md.set_property("text", r)
				md.run()
				md.destroy()
			self.update_info()

	def on_Entry_changed(self, obj):
		if obj.is_focus():
			locale = getattr(obj, "locale", False)
			group = getattr(obj, "group", None)
			self.Entry.set(obj.key, obj.get_text(), group, locale)
			self.update_objects()

	def on_Switch_notify(self, obj, active):
		if self.Entry:
			self.Entry.set(obj.key, str(obj.get_active()).lower())
			self.update_objects()

	def on_menu_Entry_changed(self, obj):
		if obj.is_focus():
			tag = getattr(obj, "tag", None)
			try:
				self.selected_menu.find(tag).text=obj.get_text()
				if tag == "Name": self.deskstore[self.desktree.get_cursor()[0]][d_menu_name] = obj.get_text()
			except: pass
			self.update_menu_objects()

	def on_menu_Switch_notify(self, obj, active):
		if obj.get_active():
			if self.selected_menu.find(obj.tag) == None: ET.SubElement(self.selected_menu, obj.tag)
		else:
			for el in self.selected_menu.findall(obj.tag): self.selected_menu.remove(el)
		self.update_menu_objects()

	def on_Bactionadd_clicked(self, obj):
		dialog = NewAction()
		dialog.Waction.set_transient_for(self.window)
		response = dialog.Waction.run()
		if response == Gtk.ResponseType.OK:
			dialog.Waction.hide()
			action = dialog.Eaction.get_text()
			self.Entry.content.add_section(" ".join(("Desktop Action", action)))
			actions = self.Entry.getlist("Actions")
			actions.append(action)
			self.Entry.set("Actions", ";".join(actions))	
		dialog.Waction.destroy()
		self.update_objects(True, True)

	def on_Bactionremove_clicked(self, obj):
		try:
			sel_action = self.Nactions.get_tab_label_text(self.Nactions.get_nth_page(self.Nactions.get_current_page()))
			self.Entry.content.remove_section(" ".join(("Desktop Action", sel_action)))
			actions = self.Entry.getlist("Actions")
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
		gettext.textdomain(LOCALE_DOMAIN)
		dialog = Gtk.FileChooserDialog(obj.msg, self.window, obj.action, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
		if obj == self.Bicon: add_filters(dialog)
		response = dialog.run()
		if response == Gtk.ResponseType.OK:
			obj.entry.grab_focus()
			obj.entry.set_text(dialog.get_filename())
		dialog.destroy()

	def on_categtreecellrenderertoggle_toggled(self, cell, path, model, *ignore):
		model[model.get_iter(path)][0] = not model[model.get_iter(path)][0]
		categories = self.Entry.getlist("Categories")
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
		if len(categories) == 0:
			self.Entry.set("Categories","")			
		else:
			self.Entry.set("Categories",";".join(categories)+";")			
		self.update_objects()

	def save_des(self):
		if self.Ronlyshowin.get_active():
			show_selected = "OnlyShowIn"
			show_removed = "NotShowIn"
		else:
			show_selected = "NotShowIn"
			show_removed = "OnlyShowIn"
		showin = ";".join(row[1] for row in self.destore if row[0]) + ";"
		if showin == ";":
			showin = "";
		self.Entry.set(show_selected, showin)
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
				if self.deskstore[treeiter][d_local_path] == filename:
					found = treeiter
					break
				treeiter = self.deskstore.iter_next(treeiter)
			return found
		gettext.textdomain(LOCALE_DOMAIN)
		dialog = NewEntry()
		dialog.Winput.set_transient_for(self.window)
		if self.desktop == "Menu":
			dialog.Winput.set_title(_("New Directory"))
			dialog.Cinputtype.append_text(_("Directory"))
		else:
			dialog.Cinputtype.append_text(_("Application"))
			dialog.Cinputtype.append_text(_("Link"))
		dialog.Cinputtype.set_active(0)
		response = dialog.Winput.run()
		if response == Gtk.ResponseType.OK:
			dialog.Winput.hide()
			filetype = dialog.Cinputtype.get_active()
			if self.desktop == "Menu":
				ext = "directory"
				type = "Directory"
				folder = "desktop-directories"
				item = self.selected_menu
				tree = ET.fromstring("".join(["<a><Menu><Name>",os.path.splitext(os.path.basename(dialog.Einputfile.get_text()))[0],"</Name><Directory>",os.path.splitext(os.path.basename(dialog.Einputfile.get_text()))[0] + "." + ext,"</Directory></Menu></a>"]))
				for node in tree:
					item.append(node)
				self.on_Bsave_clicked(None)
			else:	
				if filetype == 0:
					ext = "desktop"
					type = "Application"
					folder = "applications"
				else:
					ext = "desktop"
					type = "Link"
					folder = "applications"
			filename = os.path.join(os.path.join(self.data_home, folder), os.path.splitext(os.path.basename(dialog.Einputfile.get_text()))[0] + "." + ext)
			self.Entry = DE(filename)
			self.Entry.set("Name", os.path.splitext(os.path.basename(dialog.Einputfile.get_text()))[0])
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
		os.remove(self.deskstore[self.desktree.get_cursor()[0]][d_local_path])
#		if self.desktop == "Menu":			
#			item = self.selected_menu
#			item.clear() #Not working - <Menu /> stays
#			self.on_Bsave_clicked(None)
		if not(self.desktop == "Menu"):
			if self.deskstore[self.desktree.get_cursor()[0]][d_system_path] == "":
				self.change_tree("delete")
			else:
				self.deskstore[self.desktree.get_cursor()[0]][d_local_path] = ""
				self.deskstore[self.desktree.get_cursor()[0]][d_local_icon] = None
				self.change_tree("update")
		self.update_info()

	def on_Mvalidate_activate(self, obj):
		command = ["desktop-file-validate", self.Entry.filename]
		p = subprocess.Popen(command, stdout=subprocess.PIPE)
		if p.wait() == 0:
			r = _("No Warnings")
		else:
			r = '\n'.join(line.split(": ", maxsplit=1)[-1] for line in p.communicate()[0].decode("utf-8").split('\n'))
		md = Gtk.MessageDialog(type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.CLOSE)
		md.set_property("text", r)
		md.run()
		md.destroy()

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
		dialog.Rubuntu.set_visible(os.environ.get('XDG_CURRENT_DESKTOP') == "Unity")
		if self.desktop == "Unity": dialog.Rubuntu.set_active(True)
		elif self.desktop == "Apps": dialog.Rapps.set_active(True)
		else: dialog.Rmenu.set_active(True)
		response = dialog.Wpreferences.run()
		if response == Gtk.ResponseType.OK:
			if dialog.Rubuntu.get_active(): self.desktop = "Unity"
			elif dialog.Rapps.get_active(): self.desktop = "Apps"
			else: self.desktop = "Menu"
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
		if self.desktop_view.is_focus(): self.buffer_changed = True

	def on_menu_buffer_changed(self, obj):
		if obj.view.is_focus(): obj.view.buffer_changed = True

	def on_desktop_view_focus_out_event(self, obj, event):
		if self.buffer_changed:
			self.Entry.content.clear()
			self.Entry.read_string(self.desktop_buffer.get_text(self.desktop_buffer.get_start_iter(), self.desktop_buffer.get_end_iter(), False))
			self.update_objects(False, True)

	def on_menu_view_focus_out_event(self, obj, event):
		if obj.buffer_changed:
			tag = getattr(obj, "tag", None)
			obj_buffer = obj.get_buffer()
			if tag in ["Include", "Exclude", "Layout", "DefaultLayout"]:
				try: item = self.selected_menu.findall(tag)[-1]
				except:
					item = ET.SubElement(self.selected_menu, tag)
					pass
				#catch = self.selected_menu.find(tag)
				tree = ET.fromstring("".join(["<a>",obj_buffer.get_text(obj_buffer.get_start_iter(), obj_buffer.get_end_iter(), False),"</a>"]))
				#root = tree.getroot()
				item.clear()
				for node in tree:
					item.append(node)
				#except: pass
			elif tag == "MenuEditor":
				tree = ET.fromstring("".join(["<a>",obj_buffer.get_text(obj_buffer.get_start_iter(), obj_buffer.get_end_iter(), False),"</a>"]))
				self.selected_menu.clear()
				for node in tree:
					self.selected_menu.append(node)				
			else:
				tags = self.selected_menu.findall(tag)
				tags_text = [line.strip() for line in obj_buffer.get_text(obj_buffer.get_start_iter(), obj_buffer.get_end_iter(), False).split("\n")]
				for text in tags_text:
					try:
						tags[tags_text.index(text)].text = text
					except:
						item = ET.SubElement(self.selected_menu, tag)
						item.text = text
						pass

			obj.buffer_changed = False
			self.update_menu_objects()

	def on_notebook_switch_page(self, widget, dummy, pagenum):
		self.pagenum = pagenum
		self.update_objects()

	def on_desktree_cursor_changed(self, widget):
		self.desktree.grab_focus()
		if self.deskstore[self.desktree.get_cursor()[0]][d_local_path] == "":
			self.Rsystem.set_active(True)
		else:
			self.Ruser.set_active(True)
		self.update_info()

	def update_info(self):
		if self.menu:
			if not self.deskstore[self.desktree.get_cursor()[0]][d_menu_name]: self.Entry = None
			node = self.deskstore.get_iter([self.desktree.get_cursor()[0]])
			while self.deskstore.iter_parent(node): #or self.deskstore[parent][d_menu_name]:
				node = self.deskstore.iter_parent(node)
			if self.menu_filename != self.deskstore[node][d_system_path]:
				self.menu_filename = self.deskstore[node][d_system_path]
				self.menu = ET.parse(self.menu_filename, parser=ET.XMLParser(target=MyTreeBuilder()))
				self.menu.getroot().set("filename", self.deskstore[node][d_system_path])
			if not self.deskstore[self.desktree.get_cursor()[0]][d_menu_name]:
				self.selected_menu = self.menu.getroot()
			else:
				for menu in self.menu.iter("Menu"):
					try:
						if menu.find("Name").text == self.deskstore[self.desktree.get_cursor()[0]][d_menu_name]:
							self.selected_menu = menu
					except: pass
			self.update_menu_objects()
		if not self.menu or self.deskstore[self.desktree.get_cursor()[0]][d_menu_name]:# != None:
			if self.Rsystem.get_active():
				desktop_file_path = self.deskstore[self.desktree.get_cursor()[0]][d_system_path]
			else:
				desktop_file_path = self.deskstore[self.desktree.get_cursor()[0]][d_local_path]
			self.Rsystem.set_sensitive(not self.deskstore[self.desktree.get_cursor()[0]][d_system_path] == "")
			if desktop_file_path == "": self.Entry = None
			else: self.Entry = DE(desktop_file_path)
		self.update_objects(True, True)

	#def getMenu(self, menu, path):
		#array = path.split("/", 1)
		#for submenu in menu.Submenus:
			#if (submenu.getName()) == array[0]:
				#if len(array) > 1:
					#return self.getMenu(submenu, array[1])
				#else:
					#return submenu

	def update_objects(self, update_editor=True, update_actions=False):
		def insert_action(self, group):
			gettext.textdomain(LOCALE_DOMAIN)
			label = Gtk.Label(" ".join(group.split()[2:]))
			Laname = Gtk.Label(_("Name"), halign=Gtk.Align.START)
			Laexec = Gtk.Label(_("Exec"), halign=Gtk.Align.START)
			Laicon = Gtk.Label(_("Icon"), halign=Gtk.Align.START)
			Eaname = Gtk.Entry()
			Eaname.key = "Name"
			Eaname.group = group
			Eaname.locale = True
			Eaname.set_hexpand(True)
			Eaname.set_text(self.Entry.get("Name", group, locale = True))
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
			Eaicon.set_text(self.Entry.get("Icon", group, locale = True))
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
		
		def enable_all(self):
			self.scrolledwindoweditor.set_sensitive(True)
			self.scrolledwindowmore.set_sensitive(True)
			self.scrolledwindowprop.set_sensitive(True)
			self.categtree.set_sensitive(True)
			self.gridshow.set_sensitive(True)
			self.Rnotshowin.set_sensitive(True)
			self.Ronlyshowin.set_sensitive(True)			
			#self.Box_buttons.set_sensitive(True)
			self.Ruser.set_sensitive(True)
			self.Rsystem.set_sensitive(True)
			self.Bundo.set_sensitive(True)
			self.Bsave.set_sensitive(True)
			self.Mundo.set_sensitive(True)
			self.Msave.set_sensitive(True)
			app = self.Entry.get("Type") == "Application"
			link = self.Entry.get("Type") == "Link"
			self.scrolledwindowactions.set_sensitive(app)
			self.Eurl.set_visible(link)
			self.Lurl.set_visible(link)
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
			self.gridshow.set_sensitive(False)
			self.Rnotshowin.set_sensitive(False)
			self.Ronlyshowin.set_sensitive(False)
			#self.Box_buttons.set_sensitive(False)			
			self.Ruser.set_sensitive(False)
			self.Rsystem.set_sensitive(False)
			self.Bundo.set_sensitive(False)
			self.Bsave.set_sensitive(False)
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

		if not self.Entry:
			disable_all(self)
		else:
			self.buffer_changed = False
			Entry = self.Entry
			enable_all(self)
			self.Mdelete.set_sensitive(self.Ruser.get_active())
			self.Efile.set_text(Entry.filename)
			gettext.textdomain(LOCALE_DOMAIN)		
			self.Ltype.set_text(_(Entry.get("Type"))) #translate Application/Directory
			self.Ename.set_text(Entry.get("Name", locale = True))
			self.Egenericname.set_text(Entry.get("GenericName", locale = True))
			self.Snodisplay.set_active(Entry.getboolean("NoDisplay"))
			try: self.deskstore[self.desktree.get_cursor()[0]][d_item] = Entry.get("Name", locale = True)
			except: pass
			try: self.deskstore[self.desktree.get_cursor()[0]][d_icon] = self.load_icon(Entry.get("Icon", locale = True))
			except: pass
			try: self.deskstore[self.desktree.get_cursor()[0]][d_display] = not self.Snodisplay.get_active()
			except: pass
			self.Eexec.set_text(Entry.get("Exec"))
			self.Epath.set_text(Entry.get("Path"))
			self.Eicon.set_text(Entry.get("Icon", locale = True))
			self.Ecomment.set_text(Entry.get("Comment", locale = True))
			self.Eurl.set_text(Entry.get("URL"))

			categories = Entry.getlist("Categories")
			for row in self.categstore: row[0] = eval(row[2])

			if Entry.getlist("NotShowIn"):
				self.Rnotshowin.set_active(True)
				des = Entry.getlist("NotShowIn")
			elif Entry.getlist("OnlyShowIn"):
				self.Ronlyshowin.set_active(True)
				des = Entry.getlist("OnlyShowIn")
			else:
				self.Ronlyshowin.set_active(True) 
				des = []
			self.destore.clear()
			for de in self.de_list: self.destore.append([False, de])
			for de in des:
				exist = False
				for row in self.destore:
					if de == row[1]: exist = True
				if not exist: self.destore.append([False, de])
			for row in self.destore: row[0] = row[1] in des

			self.Eversion.set_text(Entry.get("Version"))
			self.Shidden.set_active(Entry.getboolean("Hidden"))
			self.Etryexec.set_text(Entry.get("TryExec"))
			self.Sterminal.set_active(Entry.getboolean("Terminal"))
			self.Emimetypes.set_text(Entry.get("MimeType"))
			self.Ekeywords.set_text(Entry.get("Keywords", locale = True))
			self.Sstartupnotify.set_active(Entry.getboolean("StartupNotify"))
			self.Estartupwmclass.set_text(Entry.get("StartupWMClass"))

			if update_editor:
				if hasattr(Entry, 'faulty_text'):
					self.desktop_buffer.set_text(Entry.faulty_text)
					self.Ltype.set_text("")
					self.scrolledwindowactions.set_sensitive(False)
					self.scrolledwindowmore.set_sensitive(False)
					self.scrolledwindowprop.set_sensitive(False)
					self.categtree.set_sensitive(False)
					self.gridshow.set_sensitive(False)
				else:
					try:
						self.desktop_buffer.set_text(Entry.as_string())
					except: pass
				
			if update_actions:
				for child in self.Nactions.get_children(): self.Nactions.remove(child)
				for group in self.Entry.items():
					if "Desktop Action" in group:
						insert_action(self, group)
				self.Nactions.show_all()
		if self.pagenum < 4:
			self.Ruser.set_sensitive(False)
			self.Rsystem.set_sensitive(False)
			self.Bundo.set_sensitive(True)
			self.Bsave.set_sensitive(True)
			self.Mundo.set_sensitive(True)
			self.Msave.set_sensitive(True)

	def update_menu_objects(self):
		def disable_menu_objects(self):
			self.scrolledwindowmenu.set_sensitive(False)
			self.scrolledwindowinclude.set_sensitive(False)
			self.scrolledwindowlayout.set_sensitive(False)
			#self.scrolledwindowmenueditor.set_sensitive(False)		

		if not self.menu:
			disable_menu_objects(self)
		else:
			self.scrolledwindowmenu.set_sensitive(True)
			self.scrolledwindowinclude.set_sensitive(True)
			self.scrolledwindowlayout.set_sensitive(True)
			#self.scrolledwindowmenueditor.set_sensitive(True)
			try:self.Emfile.set_text(self.menu.getroot().get("filename"))
			except: pass
			try:self.Emname.set_text(self.selected_menu.findtext("Name"))
			except:
				self.Emname.set_text("")
				pass
			try: self.Emdirectory.set_text(self.selected_menu.findall("Directory")[-1].text)
			except:
				self.Emdirectory.set_text("")
				pass
			try: self.Sdefaultappdirs.set_active(self.selected_menu.find("DefaultAppDirs") != None)
			except:
				self.Sdefaultappdirs.set_active(False)
				pass
			try: self.Sdefaultdirectorydirs.set_active(self.selected_menu.find("DefaultDirectoryDirs") != None)
			except:
				self.Sdefaultdirectorydirs.set_active(False)
				pass
			try: self.Sdefaultmergedirs.set_active(self.selected_menu.find("DefaultMergeDirs") != None)
			except:
				self.Sdefaultmergedirs.set_active(False)
				pass
			try: self.Skdelegacydirs.set_active(self.selected_menu.find("KDELegacyDirs") != None)
			except:
				self.Skdelegacydirs.set_active(False)
				pass
			try: self.Sonlyunallocated.set_active(self.selected_menu.find("OnlyUnallocated") != None)
			except:
				self.Sonlyunallocated.set_active(False)
				pass
			try: self.appdir_buffer.set_text("\n".join(elem.text for elem in self.selected_menu.findall("AppDir")))
			except:
				self.appdir_buffer.set_text("")
				pass
			try: self.directorydir_buffer.set_text("\n".join(elem.text for elem in self.selected_menu.findall("DirectoryDir")))
			except:
				self.directorydir_buffer.set_text("")
				pass
			try: self.mergedir_buffer.set_text("\n".join(elem.text for elem in self.selected_menu.findall("MergeDir")))
			except:
				self.mergedir_buffer.set_text("")
				pass
			try: self.mergefile_buffer.set_text("\n".join(elem.text for elem in self.selected_menu.findall("MergeFile")))
			except:
				self.mergefile_buffer.set_text("")
				pass
			try: self.legacydir_buffer.set_text("\n".join(elem.text for elem in self.selected_menu.findall("LegacyDir")))
			except:
				self.legacydir_buffer.set_text("")
				pass
			self.include_buffer.set_text("")
			try:
				root = self.selected_menu.findall("Include")[-1]
				self.include_buffer.set_text(self.prettystring(root))
				#for node in root:
				#	self.include_buffer.insert(self.include_buffer.get_end_iter(), ET.tostring(node, encoding="unicode"))
			except:
				pass
			self.exclude_buffer.set_text("")
			try:
				root = self.selected_menu.findall("Exclude")[-1]
				self.exclude_buffer.set_text(self.prettystring(root))
				#for node in root:
				#	self.exclude_buffer.insert(self.exclude_buffer.get_end_iter(), ET.tostring(node, encoding="unicode"))
			except:
				pass
			self.layout_buffer.set_text("")
			try:
				root = self.selected_menu.findall("Layout")[-1]
				self.layout_buffer.set_text(self.prettystring(root))
				#for node in root:
				#	self.layout_buffer.insert(self.layout_buffer.get_end_iter(), ET.tostring(node, encoding="unicode"))
			except:
				pass
			self.defaultlayout_buffer.set_text("")
			try:
				root = self.selected_menu.findall("DefaultLayout")[-1]
				self.defaultlayout_buffer.set_text(self.prettystring(root))
				#for node in root:
				#	self.defaultlayout_buffer.insert(self.defaultlayout_buffer.get_end_iter(), ET.tostring(node, encoding="unicode"))
			except:
				pass
			self.menu_buffer.set_text("")
			if self.selected_menu.tag == "Menu":
				self.menu_buffer.set_text(self.prettystring(self.selected_menu))
			else:
				self.menu_buffer.set_text(self.prettystring(self.menu.getroot()))
				disable_menu_objects(self)
				self.scrolledwindowmenueditor.set_sensitive(True)

	def change_tree(self, action):
		def iterate(treeiter, filename, action):
			while treeiter != None:
				deleted = False
				if self.deskstore.iter_has_child(treeiter):
					childiter = self.deskstore.iter_children(treeiter)
					iterate(childiter, filename, action)
				if self.deskstore[treeiter][d_local_path] == filename or self.deskstore[treeiter][d_system_path] == filename:
					if action == "update":
						self.deskstore[treeiter] = self.deskstore[self.desktree.get_cursor()[0]][:]
					elif action == "delete":
						self.deskstore.remove(treeiter)
						deleted = True
				if not deleted: treeiter = self.deskstore.iter_next(treeiter)

		path = self.desktree.get_cursor()[0]
		rootiter = self.deskstore.get_iter_first()
		if self.deskstore[self.desktree.get_cursor()[0]][d_system_path] == "": 
			filename = self.deskstore[self.desktree.get_cursor()[0]][d_local_path]
		else:
			filename = self.deskstore[self.desktree.get_cursor()[0]][d_system_path]
		iterate(rootiter, filename, action)
		try: self.desktree.set_cursor(path)
		except: pass

	def read_entry(self, desk_file):
		if desk_file[i_local] == "":
			Entry = DE(desk_file[i_system])
			local_icon = None
		else:
			Entry = DE(desk_file[i_local])
			local_icon = self.load_icon("user-home")
		return Entry, local_icon

	def load_icon(self, icon):
		pixbuf = None
		if self.default_theme.lookup_icon(icon, self.icon_size, 0):
			try: pixbuf = self.default_theme.load_icon(icon, self.icon_size, 0).scale_simple(self.icon_size, self.icon_size, GdkPixbuf.InterpType.BILINEAR)
			except: pixbuf = None
		elif os.path.isfile(icon):
			try: pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon).scale_simple(self.icon_size, self.icon_size, GdkPixbuf.InterpType.BILINEAR)
			except: pixbuf = None
		else:
			try:
				for path in self.xdg_data_dirs:
					for folder in ("pixmaps", "app-install/icons"):
						icon_path = os.path.join(path, folder, icon)
						if os.path.isfile(icon_path):
							try: pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_path).scale_simple(self.icon_size, self.icon_size, GdkPixbuf.InterpType.BILINEAR)
							except: pixbuf = None
							raise
			except: pass
		return pixbuf

	def load_menu(self):
		def load_unity_menu(self):
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

			desk_files = self.load_deskfiles()
			gettext.textdomain("unity")
			menuname = "All"
			rootiter = self.deskstore.append(None, [_(menuname), "0", self.load_icon("applications-other"), "", "", None, True, False, _(menuname)])
			for desk_file in desk_files:
				try:
					Entry, local_icon = self.read_entry(desk_file)
					name = Entry.get("Name", locale = True)
					treeiter = self.deskstore.append(rootiter,[name, name, self.load_icon(Entry.get("Icon", locale = True)), desk_file[i_local], desk_file[i_system], local_icon, not Entry.getboolean("NoDisplay"), True, desk_file[i_filename]])
				except: pass
			for menuname in menus:
				gettext.textdomain("unity-lens-applications")
				self.categstore.append([False, _(menuname), menus[menuname][0], menus[menuname][1], menus[menuname][2]])
				menuiter = self.deskstore.append(None, [_(menuname), _(menuname), self.load_icon("applications-other"), "", "", None, True, False, _(menuname)])
				for desk_file in desk_files:
					try:
						Entry, local_icon = self.read_entry(desk_file)
						categories = Entry.getlist("Categories")
						if eval(menus[menuname][0]): treeiter = self.deskstore.append(menuiter, [Entry.get("Name", locale = True), Entry.get("Name", locale = True), self.load_icon(Entry.get("Icon", locale = True)), desk_file[i_local], desk_file[i_system], local_icon, not Entry.getboolean("NoDisplay"), True, desk_file[i_filename]])
					except: pass
			gettext.textdomain(LOCALE_DOMAIN)
			self.deskstore.set_sort_column_id(1, Gtk.SortType.ASCENDING)

		def load_apps(self):
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

			desk_files = self.load_deskfiles()
			for desk_file in desk_files:
				try:
					Entry, local_icon = self.read_entry(desk_file)
					name = Entry.get("Name", locale = True)
					treeiter = self.deskstore.append(None,[name, name, self.load_icon(Entry.get("Icon", locale = True)), desk_file[i_local], desk_file[i_system], local_icon, not Entry.getboolean("NoDisplay"), True, desk_file[i_filename]])
				except: pass
			for menuname in menus:
				gettext.textdomain("unity-lens-applications")
				self.categstore.append([False, _(menuname), menus[menuname][0], menus[menuname][1], menus[menuname][2]])
			gettext.textdomain(LOCALE_DOMAIN)
			self.deskstore.set_sort_column_id(1, Gtk.SortType.ASCENDING)

		def load_freedesktop(self):
			def load_dirfiles(self):
				dirfilenames = []
				dir_system = []
				dir_user = []
				dir_files = []
				for data_dir in self.xdg_data_dirs:
					data_dir = os.path.join(data_dir, "desktop-directories")
					if "/." in data_dir:
						for path, dirnames, filenames in os.walk(data_dir):
							for filename in fnmatch.filter(filenames, "*.directory"):
								dir_user.append(os.path.join(path, filename))
					else:
						for path, dirnames, filenames in os.walk(data_dir):
							for filename in fnmatch.filter(filenames, "*.directory"):
								dir_file = os.path.join(path, filename)
								dirfilename = os.path.basename(dir_file)
								if not dirfilename in dirfilenames:
									dir_system.append(dir_file)
									dirfilenames.append(dirfilename)
				for user_file in dir_user:
					try:
						for system_file in dir_system:
							if os.path.basename(system_file) == os.path.basename(user_file):
								dir_files.append([os.path.basename(user_file), user_file, system_file])
								dir_system.remove(system_file)
								raise
						dir_files.append([os.path.basename(user_file), user_file, ""])
					except: pass
				for system_file in dir_system: dir_files.append([os.path.basename(system_file), "", system_file])
				return dir_files

			def load_menufiles(self):
				menufilenames = []
				menu_system = []
				menu_user = []
				menu_files = []
				for data_dir in self.xdg_config_dirs:
					data_dir = os.path.join(data_dir, "menus")
					for path, dirnames, filenames in os.walk(data_dir):
						for filename in fnmatch.filter(filenames, "*.menu"):
							menu_files.append(os.path.join(path, filename))
				return menu_files

			def load_tree(root, parent):
				treeroot = None
				if root.tag == "root":
					if "/." in root.get("filename"): local_icon = self.load_icon("user-home")
					else: local_icon = None
					treeroot = self.deskstore.append(parent,[os.path.basename(root.get("filename")), os.path.basename(root.get("filename")), None, root.get("filename"), root.get("filename"), local_icon, True, False, None])
				else:
					Name = root.findtext("Name")
					Directory = None
					if root.findall("Directory"): Directory = root.findall("Directory")[-1].text
					if Directory:
						for dir_file in dir_files:
							if Directory == dir_file[i_filename]:
								try:
									Entry, local_icon = self.read_entry(dir_file)
									treeroot = self.deskstore.append(parent,[Entry.get("Name", locale = True), Entry.get("Name", locale = True), self.load_icon(Entry.get("Icon", locale = True)), dir_file[i_local], dir_file[i_system], local_icon, not Entry.getboolean("NoDisplay"), parent, Name])
								except: pass
								break
					else:
						treeroot = self.deskstore.append(parent,[Name, Name, None, "", "", None, True, parent, Name])						
				if not treeroot: treeroot = self.deskstore.append(parent,[Name, Name, None, "", "", None, True, False, Name])
				Menus = root.findall("Menu")
				for menu in Menus:
					#try:
					load_tree(menu, treeroot)
					#except:bpass
						
			menu_files = load_menufiles(self)
			dir_files = load_dirfiles(self)
			try: self.config.add_section("menus")
			except: pass
			for menu_file in menu_files:
				try:
					if not(self.config.has_option("menus", menu_file)):
						with open(menu_file, "r") as menu: data=menu.read()
						self.config.set("menus", menu_file, data)
						if not os.path.exists(os.path.dirname(self.config_file)): os.mkdir(os.path.dirname(self.config_file))
						with open(self.config_file, "w") as config_file: self.config.write(config_file)
					try:
						self.menu_filename = menu_file
						self.menu = ET.parse(self.menu_filename, parser=ET.XMLParser(target=MyTreeBuilder()))
						self.menu.getroot().set("filename", menu_file)
						load_tree(self.menu.getroot(), None)
					except: pass
				except: pass
				
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
		self.Entry = None
		self.menu = None
		self.menu_filename = None
		self.update_objects()
		self.update_menu_objects()
		if self.desktop == "Unity": load_unity_menu(self)
		elif self.desktop == "Apps": load_apps(self)
		else: load_freedesktop(self)
		self.desktree.set_model(self.deskstore)
		self.desktree.set_visible(True)
		self.desktree.thaw_child_notify()
		self.id_desktree_cursor_changed = self.desktree.connect("cursor-changed", self.on_desktree_cursor_changed)
		load.Wloading.destroy()
		self.scrolledwindowmenu.set_visible(self.menu != None)
		self.scrolledwindowinclude.set_visible(self.menu != None)
		self.scrolledwindowlayout.set_visible(self.menu != None)
		self.scrolledwindowmenueditor.set_visible(self.menu != None)
		self.categtree.set_visible(self.menu == None)
		self.scrolledwindowactions.set_visible(self.menu == None)

	def load_deskfiles(self):
		def get_desktopfileid(self, desktop_file_path):
			head, desktopfileid = os.path.split(desktop_file_path)
			while True:
				head, tail = os.path.split(head)
				if tail != "applications" and head != "": desktopfileid = tail + "-" + desktopfileid
				else: break
			return desktopfileid

		desktopfileids = []
		desk_system = []
		desk_user = []
		desk_files = []
		for data_dir in self.xdg_data_dirs:
			data_dir = os.path.join(data_dir, "applications")
			if "/." in data_dir:
				for path, dirnames, filenames in os.walk(data_dir):
					for filename in fnmatch.filter(filenames, "*.desktop"):
						desk_user.append(os.path.join(path, filename))
			else:
				for path, dirnames, filenames in os.walk(data_dir):
					for filename in fnmatch.filter(filenames, "*.desktop"):
						desk_file = os.path.join(path, filename)
						desktopfileid = get_desktopfileid(self, desk_file)
						if not desktopfileid in desktopfileids:
							desk_system.append(desk_file)
							desktopfileids.append(desktopfileid)
		for user_file in desk_user:
			try:
				for system_file in desk_system:
					if get_desktopfileid(self, system_file) == get_desktopfileid(self, user_file):
						desk_files.append([get_desktopfileid(self, user_file), user_file, system_file])
						desk_system.remove(system_file)
						raise
				desk_files.append([get_desktopfileid(self, user_file), user_file, ""])
			except: pass
		for system_file in desk_system: desk_files.append([get_desktopfileid(self, system_file), "", system_file])
		return desk_files

	def __init__(self):
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
			self.gridshow = builder.get_object("gridshow")
			self.showtree = builder.get_object("showtree")
			self.showtreeselection = builder.get_object("showtreeselection")
			self.paned = builder.get_object("paned")
			#self.desktop = builder.get_object("desktop")
			self.notebook = builder.get_object("notebook")
			self.scrolledwindowmenu = builder.get_object("scrolledwindowmenu")
			self.scrolledwindowinclude = builder.get_object("scrolledwindowinclude")
			self.scrolledwindowlayout = builder.get_object("scrolledwindowlayout")
			self.scrolledwindowmenueditor = builder.get_object("scrolledwindowmenueditor")
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
			self.Eurl.key = "URL"
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
			self.Mvalidate = builder.get_object("Mvalidate")
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
			
			self.Emfile = builder.get_object("Emfile")
			self.Emname = builder.get_object("Emname")
			self.Emname.tag = "Name"
			self.Emdirectory = builder.get_object("Emdirectory")
			self.Emdirectory.tag = "Directory"
			self.Sdefaultappdirs = builder.get_object("Sdefaultappdirs")
			self.Sdefaultappdirs.tag = "DefaultAppDirs"
			self.Sdefaultdirectorydirs = builder.get_object("Sdefaultdirectorydirs")
			self.Sdefaultdirectorydirs.tag = "DefaultDirectoryDirs"
			self.Sdefaultmergedirs = builder.get_object("Sdefaultmergedirs")
			self.Sdefaultmergedirs.tag = "DefaultMergeDirs"
			self.Skdelegacydirs = builder.get_object("Skdelegacydirs")
			self.Skdelegacydirs.tag = "KDELegacyDirs"
			self.Sonlyunallocated = builder.get_object("Sonlyunallocated")
			self.Sonlyunallocated.tag = "OnlyUnallocated"
			self.appdir_view = builder.get_object("appdir_view")
			self.appdir_view.tag = "AppDir"
			self.appdir_view.buffer_changed = False
			self.appdir_buffer = builder.get_object("appdir_buffer")
			self.appdir_buffer.view = self.appdir_view
			self.directorydir_view = builder.get_object("directorydir_view")
			self.directorydir_view.tag = "DirectoryDir"
			self.directorydir_view.buffer_changed = False
			self.directorydir_buffer = builder.get_object("directorydir_buffer")
			self.directorydir_buffer.view = self.directorydir_view
			self.mergedir_view = builder.get_object("mergedir_view")
			self.mergedir_view.tag = "MergeDir"
			self.mergedir_view.buffer_changed = False
			self.mergedir_buffer = builder.get_object("mergedir_buffer")
			self.mergedir_buffer.view = self.mergedir_view
			self.mergefile_view = builder.get_object("mergefile_view")
			self.mergefile_view.tag = "MergeFile"
			self.mergefile_view.buffer_changed = False
			self.mergefile_buffer = builder.get_object("mergefile_buffer")
			self.mergefile_buffer.view = self.mergefile_view
			self.legacydir_view = builder.get_object("legacydir_view")
			self.legacydir_view.tag = "LegacyDir"
			self.legacydir_view.buffer_changed = False
			self.legacydir_buffer = builder.get_object("legacydir_buffer")
			self.legacydir_buffer.view = self.legacydir_view
			self.include_view = builder.get_object("include_view")
			self.include_view.tag = "Include"
			self.include_view.buffer_changed = False
			self.include_buffer = builder.get_object("include_buffer")
			self.include_buffer.view = self.include_view
			self.exclude_view = builder.get_object("exclude_view")
			self.exclude_view.tag = "Exclude"
			self.exclude_view.buffer_changed = False
			self.exclude_buffer = builder.get_object("exclude_buffer")
			self.exclude_buffer.view = self.exclude_view
			self.layout_view = builder.get_object("layout_view")
			self.layout_view.tag = "Layout"
			self.layout_view.buffer_changed = False
			self.layout_buffer = builder.get_object("layout_buffer")
			self.layout_buffer.view = self.layout_view
			self.defaultlayout_view = builder.get_object("defaultlayout_view")
			self.defaultlayout_view.tag = "DefaultLayout"
			self.defaultlayout_view.buffer_changed = False
			self.defaultlayout_buffer = builder.get_object("defaultlayout_buffer")
			self.defaultlayout_buffer.view = self.defaultlayout_view
			self.menu_view = builder.get_object("menu_view")
			self.menu_view.buffer_changed = False
			self.menu_view.tag = "MenuEditor"
			self.menu_buffer = builder.get_object("menu_buffer")
			self.menu_buffer.view = self.menu_view

		def load_prefs(self):
			self.de_list = ["GNOME", "KDE",  "LXDE", "MATE", "Razor", "ROX", "TDE", "Unity", "XFCE", "Cinnamon", "Old"]
			self.desktop = os.environ.get('XDG_CURRENT_DESKTOP')
			if self.desktop != "Unity": self.desktop = "Apps"
			self.icon_size = 22

			xdg_data_home = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
			try:
				self.xdg_data_dirs = os.environ.get("XDG_DATA_DIRS").split(":") + [xdg_data_home]
			except:
				self.xdg_data_dirs = ("/usr/local/share:/usr/share").split(":") + [xdg_data_home]
				pass

			xdg_config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
			try:
				self.xdg_config_dirs = os.environ.get("XDG_CONFIG_DIRS").split(":") + [xdg_config_home]
			except:
				self.xdg_config_dirs = ["/etc/xdg"] + [xdg_config_home]
				pass
				
			self.xdg_data_dirs.reverse()
			self.xdg_config_dirs.reverse()
			self.data_home = xdg_data_home
			for path in self.xdg_data_dirs:
				if not "/." in path:
					if  os.path.isdir(os.path.join(path, "applications")) and os.path.isdir(os.path.join(path, "desktop-directories")):
						self.data_dir = path
						break

			self.default_theme = Gtk.IconTheme.get_default()
			
			for path in self.xdg_config_dirs:
				if "/." in path: self.config_file = os.path.join(os.path.join(path, "ezame"), "preferences")
			self.config = ConfigParser()
			try:
				self.config.read(self.config_file)
				self.window.resize(int(self.config.get("window","width")), int(self.config.get("window","height")))
				self.paned.set_position(int(self.config.get("paned","position")))
			except: pass

		def load_signals(self):
			self.window.connect("delete-event", self.gtk_main_quit)
			self.id_desktree_cursor_changed = self.desktree.connect("cursor-changed", self.on_desktree_cursor_changed)
			self.id_notebook_switch_page = self.notebook.connect("switch_page", self.on_notebook_switch_page)
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
			self.id_desktop_view_focus_out_event = self.desktop_view.connect("focus-out-event", self.on_desktop_view_focus_out_event)
			self.id_Ruser_clicked = self.Ruser.connect("clicked", self.on_Ruser_clicked)
			self.id_Rsystem_clicked = self.Rsystem.connect("clicked", self.on_Rsystem_clicked)
			self.id_Bundo_clicked = self.Bundo.connect("clicked", self.on_Bundo_clicked)
			self.id_Bsave_clicked = self.Bsave.connect("clicked", self.on_Bsave_clicked)
			self.id_Mnew_activate = self.Mnew.connect("activate", self.on_Mnew_activate)
			self.id_Msave_activate = self.Msave.connect("activate", self.on_Bsave_clicked)
			self.id_Mdelete_activate = self.Mdelete.connect("activate", self.on_Mdelete_activate)
			self.id_Mvalidate_activate = self.Mvalidate.connect("activate", self.on_Mvalidate_activate)
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

			self.id_Emname_changed = self.Emname.connect("changed", self.on_menu_Entry_changed)
			self.id_Emdirectory_changed = self.Emdirectory.connect("changed", self.on_menu_Entry_changed)

			self.id_Sdefaultappdirs_notify = self.Sdefaultappdirs.connect("notify::active", self.on_menu_Switch_notify)
			self.id_Sdefaultdirectorydirs_notify = self.Sdefaultdirectorydirs.connect("notify::active", self.on_menu_Switch_notify)
			self.id_Sdefaultmergedirs_notify = self.Sdefaultmergedirs.connect("notify::active", self.on_menu_Switch_notify)
			self.id_Skdelegacydirs_notify = self.Skdelegacydirs.connect("notify::active", self.on_menu_Switch_notify)
			self.id_Sonlyunallocated_notify = self.Sonlyunallocated.connect("notify::active", self.on_menu_Switch_notify)

			self.id_appdir_buffer_changed = self.appdir_buffer.connect("changed", self.on_menu_buffer_changed)
			self.id_appdir_view_focus_out_event = self.appdir_view.connect("focus-out-event", self.on_menu_view_focus_out_event)
			self.id_directorydir_buffer_changed = self.directorydir_buffer.connect("changed", self.on_menu_buffer_changed)
			self.id_directorydir_view_focus_out_event = self.directorydir_view.connect("focus-out-event", self.on_menu_view_focus_out_event)
			self.id_mergedir_buffer_changed = self.mergedir_buffer.connect("changed", self.on_menu_buffer_changed)
			self.id_mergedir_view_focus_out_event = self.mergedir_view.connect("focus-out-event", self.on_menu_view_focus_out_event)
			self.id_mergefile_buffer_changed = self.mergefile_buffer.connect("changed", self.on_menu_buffer_changed)
			self.id_mergefile_view_focus_out_event = self.mergefile_view.connect("focus-out-event", self.on_menu_view_focus_out_event)
			self.id_legacydir_buffer_changed = self.legacydir_buffer.connect("changed", self.on_menu_buffer_changed)
			self.id_legacydir_view_focus_out_event = self.legacydir_view.connect("focus-out-event", self.on_menu_view_focus_out_event)
			self.id_include_buffer_changed = self.include_buffer.connect("changed", self.on_menu_buffer_changed)
			self.id_include_view_focus_out_event = self.include_view.connect("focus-out-event", self.on_menu_view_focus_out_event)
			self.id_exclude_buffer_changed = self.exclude_buffer.connect("changed", self.on_menu_buffer_changed)
			self.id_exclude_view_focus_out_event = self.exclude_view.connect("focus-out-event", self.on_menu_view_focus_out_event)
			self.id_defaultlayout_buffer_changed = self.defaultlayout_buffer.connect("changed", self.on_menu_buffer_changed)
			self.id_defaultlayout_view_focus_out_event = self.defaultlayout_view.connect("focus-out-event", self.on_menu_view_focus_out_event)
			self.id_layout_buffer_changed = self.layout_buffer.connect("changed", self.on_menu_buffer_changed)
			self.id_layout_view_focus_out_event = self.layout_view.connect("focus-out-event", self.on_menu_view_focus_out_event)
			self.id_menu_buffer_changed = self.menu_buffer.connect("changed", self.on_menu_buffer_changed)
			self.id_menu_view_focus_out_event = self.menu_view.connect("focus-out-event", self.on_menu_view_focus_out_event)
		
		builder = Gtk.Builder()
		builder.set_translation_domain(LOCALE_DOMAIN)
		builder.add_from_file(glade_path)
		load_objects(self, builder)
		load_prefs(self)
		load_signals(self)
		self.pagenum = 4
		self.Entry = None
		self.window.show()
		self.load_menu()

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
		self.Rmenu = builder.get_object("Rmenu")
		self.Rapps = builder.get_object("Rapps")

class Loading:
	def __init__(self):
		builder = Gtk.Builder()
		builder.set_translation_domain(LOCALE_DOMAIN)
		builder.add_from_file(glade_path)
		self.Wloading = builder.get_object("Wloading")

class run:
	def __init__(self):
		app = Ezame()
		Gtk.main()

if local:
	app = Ezame()
	Gtk.main()
