# Copyright (C) 2017 Tom Hartill
#
# ThemedIconChooser.py - A set of GTK+ 3 widgets for selecting themed icons.
#
# ThemedIconChooser is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 3 of the License, or (at your option) any
# later version.
#
# ThemedIconChooser is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# ThemedIconChooser; if not, see http://www.gnu.org/licenses/.
#
# An up to date version can be found at:
# https://github.com/Tomha/python-gtk-themed-icon-chooser

import re
from threading import Thread

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, GObject, Gtk, Pango

import gettext
LOCALE_DOMAIN = "ezame"
gettext.textdomain(LOCALE_DOMAIN)
_ = gettext.gettext

class IconChooserDialog(Gtk.Dialog):
    # TODO: Not all memory created by the dialog seems to be released.
    """GTK+ 3 Dialog to allow selection of a themed icon.

    The name of the selection icon is made available as a result of the run
    method, or by the get_selected_icon_name method.

    NOTE: If 1000s of icons are displayed this is 1000s of widgets. They are
    loaded asynchronously to prevent blocking the main thread, but they must
    still be show()n from the main thread, which may momentarily block it. This
    can be limited by filtering the available icon selection beforehand.
    """
    def __init__(self):
        super().__init__()
        GLib.threads_init()

        self.set_default_size(500, 500)
        self.set_icon_name("gtk-filter")
        self.set_title(_("Choose An Icon"))

        self._icon_contexts = []
        self._icon_size = 32
        self._icon_theme = None
        self._filter_term = ""
        self._selected_icon = ""
        self._use_regex = False

        # Widgets start here

        # Context Filtering
        icon_context_label = Gtk.Label(_("Icon Context:"))
        icon_context_label.set_width_chars(11)

        text_renderer = Gtk.CellRendererText()
        self._context_store = Gtk.ListStore(str)
        self._icon_context_combo = Gtk.ComboBox()
        self._icon_context_combo.set_model(self._context_store)
        self._icon_context_combo.pack_start(text_renderer, True)
        self._icon_context_combo.add_attribute(text_renderer, "text", 0)

        icon_context_box = Gtk.Box()
        icon_context_box.set_spacing(4)
        icon_context_box.pack_start(icon_context_label, False, False, 0)
        icon_context_box.pack_start(self._icon_context_combo, True, True, 0)

        # Name Filtering

        filter_label = Gtk.Label(_("Filter Term:"))
        filter_label.set_width_chars(11)

        self._filter_entry = Gtk.Entry()

        filter_clear_button = Gtk.Button.new_from_icon_name("gtk-clear",
                                                            Gtk.IconSize.MENU)

        filter_box = Gtk.Box()
        filter_box.set_spacing(4)
        filter_box.pack_start(filter_label, False, False, 0)
        filter_box.pack_start(self._filter_entry, True, True, 0)
        filter_box.pack_start(filter_clear_button, False, False, 0)

        # Icon Previews

        self._icon_box = Gtk.FlowBox()
        self._icon_box.set_orientation(Gtk.Orientation.HORIZONTAL)
        self._icon_box.set_column_spacing(8)
        self._icon_box.set_row_spacing(8)
        self._icon_box.set_homogeneous(True)
        self._icon_box.set_valign(Gtk.Align.START)

        self._scroller = Gtk.ScrolledWindow()
        self._scroller.add(self._icon_box)

        # A slight hack to get the theme's background color for widgets.
        context = self._filter_entry.get_style_context()
        background_color = context.get_background_color(Gtk.StateType.NORMAL)
        self._icon_box_frame = Gtk.Frame()
        self._icon_box_frame.override_background_color(Gtk.StateFlags.NORMAL,
                                                       background_color)
        self._icon_box_frame.add(self._scroller)

        # Spinner
        self._spinner = Gtk.Spinner()
        self._spinner.set_size_request(48, 48)
        self._spinner.set_hexpand(False)
        self._spinner.set_vexpand(False)
        self._spinner.set_halign(Gtk.Align.CENTER)
        self._spinner.set_valign(Gtk.Align.CENTER)

        content_box = self.get_content_area()
        content_box.set_margin_left(8)
        content_box.set_margin_right(8)
        content_box.set_margin_top(8)
        content_box.set_margin_bottom(8)
        content_box.set_spacing(8)
        content_box.pack_start(icon_context_box, False, False, 0)
        content_box.pack_start(filter_box, False, False, 0)
        content_box.pack_start(self._icon_box_frame, True, True, 0)

        # Dialog Buttons
        button_box = self.get_action_area()
        button_box.set_spacing(4)
        self._ok_button = self.add_button(Gtk.STOCK_OK, 1)
        self.add_button(Gtk.STOCK_CANCEL, 0)

        # Connect Signals
        self._icon_context_combo.connect("changed", self._on_context_changed)
        self._filter_entry.connect("changed", self._filter_icons)
        filter_clear_button.connect("clicked", lambda button:
                                    self._filter_entry.set_text(""))
        self._icon_box.connect("selected-children-changed",
                              self._on_icon_selected)

    def _create_icon_previews(self, icon_name_list, icon_size):
        """Create icon previews to be placed in the dialog's icon box.
        
        Intended to be run in new thread. This only creates previews and adds
        them to the icon flow box, but it will not show()/display them. This is
        done by calling _display_icon_previews, which should be done in the
        main thread via GLib.idle_add.
        
        :param icon_name_list: List of icon names to create previews for.
        :param icon_size: Size to make icons within previews.
        :return: None
        """
        for icon in icon_name_list:
            flow_child = Gtk.FlowBoxChild()
            flow_child.add(_IconPreview(icon, icon_size))
            flow_child.connect("activate", self._on_icon_preview_selected)
            GLib.idle_add(self._icon_box.insert, flow_child, -1)
        GLib.idle_add(self._display_icon_previews)

    def _display_icon_previews(self):
        """Display icons and clean up after _create_icon_previews is run.

        WARNING: This must be run from the main thread, however show_all can
        take a noticeable amount of time, so the dialog will freeze momentarily
        as this runs if there are many icons to display. This is not avoidable
        to my knowledge.
        
        :return: None
        """
        self._icon_box_frame.remove(self._icon_box_frame.get_children()[0])
        self._icon_box_frame.add(self._scroller)
        self._spinner.stop()
        self._scroller.show_all()

        if self._filter_entry.get_text():
            self._filter_icons(self._filter_entry)
            self._filter_entry.set_position(len(self._filter_entry.get_text()))
        else:
            self._icon_box.show_all()

        self._icon_context_combo.set_sensitive(True)

    def _filter_icons(self, entry):
        """Filter icons based on filter term, used when filter term changes.

        If use_regex is True, the provided string will be used as the pattern
        for a regex match, otherwise basic case-insensitive matching is used.
        
        :param entry: Text entry containing filter text.
        :return: None
        """
        self._filter_term = entry.get_text()
        if self._filter_term == "":
            for icon in self._icon_box.get_children():
                icon.show()
        else:
            for icon in self._icon_box.get_children():
                if self._use_regex:
                    if re.search(self._filter_term, icon):
                        icon.show()
                    else:
                        icon.hide()
                else:
                    name = icon.get_children()[0].get_name().lower()\
                        .replace('-', ' ').replace('_', ' ')
                    if self._filter_term.lower() in name:
                        icon.show()
                    else:
                        icon.hide()

    def _on_context_changed(self, combobox):
        """When the context is changed, display the approprite icons.
        
        :param combobox: ComboBox used for context selection.
        :return: None
        """
        self._ok_button.set_sensitive(False)
        self._selected_icon = None

        for child in self._icon_box.get_children():
            child.destroy()

        # Place a spinner in the icon section while icons are loaded.
        self._icon_box_frame.remove(self._icon_box_frame.get_children()[0])
        self._icon_box_frame.add(self._spinner)
        self._spinner.start()
        self._icon_context_combo.set_sensitive(False)
        # Load icon previews for the new context asynchronously.
        selected_context = self._context_store.get_value(
                self._icon_context_combo.get_active_iter(), 0)
        current_icons = self._icon_theme.list_icons(selected_context)
        current_icons.sort()
        thread = Thread(target=self._create_icon_previews,
                        args=(current_icons, self._icon_size))
        thread.setDaemon(True)
        thread.start()

    def _on_icon_preview_selected(self, preview):
        """Emulate OK when an icon preview is activated.
        
        :param preview: The preview activated.
        :return: None
        """
        self.response(1)

    def _on_icon_selected(self, flowbox):
        """Sets the selected_icon property when the selection changes.
        
        :param flowbox: FlowBox in which selection changed.
        :return: None
        """
        selection = flowbox.get_selected_children()
        if not selection:
            self._selected_icon = None
            self._ok_button.set_sensitive(False)
        else:
            self._selected_icon = selection[0].get_children()[0].get_name()
            self._ok_button.set_sensitive(True)

    def get_icon_contexts(self):
        """Get the list of icon contexts from which selection is allowed.

        :return: List of icon contexts to be displayed.
        """
        return self._icon_contexts

    def get_icon_size(self):
        """Get the pixel size to display icons in.

        :return: Size to display icons in, in pixels.
        """
        return self._icon_size

    def get_filter_term(self):
        """Get the string used for filtering icons by name.

        :return: String used for filtering icons by name.
        """
        return self._filter_term

    def get_selected_icon_name(self):
        """Get the name of the icon selected in the dialog.

        :return: Name of the currently selected icon.
        """
        return self._selected_icon

    def get_use_regex(self):
        """ Get whether the filter term should be used as a regex pattern.

        :return: Whether the filter term is used as a regex pattern.
        """
        return self._use_use_regex

    def run(self):
        """Run dialog to select a themed icon.

        This loads a the current icon theme, gets and filters available
        contexts, then filters/displays icon previews for the first
        (alphabetically) context.

        :return: None
        """
        self._icon_theme = Gtk.IconTheme.get_default()
        if self._icon_contexts:
            used_contexts = []
            for context in self._icon_theme.list_contexts():
                if context in self._icon_contexts:
                    used_contexts += [context]
            used_contexts.sort()
        else:
            used_contexts = self._icon_theme.list_contexts()
            used_contexts.sort()

        self._context_store.clear()
        for context in used_contexts:
            self._context_store.append([context])
        self._icon_context_combo.set_active(0)

        if self._filter_term:
            self._filter_entry.set_text(self._filter_term)

        self._ok_button.set_sensitive(False)

        self.show_all()
        result = super().run()
        self.destroy()
        if result == 1:
            return self._selected_icon
        return None

    def set_icon_contexts(self, context_list):
        """Set the list of icon contexts from which selection is allowed.

        Contexts can be found using Gtk.IconTheme.get_default().list_contexts()

        Dialog will not update the available contexts once it has been shown.

        :param context_list: List of icon contexts to allow selection from.
        :return: None
        """
        if not type(context_list) == list:
            raise TypeError("must be type list, not " +
                            type(context_list).__name__)
        self._icon_contexts = list(set(context_list))

    def set_icon_size(self, size):
        """Set the pixel size to display icons in.

        Dialog will not update the icon size once it has been shown.

        :param size: Size to display icons in, in pixels.
        :return: None
        """
        if not type(size) == int:
            raise TypeError("must be type int, not " +
                            type(size).__name__)
        self._icon_size = size

    def set_filter_term(self, filter_term):
        """Set the string used for filtering icons by name.

        If use_regex is True, the provided string will be used as the pattern
        for a regex match, otherwise basic case-insensitive matching is used.

        Dialog will not update the filter term once it has been shown.

        :param filter_term: String used for filtering icons by name.
        :return: None
        """
        if not type(filter_term) == str:
            raise TypeError("must be type str, not " +
                            type(filter_term).__name__)
        self._filter_term = filter_term

    def set_use_regex(self, use_regex):
        """Set whether or not regex terms are used to filter icons.

        If use_regex is True, the filter term will be used as the pattern for a
        regex match, otherwise basic case-insensitive matching is used.

        Dialog will not update this value once it has been shown.

        :param use_regex: Whether the filter term is used as a regex pattern.
        :return: None
        """
        if not type(use_regex) == bool:
            raise TypeError("must be type bool, not " +
                            type(use_regex).__name__)
        self._use_regex = use_regex


class IconChooserButton(Gtk.Button):
    """GTK + 3 Button to open dialog allowing selection of a themed icon.

    The name of the selected icon is emitted via the "icon-selected" signal
    once the dialog is closed, or via the get_selected_icon_name method.

    NOTE: The icon preview in the dialog and on the button may differ since
    icons can have a different appearance at different sizes.By default the
    dialog uses a larger size (32px) than the button (16px).
    set_dialog_icon_size(16) can be used to get the dialog to display the same
    icon that will be shown on the button, if you desire.
    """
    def __init__(self):
        super().__init__()

        self._icon_contexts = []
        self._icon_size = 32
        self._filter_term = ""
        self._use_regex = False
        self._selected_icon = None

        # Register a custom icon_selected signal for once dialog closes.
        GObject.type_register(IconChooserButton)
        GObject.signal_new("icon-selected",
                           IconChooserButton,
                           GObject.SIGNAL_RUN_FIRST,
                           GObject.TYPE_NONE,
                           [GObject.TYPE_STRING])

        # Widgets go here
        self._icon = Gtk.Image.new_from_icon_name("gtk-search",
                                                  Gtk.IconSize.MENU)
        self._icon.set_margin_left(2)

        open_icon = Gtk.Image.new_from_icon_name("document-open-symbolic",
                                                 Gtk.IconSize.MENU)
        self._label = Gtk.Label(_("(Choose An Icon)"))
        self._label.set_hexpand(True)
        self._label.set_halign(Gtk.Align.START)
        self._label.set_ellipsize(Pango.EllipsizeMode.END)

        box = Gtk.Box()
        box.set_spacing(4)
        box.pack_start(self._icon, False, False, 0)
        box.pack_start(self._label, False, True, 0)
        box.pack_start(open_icon, False, False, 2)

        self.add(box)
        self.connect("clicked", self._show_dialog)

    def _show_dialog(self, button):
        """Called when the button is clicked to show a selection dialog.

        :param button: The button used to show the dialog (self)
        :return: None
        """
        dialog = IconChooserDialog()
        dialog.set_transient_for(self.get_toplevel())
        dialog.set_icon_contexts(self._icon_contexts)
        dialog.set_icon_size(self._icon_size)
        dialog.set_filter_term(self._filter_term)
        dialog.set_use_regex(self._use_regex)
        self._selected_icon = dialog.run()
        dialog.destroy()

        if self._selected_icon:
            self._icon.set_from_icon_name(self._selected_icon,
                                          Gtk.IconSize.MENU)
            self._label.set_text(self._selected_icon)
        else:
            self._icon.set_from_icon_name("gtk-search", Gtk.IconSize.MENU)
            self._label.set_text(_("(Choose An Icon)"))
        self.emit("icon-selected", self._selected_icon)

    def get_icon_contexts(self):
        """Get the list of icon contexts from which selection is allowed.

        :return: List of icon contexts to be displayed.
        """
        return self._icon_contexts

    def get_icon_size(self):
        """Get the pixel size to display icons in.
        
        :return: Size to display icons in, in pixels.
        """
        return self._icon_size

    def get_filter_term(self):
        """Get the string used for filtering icons by name.

        :return: String used for filtering icons by name.
        """
        return self._filter_term

    def get_selected_icon_name(self):
        """Get the name of the icon selected in the dialog.

        :return: Name of the currently selected icon.
        """
        return self._selected_icon

    def get_use_regex(self):
        """ Get whether the filter term should be used as a regex pattern.

        :return: Whether the filter term is used as a regex pattern.
        """
        return self._use_use_regex

    def set_icon_contexts(self, context_list):
        """Set the list of icon contexts from which selection is allowed.

        Contexts can be found using Gtk.IconTheme.get_default().list_contexts()

        Dialog will not update the available contexts once it has been shown.

        :param context_list: List of icon contexts to allow selection from.
        :return: None
        """
        if not type(context_list) == list:
            raise TypeError("must be type list, not " +
                            type(context_list).__name__)
        self._icon_contexts = list(set(context_list))

    def set_icon_size(self, size):
        """Set the pixel size to display icons in.

        Dialog will not update the icon size once it has been shown.
        
        :param size: Size to display icons in, in pixels.
        :return: None
        """
        if not type(size) == int:
            raise TypeError("must be type int, not " +
                            type(size).__name__)
        self._icon_size = size

    def set_filter_term(self, filter_term):
        """Set the string used for filtering icons by name.

        If use_regex is True, the provided string will be used as the pattern
        for a regex match, otherwise basic case-insensitive matching is used.

        Dialog will not update the filter term once it has been shown.

        :param filter_term: String used for filtering icons by name.
        :return: None
        """
        if not type(filter_term) == str:
            raise TypeError("must be type str, not " +
                            type(filter_term).__name__)
        self._filter_term = filter_term

    def set_use_regex(self, use_regex):
        """Set whether or not regex terms are used to filter icons.

        If use_regex is True, the filter term will be used as the pattern for a
        regex match, otherwise basic case-insensitive matching is used.

        Dialog will not update this value once it has been shown.

        :param use_regex: Whether the filter term is used as a regex pattern.
        :return: None
        """
        if not type(use_regex) == bool:
            raise TypeError("must be type bool, not " +
                            type(use_regex).__name__)
        self._use_regex = use_regex


class IconChooserComboBox(Gtk.ComboBox):
    """GTK+ 3 ComboBox allowing selection of a themed icon.
    
    The name of the currently selected icon is made available via the
    get_selected_icon method.

    Population of the combobox, done with the populate method, can take time
    and cause the UI to freeze if there are many icons to display. Therefore it
    is advised to limit the available icons by setting filter terms or context
    filters before population. I've attempted to make this asynchronous so as
    to avoid such delays but had no luck.
    """
    def __init__(self):
        super().__init__()

        self._icon_contexts = []
        self._filter_term = ""
        self._use_regex = False

        pixbuf_renderer = Gtk.CellRendererPixbuf()
        pixbuf_renderer.set_alignment(0, 0.5)
        pixbuf_renderer.set_padding(2, 0)
        text_renderer = Gtk.CellRendererText()
        text_renderer.set_alignment(0, 0.5)

        self._icon_store = Gtk.ListStore(str, str)
        self.set_model(self._icon_store)
        self.pack_start(pixbuf_renderer, True)
        self.add_attribute(pixbuf_renderer, "icon_name", 0)
        self.pack_start(text_renderer, True)
        self.add_attribute(text_renderer, "text", 1)

    def get_icon_contexts(self):
        """Get the list of icon contexts from which selection is allowed.

        :return: List of icon contexts to be displayed.
        """
        return self._icon_contexts

    def get_filter_term(self):
        """Get the string used for filtering icons by name.

        :return: String used for filtering icons by name.
        """
        return self._filter_term

    def get_selected_icon_name(self):
        """Get the name of the icon currently selected in the combo box.

        :return: Name of the currently selected icon.
        """
        selection = self._icon_store.get_value(self.get_active_iter(), 0)
        if selection == _("(Choose An Icon)"):
            return None
        else:
            return selection

    def get_use_regex(self):
        """ Get whether the filter term should be used as a regex pattern.

        :return: Whether the filter term is used as a regex pattern.
        """
        return self._use_regex

    def populate(self):
        """Populate the combo box with themed icons.

        This can take timeand cause the UI to freeze if there are many icons to
        display. Therefore itis advised to limit the available icons by setting
        filter terms or context filters before population. I've attempted to
        make this asynchronous so as to avoid such delays but had no luck.
        
        :return: None
        """
        unfiltered_icons = []
        icon_theme = Gtk.IconTheme.get_default()
        if not self._icon_contexts:
            for context in icon_theme.list_contexts():
                unfiltered_icons += icon_theme.list_icons(context)
        else:
            for context in icon_theme.list_contexts():
                if context not in self._icon_contexts:
                    continue
                unfiltered_icons += icon_theme.list_icons(context)

        filtered_icons = []
        if not self._filter_term:
            for icon in unfiltered_icons:
                filtered_icons += [icon]
        else:
            for icon in unfiltered_icons:
                if self._use_regex:
                    if not re.search(self._filter_term, icon):
                        continue
                else:
                    if not self._filter_term.lower() in \
                            icon.lower().replace('-', ' ').replace('_', ' '):
                        continue
                filtered_icons += [icon]

        # This section can be slow with many icons to show()
        self._icon_store.clear()
        self._icon_store.append(["gtk-search", _("(Choose An Icon)")])
        for icon in filtered_icons:
            self._icon_store.append([icon, icon])
        self.set_active(0)
        self.show_all()

    def set_icon_contexts(self, context_list):
        """Set the list of icon contexts from which selection is allowed.

        Contexts can be found using Gtk.IconTheme.get_default().list_contexts()

        Combobox will not update the available contexts once it has been shown.
        
        :param context_list: List of icon contexts to allow selection from.
        :return: None
        """
        if not type(context_list) == list:
            raise TypeError("must be type list, not " +
                            type(context_list).__name__)
        self._icon_contexts = list(set(context_list))

    def set_filter_term(self, filter_term):
        """Set the string used for filtering icons by name.

        If use_regex is True, the provided string will be used as the pattern
        for a regex match, otherwise basic case-insensitive matching is used.

        Combobox will not update the filter term once it has been shown.

        :param filter_term: String used for filtering icons by name.
        :return: None
        """
        if not type(filter_term) == str:
            raise TypeError("must be type str, not " +
                            type(filter_term).__name__)
        self._filter_term = filter_term

    def set_use_regex(self, use_regex):
        """Set whether or not regex terms are used to filter icons.

        If use_regex is True, the filter term will be used as the pattern for a
        regex match, otherwise basic case-insensitive matching is used.

        Combobox will not update this value once it has been shown.

        :param use_regex: Whether the filter term is used as a regex pattern.
        :return: None
        """
        if not type(use_regex) == bool:
            raise TypeError("must be type bool, not " +
                            type(use_regex).__name__)
        self._use_regex = use_regex


class _IconPreview(Gtk.Box):
    """Creates a preview box for icons containing the icon and its name."""
    def __init__(self, name, size):
        super().__init__()
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(2)

        self._icon_name = name
        self._display_name = name.replace('-', ' ').replace('_', ' ')
        self._icon_size = size

        icon = Gtk.Image.new_from_icon_name(name, Gtk.IconSize.DIALOG)
        # Gtk.Image.new_from_icon_name seems to sometimes ignore the set size,
        #   leading to inconsistent icon sizes. Solution is to force a size
        #   using set_pixel_size.
        icon.set_pixel_size(size)
        icon.set_tooltip_text(self._icon_name)

        label = Gtk.Label(self._display_name)
        label.set_justify(Gtk.Justification.CENTER)
        label.set_lines(3)
        label.set_line_wrap(True)
        label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        label.set_max_width_chars(8)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_yalign(0.5)

        self.pack_start(icon, False, False, 0)
        self.pack_start(label, False, False, 0)

    def get_name(self):
        """Get the name of the icon.
        
        :return: Name of the icon.
        """
        return self._icon_name
