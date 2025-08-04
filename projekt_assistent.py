import customtkinter as ctk
import csv
import os
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

        self.title("Gemini Projekt-Assistent")
        self.geometry("1100x720")

        # Initialize Gemini Model
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.chat = self.model.start_chat(history=[])


        # Haupt-Grid konfigurieren (2 Spalten: Projektliste, Chatbereich)
        self.grid_columnconfigure(1, weight=1)
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

        # --- Rechter Frame (Tabs für Chat, Todo, etc.) ---
        self.tab_view = ctk.CTkTabview(self, corner_radius=8)
        self.tab_view.grid(row=0, column=1, padx=(20, 20), pady=(10, 0), sticky="nsew")
        self.tab_view.add("Chat")
        self.tab_view.add("To-Do")
        self.tab_view.add("Dateien")

        # --- Chat-Tab ---
        self.tab_view.tab("Chat").grid_columnconfigure(0, weight=1)
        self.tab_view.tab("Chat").grid_rowconfigure(0, weight=1)
        
        self.chat_display = ctk.CTkTextbox(self.tab_view.tab("Chat"), state="disabled", wrap="word")
        self.chat_display.grid(row=0, column=0, sticky="nsew")

        # --- To-Do-Tab ---
        self.tab_view.tab("To-Do").grid_columnconfigure(0, weight=1)
        self.tab_view.tab("To-Do").grid_rowconfigure(0, weight=1)
        
        # --- Datei-Tab ---
        self.tab_view.tab("Dateien").grid_columnconfigure(0, weight=1)
        self.tab_view.tab("Dateien").grid_rowconfigure(0, weight=1)
        self.file_tree_frame = ctk.CTkScrollableFrame(self.tab_view.tab("Dateien"))
        self.file_tree_frame.grid(row=0, column=0, sticky="nsew")


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
        csv_path = "G:\\Meine Ablage\\Design\\projekte.csv"
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
        self.add_message_to_display("System", f"Kontext auf Projekt '{project['Projektname']}' gesetzt.\nPfad: {project['Pfad']}")
        
        # Start a new chat session for the selected project
        self.chat = self.model.start_chat(history=[])
        self.add_message_to_display("System", "Neuer Chat für dieses Projekt gestartet.")

        self.update_todo_tab()
        self.update_file_tree()

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
        for widget in self.file_tree_frame.winfo_children():
            widget.destroy()

        if not self.current_project:
            label = ctk.CTkLabel(self.file_tree_frame, text="Kein Projekt ausgewählt.")
            label.pack(pady=10, padx=10)
            return

        project_path = self.current_project['Pfad']
        if not os.path.isdir(project_path):
            label = ctk.CTkLabel(self.file_tree_frame, text="Projektpfad ist kein gültiges Verzeichnis.")
            label.pack(pady=10, padx=10)
            return

        for item in sorted(os.listdir(project_path)):
            item_path = os.path.join(project_path, item)
            label_text = "📁 " + item if os.path.isdir(item_path) else "📄 " + item
            label = ctk.CTkLabel(self.file_tree_frame, text=label_text, anchor="w")
            label.pack(fill="x", padx=5)

    def add_message_to_display(self, sender, message):
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", f"{sender}:\n{message}\n\n")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    def send_message_event(self, event):
        self.send_message()

    def send_message(self):
        user_input = self.entry.get()
        if not user_input.strip():
            return
        
        self.add_message_to_display("Sie", user_input)
        self.entry.delete(0, "end")
        
        self.send_button.configure(state="disabled")
        self.update() # Force GUI update

        try:
            prompt = user_input
            # Add project context to the prompt
            if self.current_project:
                # Add file content to context if requested
                if "lies die datei" in user_input.lower() or "read the file" in user_input.lower():
                     # Simple parsing, can be improved
                    try:
                        filename = user_input.split(" ")[-1]
                        filepath = os.path.join(self.current_project['Pfad'], filename)
                        if os.path.exists(filepath):
                            with open(filepath, 'r', encoding='utf-8') as f:
                                file_content = f.read()
                            prompt += f"\n\n--- Inhalt von {filename} ---\n{file_content}"
                        else:
                            self.add_message_to_display("System", f"Datei nicht gefunden: {filename}")
                    except Exception as e:
                        self.add_message_to_display("System", f"Fehler beim Lesen der Datei: {e}")


                prompt = f"Kontext: Du bist ein Projekt-Assistent. Das aktuelle Projekt ist '{self.current_project['Projektname']}' im Verzeichnis '{self.current_project['Pfad']}'.\n\nAnfrage: {prompt}"
            
            response = self.chat.send_message(prompt)
            self.add_message_to_display("Gemini", response.text)
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