# UnityCleaner v2.0

UnityCleaner is a simple and efficient automation tool designed to optimize Unity project sizes by removing unnecessary files and folders while preserving core project data.

## Features

### Core Functionality
- **Project Optimization**: Automatically deletes heavy cache and temporary folders (`Library`, `Temp`, `Logs`, etc.) and IDE-generated files (`.csproj`, `.sln`).
- **Smart Preservation**: Safely keeps essential files and folders:
  - Unity folders: `Assets`, `ProjectSettings`, `Packages`
  - Unity config: `.vsconfig`, `.collabignore`
  - Git files: `.git`, `.gitignore`, `.gitattributes`, `.gitmodules`, `.github/`
  - Documentation: `README.md`, `LICENSE`, `CHANGELOG.md`, etc.
  - CI/CD configs: `.gitlab-ci.yml`, `.travis.yml`, `Jenkinsfile`, `catalog-info.yaml`, etc.
  - Package managers: `package.json`, `yarn.lock`, etc.
  - Team IDE settings: `.vscode/`, `.editorconfig`
- **Two Operation Modes**:
  - **Clean Single Project**: Targets one specific Unity project.
  - **Clean All Projects in Subfolders**: Recursively searches for and cleans all Unity projects found within a specified directory.
- **Custom Exclusions**: Allows users to specify additional folders to be skipped during the cleaning process.

### New in v2.0
- **Enhanced Performance**: Multi-threaded cleanup with up to 4 concurrent workers for faster processing.
- **Detailed Progress Tracking**: Real-time progress bar showing percentage, freed space (MB/GB), and elapsed time.
- **Size Tracking**: See exactly how much disk space you're freeing up (displayed in MB or GB).
- **Advanced Logging**: Comprehensive logging system saves all operations to `unitycleaner.log` for troubleshooting.
- **Improved Safety**:
  - Symbolic link detection and safe handling
  - Path validation to prevent accidental deletion of system folders
  - Enhanced read-only file handling
- **Better Error Handling**: Specific error messages for different failure types (permission denied, file in use, etc.).
- **Optimized Architecture**: Separated business logic (CleanupEngine) from UI for better maintainability and testability.
- **Type Hints**: Full type annotations for better code quality and IDE support.

## How to Use

### Windows
1. **Run the Application**: Open `UnityCleaner.exe` in the `dist` folder.
2. **Select Mode**: Choose between "Clean Single Project" or "Clean All Projects in Subfolders".
3. **Add Exclusions (Optional)**:
   - Click **"Add Folders"** to select folders you want to protect.
   - **Note**: To make adding multiple folders easier, the folder selection window will keep appearing until you click the **"Cancel"** button. This allows you to pick several directories in a row without having to click the "Add" button repeatedly.
4. **Start Cleanup**: Click **"Select Folder & Start"**.
5. **Select Target**: Choose the project folder or the parent directory containing multiple projects.
6. **Confirm**: Review the target information in the popup and click **"Yes"** to begin.
7. **Monitor Progress**:
   - Watch the **progress bar** for completion percentage and freed space.
   - View **detailed status** showing current project being cleaned.
   - See **total statistics** including items deleted and space freed.
   - Use the **"Stop"** button if you need to cancel the operation.
8. **View Results**: Once complete, a summary report will show:
   - Total items deleted
   - Total space freed (in MB or GB)
   - Time elapsed
   - List of cleaned projects
   - Any errors encountered

### macOS
1. **Run the Script**: Open Terminal and run `python3 main.py`. (Or open the built `.app` if available).
2. **Follow the same steps** as the Windows version from step 2 to 8.

## System Requirements
- **Windows**: Standalone `.exe` provided (No Python installation required).
- **macOS**: Python 3.x required (Run from source or build into `.app` via PyInstaller).
- **Python 3.x**: Required if running from source (Python 3.7+ recommended for type hints support).

## What Gets Preserved

UnityCleaner intelligently preserves important files and folders while cleaning your Unity projects:

### Unity Files
- **Core folders**: `Assets`, `ProjectSettings`, `Packages`
- **Config files**: `.vsconfig`, `.collabignore`

### Version Control
- **Git**: `.git`, `.gitignore`, `.gitattributes`, `.gitmodules`, `.gitkeep`, `.github/`
- **Other VCS**: `.svn/`, `.hg/`

### Documentation & License
- `README.md`, `readme.md`, `README.txt`
- `LICENSE`, `LICENSE.md`, `LICENSE.txt`
- `CHANGELOG.md`, `CONTRIBUTING.md`

### CI/CD Configurations
- `.gitlab-ci.yml`, `.travis.yml`, `azure-pipelines.yml`
- `Jenkinsfile`, `.appveyor.yml`
- `.circleci/`
- `catalog-info.yaml` - Backstage/Developer Portal metadata

### Package Managers
- `package.json`, `package-lock.json`
- `yarn.lock`, `.npmrc`, `.yarnrc`

### Team IDE Settings
- `.vscode/` - Lightweight and team-shareable
- `.editorconfig` - Code style configuration

### What Gets Deleted
Everything else in the project folder gets removed, including:
- `Library/` - Unity's cache (can be regenerated)
- `Temp/` - Temporary files
- `Logs/` - Log files
- `obj/`, `bin/` - Build outputs
- `.csproj`, `.sln` - IDE project files (regenerated by Unity)
- `.vs/`, `.idea/` - Heavy IDE settings (regenerated automatically)

### Customizing the Preservation List

If you need to add more files or folders to the preservation list, you can easily modify the code:

1. Open `main.py` in a text editor
2. Find the `Constants` class at the top of the file (around line 16)
3. Add your items to the appropriate list:

```python
class Constants:
    # Add Unity-related items here
    UNITY_CONFIG_FILES = ['.vsconfig', '.collabignore', 'YourCustomFile.txt']

    # Add documentation files here
    DOCUMENTATION_FILES = [
        'README.md', 'LICENSE',
        'YOUR_CUSTOM_DOC.md'  # Add your file here
    ]

    # Add custom folders to preserve
    CUSTOM_FOLDERS = ['MyImportantFolder', 'DoNotDelete']

    # Don't forget to add it to KEEP_LIST
    KEEP_LIST = (
        UNITY_ESSENTIAL_FOLDERS +
        UNITY_CONFIG_FILES +
        # ... existing items ...
        CUSTOM_FOLDERS  # Add your custom list here
    )
```

4. Save the file and rebuild:
```bash
pyinstaller UnityCleaner.spec
```

**Note**: Item names are case-sensitive on macOS/Linux but case-insensitive on Windows.

## Troubleshooting

### Check the Log File
If you encounter issues, check `unitycleaner.log` in the application directory for detailed information about what happened.

### Common Issues
- **Permission Denied**: Some files may be locked by other applications. Close Unity and any IDEs before cleaning.
- **File in Use**: Windows may prevent deletion of files currently open in other programs.
- **Slow Performance**: For very large projects or many projects, the initial scanning may take time.

## License
Distributed under the MIT License. See `LICENSE` for more information.

## Changelog

### v2.0 (2026-02-25)
- Separated business logic from UI (CleanupEngine class)
- Added comprehensive logging system
- Implemented size tracking and display (MB/GB)
- Added progress bar with detailed statistics
- Enhanced error handling with specific error types
- Added symbolic link detection and safe handling
- Added path validation for system folder protection
- Improved performance with optimized directory traversal
- Added full type hints for better code quality
- Migrated from deprecated `onerror` to `onexc` for shutil.rmtree
- Improved UI with better fonts and colors
- Added elapsed time tracking
- **Expanded preservation list** (40+ items):
  - Unity config files (`.vsconfig`, `.collabignore`)
  - Extended Git support (`.gitmodules`, `.gitkeep`, `.github/`)
  - Documentation files (`README`, `LICENSE`, `CHANGELOG`, etc.)
  - CI/CD configurations (GitLab, Travis, Azure, Jenkins, etc.)
  - Package manager files (`package.json`, `yarn.lock`, etc.)
  - Team IDE settings (`.vscode`, `.editorconfig`)
  - Other VCS systems (`.svn`, `.hg`)

### v1.0 (Initial Release)
- Basic Unity project cleaning functionality
- Single and recursive modes
- Custom folder exclusions
- Multi-threaded processing
