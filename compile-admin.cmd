@echo off
setlocal

set "SCRIPT=admin.py"
set "EXE=admin.exe"
set "OUTFOLDER=final"

:: Obtener nombre base sin extensión
for %%F in ("%SCRIPT%") do set "BASENAME=%%~nF"

:: Preparar carpeta final limpia
if not exist "%OUTFOLDER%" mkdir "%OUTFOLDER%"
if exist "%OUTFOLDER%\%EXE%" del /q "%OUTFOLDER%\%EXE%"

:: Borrar restos anteriores
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "%BASENAME%.spec" del /q "%BASENAME%.spec"

echo Compiling %SCRIPT%...
pyinstaller --onefile --noconsole --clean --icon=icon.ico ^
--hidden-import=asyncio ^
--hidden-import=threading ^
--hidden-import=socket ^
--hidden-import=json ^
--hidden-import=os ^
--hidden-import=base64 ^
--hidden-import=pyautogui ^
--hidden-import=tempfile ^
--hidden-import=subprocess ^
--hidden-import=getpass ^
--hidden-import=ctypes ^
--hidden-import=platform ^
--hidden-import=tkinter ^
--hidden-import=tkinter.ttk ^
--hidden-import=tkinter.scrolledtext ^
--hidden-import=tkinter.filedialog ^
"%SCRIPT%"


if exist "dist\%BASENAME%.exe" (
    move /y "dist\%BASENAME%.exe" "%OUTFOLDER%\%EXE%"
)

:: Cleanup
rmdir /s /q build >nul 2>&1
rmdir /s /q dist >nul 2>&1
del /q "%BASENAME%.spec" >nul 2>&1

echo Done. %EXE% saved to '%OUTFOLDER%'
pause
