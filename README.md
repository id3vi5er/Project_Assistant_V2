# Gemini Project Assistant v2

This is a desktop application built with Python and CustomTkinter that serves as a personal project assistant. It leverages the Gemini API to provide AI-powered chat, to-do list management, and file editing capabilities.

## Features

- **Project Management:** Organize your projects from a central `projekte.csv` file.
- **Context-Aware AI Chat:** Chat with the Gemini 1.5 Flash model. The chat is aware of the selected project, the currently opened file, and can list files in the project directory.
- **Chat History:** Each project has its own chat history, saved in a `.chats` directory within the project folder.
- **File Browser and Editor:** Browse and edit files directly within the application. The AI can be asked to modify the currently opened file.
- **To-Do List Management:** Each project can have its own `TODO.md` file for task management.
- **Project Information Panel:** Displays details about the selected project, including creation date, last modification, and a project image (`project_photo.png`).
- **Markdown Rendering:** The chat displays responses with basic markdown formatting (headings, bold, italic, code blocks).
- **Dynamic API Key Entry:** If the `GEMINI_API_KEY` is not found in the environment variables, the application will prompt the user to enter it.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    ```
2.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configure Projects:**
    - Create a `projekte.csv` file in the root directory of the application.
    - Add your projects with the following format: `Projektname,Pfad`
    - Example:
      ```csv
      MyFirstProject,C:/Users/YourUser/Documents/Projects/MyFirstProject
      AnotherProject,D:/Work/AnotherProject
      ```

4.  **Set API Key:**
    - **Recommended:** Create a `.env` file in the root directory and add your Gemini API key:
      ```
      GEMINI_API_KEY=your-api-key
      ```
    - **Alternative:** If you don't create a `.env` file, the application will ask for your API key on startup.

5.  **Run the application:**
    ```bash
    python projekt_assistent_v2.py
    ```

## How it Works

The application is built around a main `ProjectAssistantApp` class which handles the GUI and all functionalities.

- **`projekte.csv`:** This file is the central registry for all your projects. The application reads this file on startup to populate the project list.
- **Project Context:** When you select a project, the application sets the context for the AI. This includes the project's name and path.
- **AI Interaction:**
    - The AI receives the project context with every message.
    - It can read the content of the currently opened file in the "Dateien" tab to answer questions or perform modifications.
    - You can ask the AI to list the files in the current project directory by using keywords like "dateien", "files", etc.
    - You can ask the AI to read a specific file using the command "lies die datei <dateiname>".
- **File Modifications:** If you ask the AI to change the code in an opened file, it can send back the complete, modified code. The application will detect this, update the editor content, and automatically save the file.
- **Chat History:** Conversations are saved as `.json` files in a `.chats` folder inside the respective project directory, allowing you to resume previous conversations.
