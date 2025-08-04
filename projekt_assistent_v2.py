import customtkinter as ctk
import csv
import os
import json
import re
import datetime
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv


load_dotenv()
# --- Configure your Gemini API Key ---
# It's recommended to set this as an environment variable for security.
# If the environment variable is not set, the program will prompt for the key.
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    # This is a simple way to get the key, but a more robust solution
    # might be needed for a real application.
    root = ctk.CTk()
    root.withdraw() # Hide the main window
    API_KEY = ctk.CTkInputDialog(text="Please enter your Gemini API Key:", title="API Key").get_input()
    root.destroy()


genai.configure(api_key=API_KEY)


class ProjectAssistantApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Gemini Projekt-Assistent v2")
        self.geometry("1400x800")

        # Initialize Gemini Model
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.chat = None # Will be initialized when a project/chat is selected
        self.current_chat_file = None
        self.currently_editing_file = None


        # Haupt-Grid konfigurieren (3 Spalten: Projektliste, Chatbereich, Projekt-Infos)
        self.grid_columnconfigure(0, weight=0, minsize=250)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0, minsize=300)
        self.grid_rowconfigure(0, weight=1)

        # --- Linker Frame (Projektliste) ---
        self.project_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.project_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.project_frame.grid_rowconfigure(1, weight=1)

        self.project_label = ctk.CTkLabel(self.project_frame, text="Projekte", font=ctk.CTkFont(size=16, weight="bold"))
        self.project_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.project_list_frame = ctk.CTkScrollableFrame(self.project_frame, label_text="")
        self.project_list_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        self.projects = []
        self.load_projects()

        # --- Mittlerer Frame (Tabs für Chat, Todo, etc.) ---
        self.tab_view = ctk.CTkTabview(self, corner_radius=8)
        self.tab_view.grid(row=0, column=1, padx=(20, 20), pady=(10, 0), sticky="nsew")
        self.tab_view.add("Chat")
        self.tab_view.add("To-Do")
        self.tab_view.add("Dateien")

        # --- Chat-Tab ---
        self.tab_view.tab("Chat").grid_columnconfigure(0, weight=1)
        self.tab_view.tab("Chat").grid_rowconfigure(1, weight=1)
        
        # Frame for chat selection
        self.chat_selection_frame = ctk.CTkFrame(self.tab_view.tab("Chat"))
        self.chat_selection_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        
        self.new_chat_button = ctk.CTkButton(self.chat_selection_frame, text="Neuer Chat", command=self.start_new_chat)
        self.new_chat_button.pack(side="left", padx=(0, 10))
        
        self.chat_history_menu = ctk.CTkOptionMenu(self.chat_selection_frame, values=["Bestehenden Chat wählen..."])
        self.chat_history_menu.configure(command=self.load_selected_chat)
        self.chat_history_menu.pack(side="left", fill="x", expand=True)
        
        self.chat_display = ctk.CTkTextbox(self.tab_view.tab("Chat"), state="disabled", wrap="word")
        self.chat_display.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        # Configure tags for markdown rendering
        self.chat_display.tag_config("bold", underline=True)
        self.chat_display.tag_config("italic", overstrike=True) # Using overstrike as a substitute for italic
        self.chat_display.tag_config("code", background="#333333", foreground="#ffffff")
        self.chat_display.tag_config("h1", foreground="#4287f5")
        self.chat_display.tag_config("h2", foreground="#42a5f5")
        self.chat_display.tag_config("h3", foreground="#42c5f5")

        # --- To-Do-Tab ---
        self.tab_view.tab("To-Do").grid_columnconfigure(0, weight=1)
        self.tab_view.tab("To-Do").grid_rowconfigure(0, weight=1)
        
        # --- Datei-Tab ---
        self.tab_view.tab("Dateien").grid_columnconfigure(0, weight=1)
        self.tab_view.tab("Dateien").grid_rowconfigure(1, weight=1)

        self.file_browser_frame = ctk.CTkScrollableFrame(self.tab_view.tab("Dateien"), label_text="Projektdateien")
        self.file_browser_frame.grid(row=0, column=0, rowspan=2, padx=10, pady=10, sticky="nsew")

        self.file_editor_frame = ctk.CTkFrame(self.tab_view.tab("Dateien"))
        self.file_editor_frame.grid(row=0, column=1, rowspan=2, padx=10, pady=10, sticky="nsew")
        self.file_editor_frame.grid_columnconfigure(0, weight=1)
        self.file_editor_frame.grid_rowconfigure(1, weight=1)
        self.file_editor_frame.grid_remove() # Hide until a file is opened

        self.opened_file_label = ctk.CTkLabel(self.file_editor_frame, text="Keine Datei geöffnet", font=ctk.CTkFont(size=14))
        self.opened_file_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.file_editor_textbox = ctk.CTkTextbox(self.file_editor_frame, wrap="word", font=("Consolas", 12))
        self.file_editor_textbox.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")

        self.file_editor_buttons_frame = ctk.CTkFrame(self.file_editor_frame, fg_color="transparent")
        self.file_editor_buttons_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="e")

        self.file_save_button = ctk.CTkButton(self.file_editor_buttons_frame, text="Speichern", command=self.save_opened_file)
        self.file_save_button.pack(side="left", padx=(0, 10))
        
        self.file_close_button = ctk.CTkButton(self.file_editor_buttons_frame, text="Schließen", command=self.close_file_editor)
        self.file_close_button.pack(side="left")


        # --- Rechter Frame (Projekt-Infos) ---
        self.info_frame = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.info_frame.grid(row=0, column=2, rowspan=2, sticky="nsew", padx=(0, 20))
        self.info_frame.grid_propagate(False)
        self.info_frame.grid_rowconfigure(1, weight=1)

        self.info_label = ctk.CTkLabel(self.info_frame, text="Projekt-Informationen", font=ctk.CTkFont(size=16, weight="bold"))
        self.info_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.info_content_frame = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        self.info_content_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")


        # --- Eingabe-Frame ---
        self.input_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.input_frame.grid(row=1, column=1, sticky="nsew", padx=(20,20), pady=(10,20))
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkEntry(self.input_frame, placeholder_text="Stellen Sie eine Frage an Gemini...")
        self.entry.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.entry.bind("<Return>", self.send_message_event)

        self.send_button = ctk.CTkButton(self.input_frame, text="Senden", command=self.send_message)
        self.send_button.grid(row=0, column=1)
        
        self.add_message_to_display("Willkommen!", "Hallo! Ich bin Ihr persönlicher Projekt-Assistent. Wählen Sie ein Projekt aus der Liste, um zu beginnen.")
        
        self.current_project = None
        self.update_todo_tab() # Initialize with empty state
        self.update_file_tree() # Initialize with empty state


    def load_projects(self):
        csv_path = "projekte.csv"
        if not os.path.exists(csv_path):
            self.add_message_to_display("System", f"Fehler: Die Datei projekte.csv wurde nicht gefunden unter {csv_path}")
            return
            
        with open(csv_path, mode='r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                self.projects.append(row)
        
        # Projekte in der GUI anzeigen
        for project in self.projects:
            button = ctk.CTkButton(self.project_list_frame, text=project['Projektname'], fg_color="transparent", command=lambda p=project: self.select_project(p))
            button.pack(fill="x", padx=5, pady=2)

    def select_project(self, project):
        self.current_project = project
        self.clear_chat_display()
        self.add_message_to_display("System", f"Kontext auf Projekt '{project['Projektname']}' gesetzt.")
        
        self.close_file_editor()
        self.update_chat_history_menu()
        self.update_info_panel()
        self.update_todo_tab()
        self.update_file_tree()
        
        # Automatically start a new chat if no history exists
        if not self.get_chat_history_files():
            self.start_new_chat()
        else:
            self.chat = None
            self.current_chat_file = None
            self.add_message_to_display("System", "Wählen Sie einen Chat aus dem Menü oder starten Sie einen neuen.")

    def update_chat_history_menu(self):
        if not self.current_project:
            self.chat_history_menu.configure(values=["Bestehenden Chat wählen..."])
            self.chat_history_menu.set("Bestehenden Chat wählen...")
            return

        history_files = self.get_chat_history_files()
        if history_files:
            self.chat_history_menu.configure(values=history_files)
            self.chat_history_menu.set(history_files[0])
            self.load_selected_chat(history_files[0])
        else:
            self.chat_history_menu.configure(values=["Keine Chats vorhanden"])
            self.chat_history_menu.set("Keine Chats vorhanden")

    def get_chat_history_files(self):
        if not self.current_project:
            return []
        chat_dir = os.path.join(self.current_project['Pfad'], ".chats")
        if not os.path.exists(chat_dir):
            return []
        
        files = [f for f in os.listdir(chat_dir) if f.endswith(".json")]
        # Sort by creation time, newest first
        files.sort(key=lambda f: os.path.getctime(os.path.join(chat_dir, f)), reverse=True)
        return files

    def start_new_chat(self):
        if not self.current_project:
            self.add_message_to_display("System", "Bitte zuerst ein Projekt auswählen.")
            return
            
        self.chat = self.model.start_chat(history=[])
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.current_chat_file = os.path.join(self.current_project['Pfad'], ".chats", f"chat_{timestamp}.json")
        
        self.clear_chat_display()
        self.add_message_to_display("System", "Neuer Chat gestartet. Der Verlauf wird gespeichert.")
        self.update_chat_history_menu()
        self.chat_history_menu.set(os.path.basename(self.current_chat_file))


    def load_selected_chat(self, chat_file_name):
        if not self.current_project or chat_file_name in ["Bestehenden Chat wählen...", "Keine Chats vorhanden"]:
            return

        self.current_chat_file = os.path.join(self.current_project['Pfad'], ".chats", chat_file_name)
        
        try:
            with open(self.current_chat_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            self.chat = self.model.start_chat(history=history)
            self.clear_chat_display()
            self.add_message_to_display("System", f"Chat '{chat_file_name}' geladen.")
            
            # Display the loaded history
            for message in history:
                # Simple check for role, might need adjustment based on actual history format
                sender = "Sie" if message['role'] == 'user' else "Gemini"
                # Assuming 'parts' contains a list of text parts.
                self.add_message_to_display(sender, "".join(part['text'] for part in message['parts']))

        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            self.add_message_to_display("System", f"Fehler beim Laden des Chats: {e}")
            self.chat = self.model.start_chat(history=[]) # Start a fresh chat

    def save_chat_history(self):
        if not self.chat or not self.current_chat_file:
            return

        chat_dir = os.path.dirname(self.current_chat_file)
        if not os.path.exists(chat_dir):
            os.makedirs(chat_dir)
            
        # The history is already in the correct format in self.chat.history
        history_to_save = []
        for message in self.chat.history:
            # Convert Gemini's internal Message object to a serializable dict
            history_to_save.append({
                'role': message.role,
                'parts': [part.text for part in message.parts] # Extract text from parts
            })

        with open(self.current_chat_file, 'w', encoding='utf-8') as f:
            # We need to re-format the dictionary to match the expected format for start_chat
            reformatted_history = []
            for item in history_to_save:
                reformatted_history.append({
                    "role": item["role"],
                    "parts": [{"text": part} for part in item["parts"]]
                })
            json.dump(reformatted_history, f, indent=2)


    def update_info_panel(self):
        # Clear previous content
        for widget in self.info_content_frame.winfo_children():
            widget.destroy()

        if not self.current_project:
            label = ctk.CTkLabel(self.info_content_frame, text="Kein Projekt ausgewählt.")
            label.pack(pady=10, padx=10)
            return
        
        project_path = self.current_project['Pfad']
        
        # --- Project Photo ---
        photo_path = os.path.join(project_path, "project_photo.png")
        if os.path.exists(photo_path):
            try:
                img = Image.open(photo_path)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(260, 150))
                img_label = ctk.CTkLabel(self.info_content_frame, image=ctk_img, text="")
                img_label.pack(pady=(0,15))
            except Exception as e:
                error_label = ctk.CTkLabel(self.info_content_frame, text=f"Fehler beim Laden des Bildes:\n{e}", wraplength=260)
                error_label.pack(pady=(0,15))
        else:
            placeholder = ctk.CTkFrame(self.info_content_frame, width=260, height=150, fg_color="gray50")
            placeholder_label = ctk.CTkLabel(placeholder, text="Kein Projektbild\n(project_photo.png)")
            placeholder_label.pack(expand=True)
            placeholder.pack(pady=(0,15))

        # --- Project Details ---
        def create_info_row(label_text, value_text):
            frame = ctk.CTkFrame(self.info_content_frame, fg_color="transparent")
            frame.pack(fill="x", pady=2)
            label = ctk.CTkLabel(frame, text=label_text, font=ctk.CTkFont(weight="bold"), anchor="w")
            label.pack(side="left")
            value = ctk.CTkLabel(frame, text=value_text, anchor="e", wraplength=180)
            value.pack(side="right", fill="x", expand=True)

        try:
            stat = os.stat(project_path)
            create_info_row("Erstellt:", datetime.datetime.fromtimestamp(stat.st_ctime).strftime('%d.%m.%Y'))
            create_info_row("Letzte Änderung:", datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%d.%m.%Y %H:%M'))

            # Find last modified file
            last_mod_file, last_mod_time = "", 0
            for item in os.listdir(project_path):
                item_path = os.path.join(project_path, item)
                if os.path.isfile(item_path):
                    mod_time = os.path.getmtime(item_path)
                    if mod_time > last_mod_time:
                        last_mod_time = mod_time
                        last_mod_file = item
            create_info_row("Zuletzt bearbeitet:", last_mod_file)

        except FileNotFoundError:
            create_info_row("Fehler:", "Projektpfad nicht gefunden.")

    def update_todo_tab(self):
        # Clear previous content
        for widget in self.tab_view.tab("To-Do").winfo_children():
            widget.destroy()

        if not self.current_project:
            label = ctk.CTkLabel(self.tab_view.tab("To-Do"), text="Kein Projekt ausgewählt.")
            label.pack(pady=20, padx=20)
            return

        todo_path = os.path.join(self.current_project['Pfad'], "TODO.md")
        
        if os.path.exists(todo_path):
            self.todo_textbox = ctk.CTkTextbox(self.tab_view.tab("To-Do"), wrap="word")
            self.todo_textbox.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
            with open(todo_path, "r", encoding="utf-8") as f:
                self.todo_textbox.insert("0.0", f.read())
            
            self.todo_save_button = ctk.CTkButton(self.tab_view.tab("To-Do"), text="Speichern", command=self.save_todo_file)
            self.todo_save_button.grid(row=1, column=0, padx=10, pady=10, sticky="se")
        else:
            create_button = ctk.CTkButton(self.tab_view.tab("To-Do"), text="TODO.md erstellen", command=self.create_todo_file)
            create_button.pack(pady=20, padx=20)

    def create_todo_file(self):
        if not self.current_project:
            return
        todo_path = os.path.join(self.current_project['Pfad'], "TODO.md")
        with open(todo_path, "w", encoding="utf-8") as f:
            f.write("# To-Do-Liste für " + self.current_project['Projektname'] + "\n\n")
        self.update_todo_tab()

    def save_todo_file(self):
        if not self.current_project:
            return
        todo_path = os.path.join(self.current_project['Pfad'], "TODO.md")
        with open(todo_path, "w", encoding="utf-8") as f:
            f.write(self.todo_textbox.get("0.0", "end"))
        self.add_message_to_display("System", f"TODO.md für Projekt '{self.current_project['Projektname']}' gespeichert.")

    def update_file_tree(self):
        # Clear previous content
        for widget in self.file_browser_frame.winfo_children():
            widget.destroy()

        if not self.current_project:
            label = ctk.CTkLabel(self.file_browser_frame, text="Kein Projekt ausgewählt.")
            label.pack(pady=10, padx=10)
            return

        project_path = self.current_project['Pfad']
        if not os.path.isdir(project_path):
            label = ctk.CTkLabel(self.file_browser_frame, text="Projektpfad ist kein gültiges Verzeichnis.")
            label.pack(pady=10, padx=10)
            return

        for item in sorted(os.listdir(project_path)):
            item_path = os.path.join(project_path, item)
            if os.path.isdir(item_path):
                label_text = "📁 " + item
                label = ctk.CTkLabel(self.file_browser_frame, text=label_text, anchor="w")
                label.pack(fill="x", padx=5)
            else:
                label_text = "📄 " + item
                button = ctk.CTkButton(self.file_browser_frame, text=label_text, anchor="w", fg_color="transparent", command=lambda path=item_path: self.open_file_in_editor(path))
                button.pack(fill="x", padx=5)
    
    def open_file_in_editor(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.currently_editing_file = file_path
            
            self.file_editor_textbox.delete("0.0", "end")
            self.file_editor_textbox.insert("0.0", content)
            
            self.opened_file_label.configure(text=os.path.basename(file_path))
            self.file_editor_frame.grid() # Show the editor
            self.file_browser_frame.grid_remove() # Hide the browser

        except Exception as e:
            self.add_message_to_display("System", f"Fehler beim Öffnen der Datei {os.path.basename(file_path)}: {e}")

    def save_opened_file(self):
        if not self.currently_editing_file:
            return
        
        try:
            content = self.file_editor_textbox.get("0.0", "end")
            with open(self.currently_editing_file, 'w', encoding='utf-8') as f:
                f.write(content)
            self.add_message_to_display("System", f"Datei '{os.path.basename(self.currently_editing_file)}' erfolgreich gespeichert.")
        except Exception as e:
            self.add_message_to_display("System", f"Fehler beim Speichern der Datei: {e}")

    def close_file_editor(self):
        self.currently_editing_file = None
        self.file_editor_frame.grid_remove()
        self.file_browser_frame.grid()


    def clear_chat_display(self):
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.configure(state="disabled")

    def add_message_to_display(self, sender, message):
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", f"{sender}:\n", ("bold"))

        lines = message.split('\n')
        in_code_block = False
        code_block_content = ""

        for line in lines:
            if line.strip() == '```':
                if in_code_block:
                    # End of code block
                    self.create_code_block(code_block_content)
                    in_code_block = False
                    code_block_content = ""
                else:
                    # Start of code block
                    in_code_block = True
                continue

            if in_code_block:
                code_block_content += line + '\n'
            else:
                self.format_and_insert_line(line)

        self.chat_display.insert("end", "\n")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    def format_and_insert_line(self, line):
        # Same logic as before, but as a separate function
        if line.startswith("### "):
            self.chat_display.insert("end", line[4:] + "\n", "h3")
            return
        elif line.startswith("## "):
            self.chat_display.insert("end", line[3:] + "\n", "h2")
            return
        elif line.startswith("# "):
            self.chat_display.insert("end", line[2:] + "\n", "h1")
            return
        
        list_prefix = ""
        content_line = line
        if line.strip().startswith("* "):
            list_prefix = "  • "
            content_line = line.strip()[2:]
        elif line.strip().startswith("- "):
            list_prefix = "  • "
            content_line = line.strip()[2:]
        elif re.match(r"^\s*\d+\. ", line):
            match = re.match(r"^(\s*\d+\. )", line)
            list_prefix = f"  {match.group(1)}"
            content_line = line[len(match.group(0)):]

        if list_prefix:
            self.chat_display.insert("end", list_prefix)

        parts = re.split(r'(\**.*?\**|\*.*?\*|`.*?`)', content_line)
        for part in parts:
            if not part:
                continue
            if part.startswith('**') and part.endswith('**'):
                self.chat_display.insert("end", part[2:-2], "bold")
            elif part.startswith('*') and part.endswith('*'):
                self.chat_display.insert("end", part[1:-1], "italic")
            elif part.startswith('`') and part.endswith('`'):
                self.chat_display.insert("end", part[1:-1], "code")
            else:
                self.chat_display.insert("end", part)
        
        self.chat_display.insert("end", "\n")

    def create_code_block(self, code_content):
        code_frame = ctk.CTkFrame(self.chat_display, fg_color="#2b2b2b", corner_radius=5)
        
        code_text = ctk.CTkTextbox(code_frame, wrap="word", font=("Consolas", 12), fg_color="transparent")
        code_text.insert("1.0", code_content)
        code_text.configure(state="disabled")
        code_text.pack(padx=10, pady=5, fill="x")

        def copy_to_clipboard():
            self.clipboard_clear()
            self.clipboard_append(code_content)
            copy_button.configure(text="Copied!")
            self.after(2000, lambda: copy_button.configure(text="Copy"))

        copy_button = ctk.CTkButton(code_frame, text="Copy", command=copy_to_clipboard, width=80)
        copy_button.pack(padx=10, pady=(0, 5), anchor="e")

        # This is a bit of a hack to insert a widget into a Textbox
        self.chat_display.window_create("end", window=code_frame)
        self.chat_display.insert("end", "\n")

    def send_message_event(self, event):
        self.send_message()

    def send_message(self):
        user_input = self.entry.get()
        if not user_input.strip():
            return
        
        if not self.chat:
            self.add_message_to_display("System", "Bitte starten Sie einen neuen Chat oder wählen Sie einen bestehenden aus.")
            return

        self.add_message_to_display("Sie", user_input)
        self.entry.delete(0, "end")
        
        self.send_button.configure(state="disabled")
        self.update() # Force GUI update

        try:
            # Prepare the prompt for Gemini
            context_parts = []
            if self.current_project:
                # Add project context
                context_parts.append(f"Kontext: Du bist ein Projekt-Assistent. Das aktuelle Projekt ist '{self.current_project['Projektname']}' im Verzeichnis '{self.current_project['Pfad']}'.")

                # Add content of the currently edited file to the context
                if self.currently_editing_file and self.tab_view.get() == "Dateien":
                    file_content = self.file_editor_textbox.get("0.0", "end")
                    filename = os.path.basename(self.currently_editing_file)
                    context_parts.append(f"\n--- Aktuell geöffnete Datei: {filename} ---\n{file_content}")


                # Add file list to context if requested
                if any(keyword in user_input.lower() for keyword in ["dateien", "files", "verzeichnis", "directory", "liste"]):
                    try:
                        project_path = self.current_project['Pfad']
                        if os.path.isdir(project_path):
                            items = os.listdir(project_path)
                            files = [f for f in items if os.path.isfile(os.path.join(project_path, f))]
                            dirs = [d for d in items if os.path.isdir(os.path.join(project_path, d))]
                            
                            file_list_str = "\n--- Verzeichnisinhalt ---\n"
                            if dirs:
                                file_list_str += "Ordner:\n" + "\n".join(f"- {d}" for d in sorted(dirs)) + "\n"
                            if files:
                                file_list_str += "Dateien:\n" + "\n".join(f"- {f}" for f in sorted(files)) + "\n"
                            context_parts.append(file_list_str)
                        else:
                            context_parts.append("\n[System-Hinweis: Der Projektpfad ist ungültig.]")
                    except Exception as e:
                        context_parts.append(f"\n[System-Hinweis: Fehler beim Lesen des Verzeichnisses: {e}]")


                # Add file content to context if requested by command
                if "lies die datei" in user_input.lower() or "read the file" in user_input.lower():
                    try:
                        # More robust filename parsing
                        parts = user_input.split()
                        filename_index = -1
                        for i, part in enumerate(parts):
                            if part == "datei" or part == "file":
                                if i + 1 < len(parts):
                                    filename_index = i + 1
                                    break
                        
                        if filename_index != -1:
                            filename = parts[filename_index]
                            filepath = os.path.join(self.current_project['Pfad'], filename)
                            if os.path.exists(filepath) and os.path.isfile(filepath):
                                with open(filepath, 'r', encoding='utf-8') as f:
                                    file_content = f.read(4000) # Limit size
                                context_parts.append(f"\n--- Inhalt von {filename} ---\n{file_content}")
                                if len(file_content) == 4000:
                                    context_parts.append("\n[... Datei wurde gekürzt ...]")
                            else:
                                self.add_message_to_display("System", f"Datei nicht gefunden oder ist ein Verzeichnis: {filename}")
                        else:
                            self.add_message_to_display("System", "Konnte den Dateinamen im Befehl nicht finden.")
                    except Exception as e:
                        self.add_message_to_display("System", f"Fehler beim Lesen der Datei: {e}")

            # Combine context and the actual user query
            final_prompt = "\n".join(context_parts)
            if final_prompt:
                final_prompt += f"\n\nAnfrage: {user_input}"
            else:
                final_prompt = user_input
            
            response = self.chat.send_message(final_prompt)
            
            # Check if Gemini wants to modify the file
            if "---START_CODE_BLOCK---" in response.text and "---END_CODE_BLOCK---" in response.text and self.currently_editing_file:
                try:
                    # Extract code from the response
                    new_content = response.text.split("---START_CODE_BLOCK---")[1].split("---END_CODE_BLOCK---")[0].strip()
                    
                    # Update the editor
                    self.file_editor_textbox.delete("0.0", "end")
                    self.file_editor_textbox.insert("0.0", new_content)
                    
                    # Save the file automatically
                    self.save_opened_file()
                    
                    # Notify the user
                    self.add_message_to_display("Gemini", "Ich habe die Datei gemäß Ihren Anweisungen aktualisiert und gespeichert.")

                except Exception as e:
                    self.add_message_to_display("System", f"Fehler beim automatischen Aktualisieren der Datei: {e}")
                    self.add_message_to_display("Gemini", response.text) # Show original response
            else:
                self.add_message_to_display("Gemini", response.text)

            self.save_chat_history()

        except Exception as e:
            self.add_message_to_display("Error", f"Ein Fehler ist aufgetreten: {e}")
        finally:
            self.send_button.configure(state="normal")


if __name__ == "__main__":
    # A check to ensure the API key is available before starting the app
    if not API_KEY:
        print("Gemini API Key not found. Exiting.")
    else:
        app = ProjectAssistantApp()
        app.mainloop()