@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo      4DGS Studio - Environment Launcher
echo ========================================================

REM --- 1. SETUP VISUAL STUDIO ---
set "VS_FOUND=0"
REM Community
if exist "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" (
    call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
    set "VS_FOUND=1"
    echo [OK] Visual Studio 2022 Community Environment Active
)

REM Professional
if "!VS_FOUND!"=="0" (
    if exist "C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat" (
        call "C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat" >nul
        set "VS_FOUND=1"
        echo [OK] Visual Studio 2022 Professional Environment Active
    )
)

if "!VS_FOUND!"=="0" echo [WARNING] Visual Studio 2022 vcvars64.bat not found.

REM --- 2. SETUP CUDA ---
set "CUDA_FOUND=0"
REM Try 11.8
if exist "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin" (
    set "PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin;!PATH!"
    set "CUDA_FOUND=1"
    echo [OK] CUDA 11.8 Added to PATH
)

REM Try 12.1
if "!CUDA_FOUND!"=="0" (
    if exist "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1\bin" (
        set "PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1\bin;!PATH!"
        set "CUDA_FOUND=1"
        echo [OK] CUDA 12.1 Added to PATH
    )
)

if "!CUDA_FOUND!"=="0" echo [WARNING] CUDA Toolkit bin folder not found in default locations.

REM --- 3. SETUP FFMPEG ---
set "FFMPEG_PATH=C:\Users\Santosh\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin"
if exist "!FFMPEG_PATH!\ffmpeg.exe" (
    set "PATH=!FFMPEG_PATH!;!PATH!"
    echo [OK] FFmpeg found at hardcoded path
) else (
    echo [WARNING] FFmpeg binary not found at hardcoded path.
)

REM --- 4. DIAGNOSTICS ---
echo.
echo --- Diagnostics ---
where cl
if errorlevel 1 echo [FAIL] cl.exe - C++ Compiler - not in PATH
where nvcc
if errorlevel 1 echo [FAIL] nvcc.exe - CUDA Compiler - not in PATH
where ffmpeg
if errorlevel 1 echo [FAIL] ffmpeg.exe - Video Processor - not in PATH

echo.
echo Launching Application...
python app_gui.py
pause
