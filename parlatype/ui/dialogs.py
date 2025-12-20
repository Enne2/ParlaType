from gi.repository import Gtk

class InputDialog(Gtk.Window):
    def __init__(self, parent, title, message, callback):
        super().__init__(title=title)
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(300, 150)
        self.callback = callback
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(20)
        vbox.set_margin_bottom(20)
        vbox.set_margin_start(20)
        vbox.set_margin_end(20)
        self.set_child(vbox)
        
        lbl = Gtk.Label(label=message)
        vbox.append(lbl)
        
        self.entry = Gtk.Entry()
        vbox.append(self.entry)
        
        hbox = Gtk.Box(spacing=10)
        hbox.set_halign(Gtk.Align.CENTER)
        vbox.append(hbox)
        
        btn_cancel = Gtk.Button(label="Cancel")
        btn_cancel.connect("clicked", lambda x: self.close())
        hbox.append(btn_cancel)
        
        btn_ok = Gtk.Button(label="OK")
        btn_ok.connect("clicked", self.on_ok)
        hbox.append(btn_ok)
        
    def on_ok(self, btn):
        text = self.entry.get_text()
        if text:
            self.callback(text)
        self.close()
