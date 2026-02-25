import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import stat
import logging
from typing import List, Set, Optional
from dataclasses import dataclass
import time


# ============================================================================
# Constants
# ============================================================================
class Constants:
    """
    Application-wide constants

    CUSTOMIZATION GUIDE:
    To add files or folders you want to preserve during cleanup:
    1. Add them to the appropriate category below (or create a new category)
    2. Add your category to KEEP_LIST at the bottom
    3. Rebuild: pyinstaller UnityCleaner.spec

    Example:
        CUSTOM_PRESERVE = ['MyFolder', 'important.txt']
        KEEP_LIST = (... + CUSTOM_PRESERVE)
    """

    # ========================================
    # Unity Files
    # ========================================
    # Unity essential folders to preserve (DO NOT MODIFY unless you know what you're doing)
    UNITY_ESSENTIAL_FOLDERS = ['Assets', 'ProjectSettings', 'Packages']

    # Unity configuration files (ADD YOUR UNITY-RELATED FILES HERE)
    UNITY_CONFIG_FILES = ['.vsconfig', '.collabignore']

    # ========================================
    # Version Control Systems
    # ========================================
    # Git-related files to preserve (ADD YOUR GIT FILES HERE)
    GIT_FILES = ['.git', '.gitignore', '.gitattributes', '.gitmodules', '.gitkeep']
    GIT_FOLDERS = ['.github']

    # Other version control systems (ADD OTHER VCS HERE)
    VCS_FOLDERS = ['.svn', '.hg']

    # ========================================
    # Documentation & License
    # ========================================
    # Documentation files (ADD YOUR DOCS HERE)
    DOCUMENTATION_FILES = [
        'README.md', 'readme.md', 'README.txt', 'readme.txt',
        'LICENSE', 'LICENSE.md', 'LICENSE.txt',
        'CHANGELOG.md', 'CHANGELOG.txt',
        'CONTRIBUTING.md'
    ]

    # ========================================
    # CI/CD & Build Tools
    # ========================================
    # CI/CD configuration files (ADD YOUR CI/CD CONFIGS HERE)
    CICD_FILES = [
        '.gitlab-ci.yml', '.travis.yml', 'azure-pipelines.yml',
        'Jenkinsfile', '.appveyor.yml', 'catalog-info.yaml'
    ]
    CICD_FOLDERS = ['.circleci']

    # ========================================
    # Package Managers
    # ========================================
    # Package manager files (ADD YOUR PACKAGE FILES HERE)
    PACKAGE_FILES = [
        'package.json', 'package-lock.json',
        'yarn.lock', '.npmrc', '.yarnrc'
    ]

    # ========================================
    # IDE & Editor Settings
    # ========================================
    # IDE settings (lightweight, team-shared only)
    # Note: Heavy IDE folders like .idea/ and .vs/ are intentionally excluded
    IDE_SHARED = ['.vscode', '.editorconfig']

    # ========================================
    # CUSTOM ADDITIONS
    # ========================================
    # Add your custom files/folders here
    # CUSTOM_PRESERVE = ['MyFolder', 'important-file.txt']

    # ========================================
    # Combined Keep List (DO NOT FORGET TO ADD YOUR CUSTOM LIST HERE!)
    # ========================================
    KEEP_LIST = (
        UNITY_ESSENTIAL_FOLDERS +
        UNITY_CONFIG_FILES +
        GIT_FILES +
        GIT_FOLDERS +
        DOCUMENTATION_FILES +
        CICD_FILES +
        CICD_FOLDERS +
        PACKAGE_FILES +
        IDE_SHARED +
        VCS_FOLDERS
        # + CUSTOM_PRESERVE  # Uncomment and add your custom list here
    )

    # Performance settings
    MAX_WORKERS = 4

    # UI settings
    DEFAULT_WINDOW_SIZE = "500x600"
    STATUS_LABEL_WIDTH = 450
    LISTBOX_HEIGHT = 4

    # File settings
    LOG_FILE = "unitycleaner.log"
    CONFIG_FILE = "config.json"

    # System dangerous paths to protect
    DANGEROUS_PATHS_WINDOWS = ['C:\\Windows', 'C:\\Program Files', 'C:\\Program Files (x86)', 'C:\\System32']
    DANGEROUS_PATHS_UNIX = ['/usr', '/bin', '/sbin', '/etc', '/var', '/boot', '/sys', '/proc']


# ============================================================================
# Data Classes
# ============================================================================
@dataclass
class CleanupResult:
    """Result of a cleanup operation"""
    project_path: str
    deleted_count: int
    freed_bytes: int
    errors: List[str]
    was_interrupted: bool
    deleted_items: List[str]


@dataclass
class CleanupSummary:
    """Summary of all cleanup operations"""
    total_deleted: int
    total_freed_bytes: int
    total_errors: List[str]
    cleaned_projects: List[str]
    interrupted: bool

    @property
    def freed_mb(self) -> float:
        """Convert freed bytes to MB"""
        return self.freed_bytes / (1024 * 1024)

    @property
    def freed_gb(self) -> float:
        """Convert freed bytes to GB"""
        return self.freed_bytes / (1024 * 1024 * 1024)


# ============================================================================
# Logging Setup
# ============================================================================
def setup_logging() -> logging.Logger:
    """Configure logging system"""
    logger = logging.getLogger('UnityCleaner')
    logger.setLevel(logging.INFO)

    # File handler
    file_handler = logging.FileHandler(Constants.LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)

    # Add handler
    if not logger.handlers:
        logger.addHandler(file_handler)

    return logger


# ============================================================================
# Cleanup Engine (Business Logic)
# ============================================================================
class CleanupEngine:
    """Core cleanup logic separated from UI"""

    def __init__(self, logger: logging.Logger, stop_event: threading.Event):
        self.logger = logger
        self.stop_event = stop_event
        self.keep_list = Constants.KEEP_LIST

    def is_unity_project(self, path: str) -> bool:
        """
        Check if a directory is a Unity project.

        Args:
            path: Directory path to check

        Returns:
            True if path contains Assets and ProjectSettings folders
        """
        assets_path = os.path.join(path, 'Assets')
        project_settings_path = os.path.join(path, 'ProjectSettings')
        return (os.path.exists(assets_path) and os.path.isdir(assets_path) and
                os.path.exists(project_settings_path) and os.path.isdir(project_settings_path))

    def find_unity_projects(self, root_path: str, exclude_paths: Optional[Set[str]] = None) -> List[str]:
        """
        Recursively find all Unity projects in a directory.

        Args:
            root_path: Root directory to search
            exclude_paths: Set of normalized paths to exclude from search

        Returns:
            List of Unity project paths
        """
        exclude_paths = exclude_paths or set()
        projects = []

        # Check if root itself is a Unity project
        if self.is_unity_project(root_path):
            projects.append(root_path)
            self.logger.info(f"Found Unity project: {root_path}")
            return projects

        # Search recursively
        for root, dirs, _files in os.walk(root_path):
            if self.stop_event.is_set():
                break

            # Filter out excluded directories
            dirs[:] = [
                d for d in dirs
                if os.path.normpath(os.path.join(root, d)).lower() not in exclude_paths
            ]

            if self.is_unity_project(root):
                projects.append(root)
                self.logger.info(f"Found Unity project: {root}")
                # Skip searching inside Unity project folders
                dirs[:] = []

        return projects

    def get_size(self, path: str) -> int:
        """
        Calculate total size of a file or directory.

        Args:
            path: Path to file or directory

        Returns:
            Size in bytes
        """
        if os.path.isfile(path):
            try:
                return os.path.getsize(path)
            except (OSError, PermissionError):
                return 0

        total = 0
        try:
            for dirpath, _dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        if os.path.exists(fp) and not os.path.islink(fp):
                            total += os.path.getsize(fp)
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            pass

        return total

    def is_safe_to_delete(self, item_path: str, project_path: str) -> bool:
        """
        Verify if a path is safe to delete.

        Args:
            item_path: Path to check
            project_path: Unity project root path

        Returns:
            True if safe to delete
        """
        # Normalize paths
        item_path_norm = os.path.normpath(item_path)
        project_path_norm = os.path.normpath(project_path)

        # Must be inside project folder
        if not item_path_norm.startswith(project_path_norm):
            self.logger.warning(f"Unsafe: {item_path} is outside project {project_path}")
            return False

        # Check against dangerous system paths
        dangerous_paths = Constants.DANGEROUS_PATHS_WINDOWS if os.name == 'nt' else Constants.DANGEROUS_PATHS_UNIX
        for dangerous in dangerous_paths:
            if item_path_norm.startswith(dangerous):
                self.logger.warning(f"Unsafe: {item_path} is in dangerous path {dangerous}")
                return False

        return True

    def remove_readonly_onexc(self, func, path: str, _exc_info) -> None:
        """
        Error handler for shutil.rmtree to handle read-only files (onexc version).

        Args:
            func: Function that failed
            path: Path that caused the error
            _exc_info: Exception information tuple (unused but required by callback signature)
        """
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception as e:
            self.logger.error(f"Failed to remove readonly: {path} - {e}")

    def clean_single_project(
        self,
        project_path: str,
        normalized_custom_excludes: Optional[Set[str]] = None
    ) -> CleanupResult:
        """
        Clean unnecessary files from a single Unity project.

        Args:
            project_path: Path to Unity project
            normalized_custom_excludes: Set of normalized lowercase paths to exclude

        Returns:
            CleanupResult with deletion statistics and errors
        """
        if normalized_custom_excludes is None:
            normalized_custom_excludes = set()

        if self.stop_event.is_set():
            return CleanupResult(project_path, 0, 0, [], False, [])

        # If the project path itself is in the exclude list, skip
        norm_project_path = os.path.normpath(project_path).lower()
        if norm_project_path in normalized_custom_excludes:
            self.logger.info(f"Skipping excluded project: {project_path}")
            return CleanupResult(project_path, 0, 0, [], False, [])

        deleted_count = 0
        freed_bytes = 0
        errors = []
        deleted_items = []

        # Basic keep list (lowercase)
        basic_keep_set = {item.lower() for item in self.keep_list}

        self.logger.info(f"Starting cleanup: {project_path}")

        try:
            items = os.listdir(project_path)
            for item in items:
                if self.stop_event.is_set():
                    self.logger.info(f"Cleanup interrupted: {project_path}")
                    return CleanupResult(project_path, deleted_count, freed_bytes, errors, True, deleted_items)

                item_lower = item.lower()

                # Check basic keep list
                if item_lower in basic_keep_set:
                    continue

                item_path = os.path.join(project_path, item)
                norm_item_path = os.path.normpath(item_path).lower()

                # Check custom exclude list
                if item_lower in normalized_custom_excludes or norm_item_path in normalized_custom_excludes:
                    self.logger.info(f"Skipping excluded item: {item}")
                    continue

                # Safety check
                if not self.is_safe_to_delete(item_path, project_path):
                    errors.append(f"[{os.path.basename(project_path)}] {item}: Unsafe to delete")
                    continue

                try:
                    # Calculate size before deletion
                    item_size = self.get_size(item_path)

                    if os.path.isdir(item_path):
                        # Handle symbolic links safely
                        if os.path.islink(item_path):
                            os.unlink(item_path)
                            self.logger.info(f"Removed symlink: {item}")
                        else:
                            shutil.rmtree(item_path, onexc=self.remove_readonly_onexc)
                            self.logger.info(f"Removed directory: {item}")
                    else:
                        if not os.access(item_path, os.W_OK):
                            os.chmod(item_path, stat.S_IWRITE)
                        os.remove(item_path)
                        self.logger.info(f"Removed file: {item}")

                    deleted_count += 1
                    freed_bytes += item_size
                    deleted_items.append(item)

                except PermissionError as e:
                    error_msg = f"[{os.path.basename(project_path)}] {item}: Permission denied or in use"
                    errors.append(error_msg)
                    self.logger.error(f"PermissionError: {item_path} - {e}")

                except FileNotFoundError as e:
                    # Already deleted (concurrency issue), just log it
                    self.logger.warning(f"FileNotFoundError: {item_path} - already deleted")

                except OSError as e:
                    if hasattr(e, 'winerror') and e.winerror == 32:
                        error_msg = f"[{os.path.basename(project_path)}] {item}: File in use"
                    else:
                        error_msg = f"[{os.path.basename(project_path)}] {item}: OS error {e.errno}"
                    errors.append(error_msg)
                    self.logger.error(f"OSError: {item_path} - {e}")

                except Exception as e:
                    error_msg = f"[{os.path.basename(project_path)}] {item}: {type(e).__name__}"
                    errors.append(error_msg)
                    self.logger.error(f"Unexpected error: {item_path} - {e}", exc_info=True)

            self.logger.info(f"Cleanup completed: {project_path} - {deleted_count} items, {freed_bytes} bytes freed")
            return CleanupResult(project_path, deleted_count, freed_bytes, errors, False, deleted_items)

        except Exception as e:
            error_msg = f"[{os.path.basename(project_path)}] Folder access error: {str(e)}"
            self.logger.error(f"Project access error: {project_path} - {e}", exc_info=True)
            return CleanupResult(project_path, 0, 0, [error_msg], False, [])


# ============================================================================
# GUI Application
# ============================================================================
class UnityCleanerApp:
    """Main GUI application"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("UnityCleaner v2.0")
        self.root.geometry(Constants.DEFAULT_WINDOW_SIZE)
        self.root.resizable(False, False)

        # Setup logging
        self.logger = setup_logging()
        self.logger.info("=" * 60)
        self.logger.info("UnityCleaner started")

        # Cancellation event handler
        self.stop_event = threading.Event()
        self.is_running = False

        # Create cleanup engine
        self.engine = CleanupEngine(self.logger, self.stop_event)

        # Statistics tracking
        self.current_progress = 0
        self.total_progress = 0

        # Build UI
        self._build_ui()

        # Handling window closing event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _build_ui(self) -> None:
        """Build the user interface"""
        # Info label
        self.label_info = tk.Label(
            self.root,
            text="Select operation mode and folder.",
            pady=10,
            font=('Arial', 10)
        )
        self.label_info.pack()

        # Operation mode selection
        self.mode_var = tk.StringVar(value="single")
        self.radio_frame = tk.LabelFrame(
            self.root,
            text="Operation Mode",
            padx=10,
            pady=5,
            font=('Arial', 9, 'bold')
        )
        self.radio_frame.pack(pady=5, padx=20, fill="x")

        tk.Radiobutton(
            self.radio_frame,
            text="Clean Single Project",
            variable=self.mode_var,
            value="single",
            font=('Arial', 9)
        ).pack(anchor="w")

        tk.Radiobutton(
            self.radio_frame,
            text="Clean All Projects in Subfolders",
            variable=self.mode_var,
            value="recursive",
            font=('Arial', 9)
        ).pack(anchor="w")

        # Exclude folders management UI
        self.exclude_frame = tk.LabelFrame(
            self.root,
            text="Additional Exclusions (Folders)",
            padx=10,
            pady=5,
            font=('Arial', 9, 'bold')
        )
        self.exclude_frame.pack(pady=5, fill="x", padx=20)

        self.exclude_btn_frame = tk.Frame(self.exclude_frame)
        self.exclude_btn_frame.pack(fill="x")

        self.btn_add_folder = tk.Button(
            self.exclude_btn_frame,
            text="Add Folders",
            command=self.add_exclude_folder,
            font=('Arial', 9)
        )
        self.btn_add_folder.pack(side=tk.LEFT, expand=True, fill="x", padx=2)

        self.exclude_listbox_frame = tk.Frame(self.exclude_frame)
        self.exclude_listbox_frame.pack(fill="both", expand=True, pady=5)

        self.exclude_listbox = tk.Listbox(
            self.exclude_listbox_frame,
            height=Constants.LISTBOX_HEIGHT,
            font=('Arial', 8)
        )
        self.exclude_listbox.pack(side=tk.LEFT, fill="both", expand=True)

        self.scrollbar = tk.Scrollbar(self.exclude_listbox_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill="y")

        self.exclude_listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.exclude_listbox.yview)

        self.btn_remove_exclude = tk.Button(
            self.exclude_frame,
            text="Remove Selected",
            command=self.remove_exclude,
            font=('Arial', 9)
        )
        self.btn_remove_exclude.pack(anchor="e")

        # Progress bar
        self.progress_frame = tk.Frame(self.root)
        self.progress_frame.pack(pady=5, padx=20, fill="x")

        self.progress = ttk.Progressbar(
            self.progress_frame,
            length=400,
            mode='determinate'
        )
        self.progress.pack(fill="x")

        self.progress_label = tk.Label(
            self.progress_frame,
            text="0%",
            font=('Arial', 8)
        )
        self.progress_label.pack()

        # Status label
        self.status_label = tk.Label(
            self.root,
            text="Waiting...",
            fg="blue",
            wraplength=Constants.STATUS_LABEL_WIDTH,
            font=('Arial', 9),
            justify=tk.LEFT
        )
        self.status_label.pack(pady=5)

        # Detailed stats label
        self.stats_label = tk.Label(
            self.root,
            text="",
            fg="gray",
            font=('Arial', 8),
            justify=tk.LEFT
        )
        self.stats_label.pack(pady=2)

        # Button frame
        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(pady=10)

        self.btn_select = tk.Button(
            self.button_frame,
            text="Select Folder & Start",
            command=self.start_cleanup_thread,
            width=20,
            height=2,
            font=('Arial', 10, 'bold'),
            bg='#4CAF50',
            fg='white'
        )
        self.btn_select.pack(side=tk.LEFT, padx=5)

        self.btn_stop = tk.Button(
            self.button_frame,
            text="Stop",
            command=self.stop_cleanup,
            state=tk.DISABLED,
            width=10,
            height=2,
            font=('Arial', 10, 'bold'),
            bg='#f44336',
            fg='white'
        )
        self.btn_stop.pack(side=tk.LEFT, padx=5)

    def set_status(self, text: str, color: str = "black") -> None:
        """
        Update status label.

        Args:
            text: Status text to display
            color: Text color
        """
        self.status_label.config(text=text, fg=color)
        self.root.update_idletasks()

    def set_stats(self, text: str) -> None:
        """
        Update statistics label.

        Args:
            text: Statistics text to display
        """
        self.stats_label.config(text=text)
        self.root.update_idletasks()

    def update_progress(self, current: int, total: int, freed_bytes: int = 0) -> None:
        """
        Update progress bar and label.

        Args:
            current: Current progress value
            total: Total progress value
            freed_bytes: Total bytes freed so far
        """
        if total > 0:
            percentage = (current / total) * 100
            self.progress['value'] = percentage

            freed_mb = freed_bytes / (1024 * 1024)
            freed_gb = freed_bytes / (1024 * 1024 * 1024)

            if freed_gb >= 0.1:
                self.progress_label.config(text=f"{percentage:.1f}% | Freed: {freed_gb:.2f} GB")
            else:
                self.progress_label.config(text=f"{percentage:.1f}% | Freed: {freed_mb:.1f} MB")
        else:
            self.progress['value'] = 0
            self.progress_label.config(text="0%")

        self.root.update_idletasks()

    def add_exclude_folder(self) -> None:
        """Add folders to exclusion list"""
        added_count = 0
        while True:
            folder_path = filedialog.askdirectory(
                title=f"Select folder to exclude ({added_count} added so far, Cancel to stop)"
            )
            if not folder_path:
                break

            # Use absolute path for consistency
            folder_path = os.path.normpath(folder_path)
            if folder_path not in self.exclude_listbox.get(0, tk.END):
                self.exclude_listbox.insert(tk.END, folder_path)
                added_count += 1
                self.logger.info(f"Added exclude folder: {folder_path}")
            else:
                messagebox.showinfo("Notice", f"'{folder_path}' is already in the list.")

        if added_count > 0:
            messagebox.showinfo(
                "Notice",
                f"{added_count} folders have been added to the exclude list.\n"
                "These folders will be skipped entirely or preserved if found inside a project."
            )

    def remove_exclude(self) -> None:
        """Remove selected folders from exclusion list"""
        selection = self.exclude_listbox.curselection()
        if selection:
            for index in reversed(selection):
                removed = self.exclude_listbox.get(index)
                self.exclude_listbox.delete(index)
                self.logger.info(f"Removed exclude folder: {removed}")

    def start_cleanup_thread(self) -> None:
        """Start cleanup process in a separate thread"""
        root_path = filedialog.askdirectory(title="Select Folder")
        if not root_path:
            return

        mode = self.mode_var.get()
        target_projects = []

        if mode == "single":
            if self.engine.is_unity_project(root_path):
                target_projects.append(root_path)
            else:
                messagebox.showwarning(
                    "Warning",
                    "The selected folder is not a Unity project.\n"
                    "(Requires Assets and ProjectSettings folders)"
                )
                return
        else:
            self.set_status("Searching for Unity projects...", "blue")

            # Get exclude list for filtering
            custom_excludes = list(self.exclude_listbox.get(0, tk.END))
            normalized_excludes = {os.path.normpath(ex).lower() for ex in custom_excludes}

            target_projects = self.engine.find_unity_projects(root_path, normalized_excludes)

            if not target_projects:
                messagebox.showinfo("Notice", "No Unity projects found in subfolders.")
                self.set_status("Waiting...", "blue")
                return

        msg = f"Selected Path: {root_path}\n"
        if mode == "recursive":
            msg += f"Projects Found: {len(target_projects)}\n"
        msg += "\nDo you want to delete all items except essential folders?"

        if not messagebox.askyesno("Confirm", msg):
            if mode == "recursive":
                self.set_status("Waiting...", "blue")
            return

        # Thread setup
        self.stop_event.clear()
        self.is_running = True
        self.btn_select.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.progress['value'] = 0

        # Get current exclude list
        custom_excludes = list(self.exclude_listbox.get(0, tk.END))

        self.logger.info(f"Starting cleanup thread for {len(target_projects)} projects")

        threading.Thread(
            target=self.run_cleanup_multi,
            args=(target_projects, custom_excludes),
            daemon=True
        ).start()

    def stop_cleanup(self) -> None:
        """Request to stop the cleanup process"""
        if self.is_running:
            if messagebox.askyesno("Confirm", "Do you want to stop the cleanup process?"):
                self.stop_event.set()
                self.set_status("Requesting stop...", "orange")
                self.logger.info("User requested stop")

    def on_closing(self) -> None:
        """Handle window closing event"""
        if self.is_running:
            if messagebox.askyesno("Confirm", "Cleanup is in progress. Are you sure you want to exit?"):
                self.stop_event.set()
                self.logger.info("Application closed during cleanup")
                self.root.destroy()
        else:
            self.logger.info("Application closed normally")
            self.root.destroy()

    def run_cleanup_multi(self, target_projects: List[str], custom_excludes: List[str] = None) -> None:
        """
        Run cleanup on multiple projects with multi-threading.

        Args:
            target_projects: List of Unity project paths to clean
            custom_excludes: List of custom exclusion paths
        """
        import concurrent.futures

        if custom_excludes is None:
            custom_excludes = []

        total_deleted = 0
        total_freed_bytes = 0
        total_errors = []
        cleaned_projects = []
        interrupted = False

        # Pre-normalize excludes for faster lookup
        normalized_custom_excludes = {os.path.normpath(ex).lower() for ex in custom_excludes}

        self.logger.info(f"Starting multi-threaded cleanup: {len(target_projects)} projects")
        start_time = time.time()

        try:
            # Use multi-threading for better performance
            max_workers = min(len(target_projects), Constants.MAX_WORKERS)

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all cleanup tasks
                future_to_project = {
                    executor.submit(self.engine.clean_single_project, p, normalized_custom_excludes): p
                    for p in target_projects
                }

                completed = 0
                for future in concurrent.futures.as_completed(future_to_project):
                    if self.stop_event.is_set():
                        interrupted = True
                        self.logger.info("Cleanup interrupted by user")
                        break

                    project_path = future_to_project[future]
                    project_name = os.path.basename(project_path)

                    completed += 1

                    try:
                        result: CleanupResult = future.result()

                        total_deleted += result.deleted_count
                        total_freed_bytes += result.freed_bytes
                        total_errors.extend(result.errors)

                        if result.deleted_count > 0:
                            cleaned_projects.append(project_path)

                        if result.was_interrupted:
                            interrupted = True

                        # Update UI with detailed progress
                        freed_mb = result.freed_bytes / (1024 * 1024)
                        status_text = (
                            f"[{completed}/{len(target_projects)}] {project_name}\n"
                            f"Items: {result.deleted_count} | Freed: {freed_mb:.1f} MB"
                        )
                        self.set_status(status_text, "red")

                        # Update overall statistics
                        total_freed_mb = total_freed_bytes / (1024 * 1024)
                        total_freed_gb = total_freed_bytes / (1024 * 1024 * 1024)

                        if total_freed_gb >= 0.1:
                            stats_text = f"Total: {total_deleted} items | {total_freed_gb:.2f} GB freed"
                        else:
                            stats_text = f"Total: {total_deleted} items | {total_freed_mb:.1f} MB freed"

                        self.set_stats(stats_text)
                        self.update_progress(completed, len(target_projects), total_freed_bytes)

                    except Exception as e:
                        error_msg = f"[{project_name}] Execution error: {str(e)}"
                        total_errors.append(error_msg)
                        self.logger.error(f"Future execution error: {project_path} - {e}", exc_info=True)

            # Calculate elapsed time
            elapsed_time = time.time() - start_time

            # Show results
            if interrupted:
                self.set_status("Task Interrupted", "orange")
                messagebox.showwarning("Interrupted", "Cleanup process was interrupted by user.")
                self.logger.info(f"Cleanup interrupted after {elapsed_time:.2f} seconds")
            else:
                self.set_status("Task Completed", "green")

                # Prepare result message
                freed_mb = total_freed_bytes / (1024 * 1024)
                freed_gb = total_freed_bytes / (1024 * 1024 * 1024)

                if freed_gb >= 0.1:
                    freed_str = f"{freed_gb:.2f} GB"
                else:
                    freed_str = f"{freed_mb:.1f} MB"

                result_msg = (
                    f"Cleanup complete!\n\n"
                    f"Total items deleted: {total_deleted}\n"
                    f"Space freed: {freed_str}\n"
                    f"Time elapsed: {elapsed_time:.1f} seconds"
                )

                if len(target_projects) > 1:
                    result_msg = (
                        f"{len(cleaned_projects)} out of {len(target_projects)} projects cleaned.\n\n"
                        + result_msg
                    )

                    if cleaned_projects:
                        project_list_str = "\n".join([
                            f"- {os.path.basename(p)}"
                            for p in cleaned_projects[:10]
                        ])
                        if len(cleaned_projects) > 10:
                            project_list_str += f"\n...and {len(cleaned_projects)-10} more"
                        result_msg += f"\n\n[Cleaned Projects]:\n{project_list_str}"

                if total_errors:
                    error_summary = "\n".join(total_errors[:5])
                    if len(total_errors) > 5:
                        error_summary += f"\n...and {len(total_errors)-5} more errors"
                    messagebox.showinfo(
                        "Completed with Errors",
                        f"{result_msg}\n\n[Errors Encountered]:\n{error_summary}"
                    )
                else:
                    messagebox.showinfo("Completed", result_msg)

                self.logger.info(
                    f"Cleanup completed: {total_deleted} items, "
                    f"{freed_str} freed in {elapsed_time:.2f} seconds"
                )

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during process:\n{str(e)}")
            self.set_status("Error Occurred", "red")
            self.logger.error(f"Critical error during cleanup: {e}", exc_info=True)

        finally:
            self.is_running = False
            self.btn_select.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
            if not interrupted:
                self.set_status("Waiting...", "blue")


# ============================================================================
# Main Entry Point
# ============================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = UnityCleanerApp(root)
    root.mainloop()
