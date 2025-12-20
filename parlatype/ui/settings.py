import os
from gi.repository import Gtk
from ..core.config import PROMPTS_DIR, SYSTEM_PROMPTS_DIR, ENV_PATH
from .dialogs import InputDialog

class SettingsWindow(Gtk.Window):
    def __init__(self, parent, llm_corrector):
        super().__init__(title="Settings")
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(600, 450)
        self.llm_corrector = llm_corrector

        notebook = Gtk.Notebook()
        self.set_child(notebook)

        # --- General Tab ---
        general_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        general_box.set_margin_top(20)
        general_box.set_margin_bottom(20)
        general_box.set_margin_start(20)
        general_box.set_margin_end(20)
        notebook.append_page(general_box, Gtk.Label(label="General"))

        # API Key
        lbl_key = Gtk.Label(label="OpenAI API Key", xalign=0)
        general_box.append(lbl_key)

        self.api_key_entry = Gtk.Entry()
        self.api_key_entry.set_visibility(False)
        current_key = os.getenv("OPENAI_API_KEY", "")
        self.api_key_entry.set_text(current_key)
        general_box.append(self.api_key_entry)

        # Model
        lbl_model = Gtk.Label(label="LLM Model", xalign=0)
        general_box.append(lbl_model)

        self.model_entry = Gtk.Entry()
        current_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.model_entry.set_text(current_model)
        general_box.append(self.model_entry)

        # Save Button (General)
        save_gen_btn = Gtk.Button(label="Save Settings")
        save_gen_btn.add_css_class("suggested-action")
        save_gen_btn.connect("clicked", self.on_save_general)
        general_box.append(save_gen_btn)

        # --- Prompts Tab ---
        prompts_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        prompts_box.set_margin_top(10)
        prompts_box.set_margin_bottom(10)
        prompts_box.set_margin_start(10)
        prompts_box.set_margin_end(10)
        notebook.append_page(prompts_box, Gtk.Label(label="Prompts"))

        # File selection
        hbox_file = Gtk.Box(spacing=10)
        prompts_box.append(hbox_file)
        
        self.file_combo = Gtk.ComboBoxText()
        self.refresh_file_list()
        self.file_combo.set_active(0)
        self.file_combo.connect("changed", self.on_file_changed)
        hbox_file.append(self.file_combo)

        new_btn = Gtk.Button(label="New")
        new_btn.connect("clicked", self.on_new_clicked)
        hbox_file.append(new_btn)

        # Text Area
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        prompts_box.append(scrolled)

        self.textview = Gtk.TextView()
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.textbuffer = self.textview.get_buffer()
        self.textbuffer.set_text(self.llm_corrector.system_prompt)
        scrolled.set_child(self.textview)

        # Save Button (Prompts)
        save_prompt_btn = Gtk.Button(label="Save Prompt")
        save_prompt_btn.add_css_class("suggested-action")
        save_prompt_btn.connect("clicked", self.on_save_prompt)
        prompts_box.append(save_prompt_btn)

    def on_save_general(self, btn):
        new_key = self.api_key_entry.get_text().strip()
        new_model = self.model_entry.get_text().strip()
        
        # Update runtime
        os.environ["OPENAI_API_KEY"] = new_key
        os.environ["LLM_MODEL"] = new_model
        self.llm_corrector.client.api_key = new_key
        self.llm_corrector.model = new_model
        
        # Save to .env
        config_dir = os.path.dirname(ENV_PATH)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        try:
            with open(ENV_PATH, "w") as f:
                f.write(f"OPENAI_API_KEY={new_key}\n")
                f.write(f"LLM_MODEL={new_model}\n")
            self.close()
        except Exception as e:
            print(f"Error saving .env: {e}")

    def refresh_file_list(self):
        self.file_combo.remove_all()
        files = set()
        if os.path.exists(PROMPTS_DIR):
            files.update([f for f in os.listdir(PROMPTS_DIR) if f.endswith(".txt")])
        if os.path.exists(SYSTEM_PROMPTS_DIR):
            files.update([f for f in os.listdir(SYSTEM_PROMPTS_DIR) if f.endswith(".txt")])
            
        for f in sorted(list(files)):
            self.file_combo.append_text(f)
        if not files:
            self.file_combo.append_text("default.txt")

    def on_file_changed(self, widget):
        filename = widget.get_active_text()
        if filename:
            content = self.llm_corrector.load_prompt(filename)
            self.textbuffer.set_text(content)

    def on_new_clicked(self, widget):
        def on_filename_entered(filename):
            if not filename.endswith(".txt"):
                filename += ".txt"
            self.textbuffer.set_text("")
            self.file_combo.append_text(filename)
            # Select the new item (last one)
            model = self.file_combo.get_model()
            iter_ = model.get_iter_first()
            last_iter = None
            while iter_:
                last_iter = iter_
                iter_ = model.iter_next(iter_)
            if last_iter:
                self.file_combo.set_active_iter(last_iter)
        
        InputDialog(self, "New Prompt", "Enter filename (e.g. my_prompt):", on_filename_entered).present()

    def on_save_prompt(self, widget):
        start, end = self.textbuffer.get_bounds()
        content = self.textbuffer.get_text(start, end, True)
        filename = self.file_combo.get_active_text()
        if not filename:
            filename = "custom.txt"
        
        if self.llm_corrector.save_prompt(filename, content):
            pass
