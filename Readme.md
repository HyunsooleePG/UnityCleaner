# UnityCleaner

UnityCleaner is a simple and efficient automation tool designed to optimize Unity project sizes by removing unnecessary files and folders while preserving core project data.

## Features
- **Project Optimization**: Automatically deletes heavy cache and temporary folders (`Library`, `Temp`, `Logs`, etc.) and IDE-generated files (`.csproj`, `.sln`).
- **Core Preservation**: Safely keeps essential Unity folders: `Assets`, `ProjectSettings`, and `Packages`.
- **Two Operation Modes**:
  - **Clean Single Project**: Targets one specific Unity project.
  - **Clean All Projects in Subfolders**: Recursively searches for and cleans all Unity projects found within a specified directory.
- **Custom Exclusions**: Allows users to specify additional folders to be skipped during the cleaning process.

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
7. **Monitor Progress**: Watch the status label for real-time updates. You can use the **"Stop"** button if you need to cancel the operation.
8. **View Results**: Once complete, a summary report will show how many items were deleted and which projects were cleaned.

### macOS
1. **Run the Script**: Open Terminal and run `python3 main.py`. (Or open the built `.app` if available).
2. **Follow the same steps** as the Windows version from step 2 to 8.

## System Requirements
- **Windows**: Standalone `.exe` provided (No Python installation required).
- **macOS**: Python 3.x required (Run from source or build into `.app` via PyInstaller).
- **Python 3.x**: Required if running from source.

## License
Distributed under the MIT License. See `LICENSE` for more information.
