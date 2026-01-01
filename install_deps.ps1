
# 4DGS Dependencies Installer Script
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "      4DGS Studio Dependency Installer       " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# 1. Install FFmpeg using Winget
Write-Host "`n[1/3] Checking FFmpeg..." -ForegroundColor Yellow
if (Get-Command "ffmpeg" -ErrorAction SilentlyContinue) {
    Write-Host "✅ FFmpeg is already installed." -ForegroundColor Green
} else {
    Write-Host "Installing FFmpeg via Winget..." -ForegroundColor Cyan
    winget install "Gyan.FFmpeg" --accept-source-agreements --accept-package-agreements
    
    # Validation
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    if (Get-Command "ffmpeg" -ErrorAction SilentlyContinue) {
        Write-Host "✅ FFmpeg installed successfully!" -ForegroundColor Green
    } else {
        Write-Host "⚠️ FFmpeg install finished but command not found yet. You might need to restart your terminal." -ForegroundColor Red
    }
}

# 2. CUDA Toolkit Guidance
Write-Host "`n[2/3] NVIDIA CUDA Toolkit (Manual Step Required)" -ForegroundColor Yellow
Write-Host "I cannot silently install CUDA 11.8+ drivers. You must download them manually."
Write-Host "👉 Download Link: https://developer.nvidia.com/cuda-downloads" -ForegroundColor Cyan
Write-Host "   (Make sure to select version 11.8 or 12.1 compatible with your PyTorch)"

# 3. Visual Studio C++ Tools Guidance
Write-Host "`n[3/3] Visual Studio C++ Built Tools (Manual Step Required)" -ForegroundColor Yellow
Write-Host "Required for compiling the Gaussian Splatting kernels."
Write-Host "👉 Download Link: https://visualstudio.microsoft.com/visual-cpp-build-tools/" -ForegroundColor Cyan
Write-Host "   (During install, select 'Desktop development with C++')"

Write-Host "`n=============================================" -ForegroundColor Cyan
Write-Host "IMPORTANT: After installing these, RESTART your PC." -ForegroundColor Red
Write-Host "=============================================" -ForegroundColor Cyan
Read-Host -Prompt "Press Enter to exit"
