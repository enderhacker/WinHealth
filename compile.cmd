@echo off
setlocal enabledelayedexpansion

REM Output folder
set OUTFOLDER=final

REM Create output folder if it doesn't exist
if not exist %OUTFOLDER% mkdir %OUTFOLDER%

REM Force delete old build/dist folders if exist
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM ------------------------------
REM Compile installer.py
REM ------------------------------
if exist "%OUTFOLDER%\installer.exe" del /f /q "%OUTFOLDER%\installer.exe"

pyinstaller --onefile --noconsole --clean ^
--icon=none ^
--hidden-import=os ^
--hidden-import=sys ^
--hidden-import=ctypes ^
--hidden-import=subprocess ^
--hidden-import=urllib.request ^
--hidden-import=urllib.error ^
--hidden-import=HTTPError ^
--hidden-import=URLError ^
--hidden-import=winreg ^
--hidden-import=shutil ^
"installer.py"

if exist "dist\installer.exe" move /y "dist\installer.exe" "%OUTFOLDER%\installer.exe"
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "installer.spec" del /f /q "installer.spec"

REM ------------------------------
REM Compile agent.py
REM ------------------------------
if exist "%OUTFOLDER%\agent.exe" del /f /q "%OUTFOLDER%\agent.exe"

pyinstaller --onefile --noconsole --clean ^
--icon=none ^
--hidden-import=asyncio ^
--hidden-import=socket ^
--hidden-import=os ^
--hidden-import=json ^
--hidden-import=tempfile ^
--hidden-import=subprocess ^
--hidden-import=getpass ^
--hidden-import=threading ^
"agent.py"

if exist "dist\agent.exe" move /y "dist\agent.exe" "%OUTFOLDER%\agent.exe"
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "agent.spec" del /f /q "agent.spec"

REM ------------------------------
REM Compile admin.py
REM ------------------------------
if exist "%OUTFOLDER%\admin.exe" del /f /q "%OUTFOLDER%\admin.exe"

pyinstaller --onefile --noconsole --clean ^
--icon=none ^
--hidden-import=tkinter ^
--hidden-import=tkinter.messagebox ^
--hidden-import=tkinter.simpledialog ^
--hidden-import=tkinter.scrolledtext ^
--hidden-import=tkinter.ttk ^
--hidden-import=threading ^
--hidden-import=socket ^
--hidden-import=json ^
--hidden-import=time ^
"admin.py"

if exist "dist\admin.exe" move /y "dist\admin.exe" "%OUTFOLDER%\admin.exe"
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "admin.spec" del /f /q "admin.spec"

echo Compilation complete. All exes are in '%OUTFOLDER%'.
pause
