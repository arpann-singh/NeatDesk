import os
import shutil
import threading
import hashlib
import logging
from tkinter import (
    Tk, Label, Button, Frame, filedialog, Listbox, Scrollbar, 
    messagebox, ttk, StringVar, END, VERTICAL, HORIZONTAL, BOTH, RIGHT, LEFT, Y, X
)

# -----------------------
# Configuration & Globals
# -----------------------

# File categories by extension (add more as needed)
FILE_CATEGORIES = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"],
    "Documents": [".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx"],
    "Videos": [".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv"],
    "Music": [".mp3", ".wav", ".aac", ".flac"],
    "Archives": [".zip", ".rar", ".tar", ".gz", ".7z"],
    "Scripts": [".py", ".js", ".sh", ".bat", ".pl"],
    "Executables": [".exe", ".msi", ".bin", ".apk"],
    "Others": []
}

# Logging setup
logging.basicConfig(
    filename='file_organizer.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# -----------------------
# Utility Functions
# -----------------------

def get_file_hash(filepath, block_size=65536):
    """Calculate SHA256 hash of a file for duplicate detection."""
    sha = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            while True:
                data = f.read(block_size)
                if not data:
                    break
                sha.update(data)
    except Exception as e:
        logging.warning(f"Cannot read file for hashing: {filepath}, {e}")
        return None
    return sha.hexdigest()

def get_category(filename):
    """Get the category folder for a given filename based on extension."""
    ext = os.path.splitext(filename)[1].lower()
    for category, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            return category
    return "Others"

def safe_move_file(src, dest_folder):
    """Move a file to destination folder, handling duplicate names by renaming."""
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    filename = os.path.basename(src)
    dest_path = os.path.join(dest_folder, filename)

    # If file exists, rename
    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(dest_path):
        dest_path = os.path.join(dest_folder, f"{base}({counter}){ext}")
        counter += 1
    shutil.move(src, dest_path)
    return dest_path

def remove_empty_folders(folder):
    """Recursively remove empty folders."""
    removed_count = 0
    for root, dirs, files in os.walk(folder, topdown=False):
        for d in dirs:
            full_path = os.path.join(root, d)
            try:
                if not os.listdir(full_path):
                    os.rmdir(full_path)
                    removed_count += 1
            except Exception as e:
                logging.warning(f"Failed to remove folder {full_path}: {e}")
    return removed_count

# -----------------------
# Core Organizer Class
# -----------------------

class FileOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("File Organizer")
        self.root.geometry("700x500")

        self.selected_folder = StringVar()
        self.status_text = StringVar()
        self.file_list = []
        self.preview_moves = []

        self.setup_ui()

    def setup_ui(self):
        # Folder selection frame
        folder_frame = Frame(self.root)
        folder_frame.pack(pady=10, padx=10, fill=X)

        Label(folder_frame, text="Select Folder to Organize:").pack(side=LEFT)
        self.folder_label = Label(folder_frame, textvariable=self.selected_folder, fg="blue")
        self.folder_label.pack(side=LEFT, padx=10)
        Button(folder_frame, text="Browse", command=self.browse_folder).pack(side=LEFT)

        # Action buttons frame
        btn_frame = Frame(self.root)
        btn_frame.pack(pady=10, padx=10, fill=X)

        self.scan_btn = Button(btn_frame, text="Scan Folder", command=self.scan_folder)
        self.scan_btn.pack(side=LEFT, padx=5)

        self.preview_btn = Button(btn_frame, text="Show Preview", state='disabled', command=self.show_preview)
        self.preview_btn.pack(side=LEFT, padx=5)

        self.organize_btn = Button(btn_frame, text="Organize Files", state='disabled', command=self.organize_files)
        self.organize_btn.pack(side=LEFT, padx=5)

        self.clean_btn = Button(btn_frame, text="Clean Empty Folders", state='disabled', command=self.clean_empty_folders)
        self.clean_btn.pack(side=LEFT, padx=5)

        # Progress bar
        self.progress = ttk.Progressbar(self.root, orient=HORIZONTAL, length=600, mode='determinate')
        self.progress.pack(pady=10)

        # Status label
        self.status_label = Label(self.root, textvariable=self.status_text, fg="green")
        self.status_label.pack(pady=5)

        # Preview Listbox with scrollbar
        preview_frame = Frame(self.root)
        preview_frame.pack(pady=10, padx=10, fill=BOTH, expand=True)

        self.preview_listbox = Listbox(preview_frame)
        self.preview_listbox.pack(side=LEFT, fill=BOTH, expand=True)

        scrollbar = Scrollbar(preview_frame, orient=VERTICAL)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.preview_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.preview_listbox.yview)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.selected_folder.set(folder)
            self.status_text.set(f"Selected folder: {folder}")
            self.file_list = []
            self.preview_moves = []
            self.preview_listbox.delete(0, END)
            self.preview_btn.config(state='disabled')
            self.organize_btn.config(state='disabled')
            self.clean_btn.config(state='disabled')

    def scan_folder(self):
        folder = self.selected_folder.get()
        if not folder or not os.path.exists(folder):
            messagebox.showerror("Error", "Please select a valid folder!")
            return

        self.status_text.set("Scanning folder, please wait...")
        self.preview_listbox.delete(0, END)
        self.file_list = []

        def scan():
            for root, dirs, files in os.walk(folder):
                for file in files:
                    filepath = os.path.join(root, file)
                    self.file_list.append(filepath)

            self.status_text.set(f"Scan complete: {len(self.file_list)} files found.")
            self.preview_btn.config(state='normal')
            self.organize_btn.config(state='disabled')
            self.clean_btn.config(state='disabled')

        threading.Thread(target=scan, daemon=True).start()

    def show_preview(self):
        if not self.file_list:
            messagebox.showinfo("No files", "No files to preview. Please scan first.")
            return

        self.preview_listbox.delete(0, END)
        self.preview_moves = []

        folder = self.selected_folder.get()
        total = len(self.file_list)
        self.progress['maximum'] = total
        self.progress['value'] = 0
        self.status_text.set("Generating preview...")

        for idx, filepath in enumerate(self.file_list):
            filename = os.path.basename(filepath)
            category = get_category(filename)
            dest_folder = os.path.join(folder, category)
            dest_path = os.path.join(dest_folder, filename)

            # Handle duplicate names in preview (simulate renaming)
            base, ext = os.path.splitext(filename)
            counter = 1
            while any(move[1] == dest_path for move in self.preview_moves):
                dest_path = os.path.join(dest_folder, f"{base}({counter}){ext}")
                counter += 1

            self.preview_moves.append((filepath, dest_path))
            display_text = f"{filepath}  -->  {dest_path}"
            self.preview_listbox.insert(END, display_text)
            self.progress['value'] = idx + 1
            self.root.update_idletasks()

        self.status_text.set(f"Preview ready: {total} files will be moved.")
        self.organize_btn.config(state='normal')
        self.clean_btn.config(state='disabled')

    def organize_files(self):
        if not self.preview_moves:
            messagebox.showinfo("No preview", "Please generate preview before organizing.")
            return

        folder = self.selected_folder.get()
        total = len(self.preview_moves)
        self.progress['maximum'] = total
        self.progress['value'] = 0
        self.status_text.set("Organizing files, please wait...")

        def organize():
            success_count = 0
            for idx, (src, dest) in enumerate(self.preview_moves):
                try:
                    dest_folder = os.path.dirname(dest)
                    if not os.path.exists(dest_folder):
                        os.makedirs(dest_folder)

                    # If file exists (should not happen because preview handled duplicates), rename:
                    final_dest = dest
                    base, ext = os.path.splitext(os.path.basename(dest))
                    counter = 1
                    while os.path.exists(final_dest):
                        final_dest = os.path.join(dest_folder, f"{base}({counter}){ext}")
                        counter += 1

                    shutil.move(src, final_dest)
                    success_count += 1
                    logging.info(f"Moved: {src} -> {final_dest}")
                except Exception as e:
                    logging.error(f"Failed to move {src} -> {dest}: {e}")

                self.progress['value'] = idx + 1
                self.root.update_idletasks()

            self.status_text.set(f"Organizing complete. {success_count}/{total} files moved.")
            self.clean_btn.config(state='normal')
            self.organize_btn.config(state='disabled')
            self.preview_btn.config(state='disabled')

        threading.Thread(target=organize, daemon=True).start()

    def clean_empty_folders(self):
        folder = self.selected_folder.get()
        if not folder or not os.path.exists(folder):
            messagebox.showerror("Error", "Please select a valid folder!")
            return

        self.status_text.set("Cleaning empty folders...")

        def clean():
            removed = remove_empty_folders(folder)
            self.status_text.set(f"Cleaned {removed} empty folders.")
            self.clean_btn.config(state='disabled')

        threading.Thread(target=clean, daemon=True).start()

# -----------------------
# Main Execution
# -----------------------

def main():
    root = Tk()
    app = FileOrganizerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
# This script is a simple file organizer GUI application using Tkinter.
# It allows users to select a folder, scan for files, preview the organization,
# and move files into categorized folders based on their extensions.
# It also cleans up empty folders after the organization process.
# The application uses threading to keep the UI responsive during long operations.
# Logging is implemented to track file movements and errors.
# The script is designed to be user-friendly and provides feedback through status messages.
# The file categories and extensions can be easily modified in the FILE_CATEGORIES dictionary.
# The application is structured with a main class (FileOrganizerApp) that handles the UI and logic.
# The utility functions are defined separately for better organization and readability.
# The script is intended for educational purposes and can be further enhanced with additional features.
# For example, adding more file categories, improving error handling,
# or implementing a more sophisticated duplicate file detection mechanism.
# The GUI is designed to be simple and intuitive, making it accessible for users with varying levels of technical expertise.
# The application can be run directly, and it will open a window for user interaction.
# The script is self-contained and does not require any external dependencies beyond the standard library.
# The use of threading ensures that the application remains responsive,
# even when performing potentially time-consuming operations like scanning and moving files.
# The progress bar provides visual feedback on the status of file operations,
# enhancing the user experience.
# The application can be further improved by adding features such as:
# - Customizable file categories and extensions
# - A settings menu for user preferences
# - A help section with usage instructions
# - Support for undoing the last operation
# - Integration with cloud storage services for file organization
# - A more advanced duplicate file detection and merging system
# - A search function to quickly find files within the selected folder
# - The ability to filter files by size, date, or other criteria
# - A dark mode or theme customization option
# - Support for multiple languages
# - A command-line interface for advanced users
# - A logging system that allows users to view past operations and errors 
# - A backup feature to save original files before moving them
# - A batch processing feature to organize multiple folders at once
# - A file preview feature to view images or documents before moving
# - A context menu integration for right-clicking files in the file explorer
# - A built-in file viewer for quick access to files without opening external applications
# - A file compression feature to zip files before moving them
# - A file encryption feature for sensitive files
# - A user authentication system for added security
# - A built-in file renamer for batch renaming files
# - A built-in file converter for changing file formats
# - A built-in file splitter for large files
# - A built-in file merger for combining multiple files into one
# - A built-in file compressor for reducing file size
# - A built-in file extractor for decompressing files
# - A built-in file shredder for securely deleting files

