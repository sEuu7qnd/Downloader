@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo  Creando Downloader (carpeta rapida + un solo archivo)
echo ============================================================

where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo No se encontro Python. Instalalo desde https://www.python.org/downloads/
    echo y marca la casilla "Add python.exe to PATH" durante la instalacion.
    pause
    exit /b 1
)

echo.
echo [1/4] Instalando dependencias...
python -m pip install --upgrade pip
python -m pip install --upgrade "yt-dlp[default]" imageio-ffmpeg pyinstaller
if errorlevel 1 goto :error

echo.
echo [2/4] Compilando version en carpeta (arranque rapido)...
python -m PyInstaller --noconfirm --clean --onedir --noconsole ^
    --name Downloader ^
    --collect-submodules yt_dlp ^
    --collect-all imageio_ffmpeg ^
    --collect-all yt_dlp_ejs ^
    --paths . --hidden-import gui.app main.py
if errorlevel 1 goto :error

echo.
echo [3/4] Compilando version de un solo archivo...
python -m PyInstaller --noconfirm --clean --onefile --noconsole ^
    --name Downloader ^
    --distpath dist-unico --workpath build-unico ^
    --collect-submodules yt_dlp ^
    --collect-all imageio_ffmpeg ^
    --collect-all yt_dlp_ejs ^
    --paths . --hidden-import gui.app main.py
if errorlevel 1 goto :error

echo.
echo [4/4] Listo.
echo.
echo  Rapida (recomendada):  %~dp0dist\Downloader\Downloader.exe
echo     (usa la carpeta completa "Downloader"; puedes crear un acceso directo al .exe)
echo  Un solo archivo:       %~dp0dist-unico\Downloader.exe
echo.
pause
exit /b 0

:error
echo.
echo Ocurrio un error. Revisa los mensajes anteriores.
pause
exit /b 1
