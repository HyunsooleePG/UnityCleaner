import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import stat

class UnityCleanerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("UnityCleaner")
        self.root.geometry("400x520")
        self.root.resizable(False, False)

        # Cancellation event handler
        self.stop_event = threading.Event()
        self.is_running = False

        # UI Elements
        self.label_info = tk.Label(root, text="Select operation mode and folder.", pady=10)
        self.label_info.pack()

        # Operation mode selection
        self.mode_var = tk.StringVar(value="single")
        self.radio_frame = tk.LabelFrame(root, text="Operation Mode", padx=10, pady=5)
        self.radio_frame.pack(pady=5)

        tk.Radiobutton(self.radio_frame, text="Clean Single Project", variable=self.mode_var, value="single").pack(anchor="w")
        tk.Radiobutton(self.radio_frame, text="Clean All Projects in Subfolders", variable=self.mode_var, value="recursive").pack(anchor="w")

        # Exclude folders management UI
        self.exclude_frame = tk.LabelFrame(root, text="Additional Exclusions (Folders)", padx=10, pady=5)
        self.exclude_frame.pack(pady=5, fill="x", padx=20)

        self.exclude_btn_frame = tk.Frame(self.exclude_frame)
        self.exclude_btn_frame.pack(fill="x")

        self.btn_add_folder = tk.Button(self.exclude_btn_frame, text="Add Folders", command=self.add_exclude_folder)
        self.btn_add_folder.pack(side=tk.LEFT, expand=True, fill="x", padx=2)

        self.exclude_listbox_frame = tk.Frame(self.exclude_frame)
        self.exclude_listbox_frame.pack(fill="both", expand=True, pady=5)

        self.exclude_listbox = tk.Listbox(self.exclude_listbox_frame, height=4)
        self.exclude_listbox.pack(side=tk.LEFT, fill="both", expand=True)
        
        self.scrollbar = tk.Scrollbar(self.exclude_listbox_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill="y")
        
        self.exclude_listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.exclude_listbox.yview)

        self.btn_remove_exclude = tk.Button(self.exclude_frame, text="Remove Selected", command=self.remove_exclude)
        self.btn_remove_exclude.pack(anchor="e")

        self.status_label = tk.Label(root, text="Waiting...", fg="blue", wraplength=350)
        self.status_label.pack(pady=5)

        self.button_frame = tk.Frame(root)
        self.button_frame.pack(pady=10)

        self.btn_select = tk.Button(self.button_frame, text="Select Folder & Start", command=self.start_cleanup_thread, width=20, height=2)
        self.btn_select.pack(side=tk.LEFT, padx=5)

        self.btn_stop = tk.Button(self.button_frame, text="Stop", command=self.stop_cleanup, state=tk.DISABLED, width=10, height=2)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        self.keep_list = ['Assets', 'ProjectSettings', 'Packages', '.git', '.gitignore', '.gitattributes']

        # Handling window closing event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def set_status(self, text, color="black"):
        self.status_label.config(text=text, fg=color)
        self.root.update_idletasks()

    def add_exclude_folder(self):
        # Tkinter's standard dialog doesn't support multiple directory selection at once.
        # To improve UX, we allow consecutive selection until the user cancels.
        added_count = 0
        while True:
            folder_path = filedialog.askdirectory(title=f"Select folder to exclude ({added_count} added so far, Cancel to stop)")
            if not folder_path:
                break
            
            # Use absolute path for consistency and accurate matching.
            folder_path = os.path.normpath(folder_path)
            if folder_path not in self.exclude_listbox.get(0, tk.END):
                self.exclude_listbox.insert(tk.END, folder_path)
                added_count += 1
            else:
                messagebox.showinfo("Notice", f"'{folder_path}' is already in the list.")
        
        if added_count > 0:
            messagebox.showinfo("Notice", f"{added_count} folders have been added to the exclude list.\nThese folders will be skipped entirely or preserved if found inside a project.")

    def remove_exclude(self):
        selection = self.exclude_listbox.curselection()
        if selection:
            for index in reversed(selection):
                self.exclude_listbox.delete(index)

    def is_unity_project(self, path):
        assets_path = os.path.join(path, 'Assets')
        project_settings_path = os.path.join(path, 'ProjectSettings')
        return (os.path.exists(assets_path) and os.path.isdir(assets_path) and
                os.path.exists(project_settings_path) and os.path.isdir(project_settings_path))

    def find_unity_projects(self, root_path):
        projects = []
        if self.is_unity_project(root_path):
            projects.append(root_path)
            return projects

        for root, dirs, files in os.walk(root_path):
            if self.is_unity_project(root):
                projects.append(root)
                # Skip searching inside unity project folders
                dirs[:] = [] 
        return projects

    def start_cleanup_thread(self):
        root_path = filedialog.askdirectory(title="Select Folder")
        if not root_path:
            return

        mode = self.mode_var.get()
        target_projects = []

        if mode == "single":
            if self.is_unity_project(root_path):
                target_projects.append(root_path)
            else:
                messagebox.showwarning("Warning", "The selected folder is not a Unity project.\n(Requires Assets and ProjectSettings folders)")
                return
        else:
            self.set_status("Searching for Unity projects...", "blue")
            target_projects = self.find_unity_projects(root_path)
            if not target_projects:
                messagebox.showinfo("Notice", "No Unity projects found in subfolders.")
                self.set_status("Waiting...", "blue")
                return

        msg = f"Selected Path: {root_path}\n"
        if mode == "recursive":
            msg += f"Projects Found: {len(target_projects)}\n"
        msg += "\nDo you want to delete all items except essential folders?"

        if not messagebox.askyesno("Confirm", msg):
            if mode == "recursive": self.set_status("Waiting...", "blue")
            return

        # Thread setup
        self.stop_event.clear()
        self.is_running = True
        self.btn_select.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        
        # Get current exclude list
        custom_excludes = list(self.exclude_listbox.get(0, tk.END))
        
        threading.Thread(target=self.run_cleanup_multi, args=(target_projects, custom_excludes), daemon=True).start()

    def stop_cleanup(self):
        if self.is_running:
            if messagebox.askyesno("Confirm", "Do you want to stop the cleanup process?"):
                self.stop_event.set()
                self.set_status("Requesting stop...", "orange")

    def on_closing(self):
        if self.is_running:
            if messagebox.askyesno("Confirm", "Cleanup is in progress. Are you sure you want to exit?"):
                self.stop_event.set()
                self.root.destroy()
        else:
            self.root.destroy()

    def remove_readonly(self, func, path, excinfo):
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass

    def clean_single_project(self, project_path, normalized_custom_excludes=set()):
        """Internal function to delete unnecessary files in a single project"""
        if self.stop_event.is_set():
            return 0, [], False

        # If the project path itself is in the exclude list, skip the operation
        norm_project_path = os.path.normpath(project_path).lower()
        if norm_project_path in normalized_custom_excludes:
            return 0, [], False

        deleted_count = 0
        errors = []
        
        # Basic keep list (lowercase conversion)
        basic_keep_set = {item.lower() for item in self.keep_list}

        try:
            items = os.listdir(project_path)
            for item in items:
                if self.stop_event.is_set():
                    return deleted_count, errors, True
                
                item_lower = item.lower()

                # 1. Check basic keep list
                if item_lower in basic_keep_set:
                    continue
                
                item_path = os.path.join(project_path, item)
                norm_item_path = os.path.normpath(item_path).lower()

                # 2. Check custom exclude list (matching by name or full path)
                if item_lower in normalized_custom_excludes or norm_item_path in normalized_custom_excludes:
                    continue
                
                try:
                    if os.path.isdir(item_path):
                        # Double check before using rmtree (against edge cases like symbolic links)
                        shutil.rmtree(item_path, onerror=self.remove_readonly)
                    else:
                        if not os.access(item_path, os.W_OK):
                            os.chmod(item_path, stat.S_IWRITE)
                        os.remove(item_path)
                    deleted_count += 1
                except PermissionError:
                    errors.append(f"[{os.path.basename(project_path)}] {item}: In use or Access Denied")
                except Exception as e:
                    errors.append(f"[{os.path.basename(project_path)}] {item}: {str(e)}")
            
            return deleted_count, errors, False
        except Exception as e:
            return 0, [f"[{os.path.basename(project_path)}] Folder Access Error: {str(e)}"], False

    def run_cleanup_multi(self, target_projects, custom_excludes=[]):
        import concurrent.futures
        
        total_deleted = 0
        total_errors = []
        cleaned_projects = []
        interrupted = False
        
        # Pre-normalize excludes for faster lookup
        normalized_custom_excludes = {os.path.normpath(ex).lower() for ex in custom_excludes}

        try:
            # Improve speed with multi-threading for multiple projects.
            # Limited to 4 workers to avoid disk I/O bottlenecks.
            max_workers = min(len(target_projects), 4)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Register cleanup tasks
                future_to_project = {executor.submit(self.clean_single_project, p, normalized_custom_excludes): p for p in target_projects}
                
                for i, future in enumerate(concurrent.futures.as_completed(future_to_project)):
                    if self.stop_event.is_set():
                        interrupted = True
                        break
                        
                    project_path = future_to_project[future]
                    self.set_status(f"[{i+1}/{len(target_projects)}] Cleaning: {os.path.basename(project_path)}", "red")
                    
                    try:
                        deleted, errors, was_interrupted = future.result()
                        total_deleted += deleted
                        total_errors.extend(errors)
                        if deleted > 0:
                            cleaned_projects.append(project_path)
                        if was_interrupted:
                            interrupted = True
                    except Exception as e:
                        total_errors.append(f"[{os.path.basename(project_path)}] Execution Error: {str(e)}")

            if interrupted:
                self.set_status("Task Interrupted", "orange")
                messagebox.showwarning("Interrupted", "Cleanup process was interrupted by user.")
            else:
                self.set_status("Task Completed", "blue")
                
                result_msg = f"Cleanup complete.\nTotal items deleted: {total_deleted}\n"
                
                if len(target_projects) > 1:
                    result_msg = f"{len(cleaned_projects)} out of {len(target_projects)} projects cleaned.\n" + result_msg
                    
                    if cleaned_projects:
                        project_list_str = "\n".join([f"- {os.path.basename(p)}" for p in cleaned_projects[:10]])
                        if len(cleaned_projects) > 10:
                            project_list_str += f"\n...and {len(cleaned_projects)-10} more"
                        result_msg += f"\n[Cleaned Project List]:\n{project_list_str}"

                if total_errors:
                    error_summary = "\n".join(total_errors[:5])
                    if len(total_errors) > 5:
                        error_summary += f"\n...and {len(total_errors)-5} more errors"
                    messagebox.showinfo("Completed", f"{result_msg}\n\nSome errors occurred:\n{error_summary}")
                else:
                    messagebox.showinfo("Completed", result_msg)

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during process: {str(e)}")
            self.set_status("Error Occurred", "orange")
        finally:
            self.is_running = False
            self.btn_select.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
            if not interrupted:
                self.set_status("Waiting...", "blue")

if __name__ == "__main__":
    root = tk.Tk()
    app = UnityCleanerApp(root)
    root.mainloop()
