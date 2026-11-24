# PowerShell script to create a Windows Desktop shortcut for AGY Token Monitor
# Zero-black-window launch via pythonw.exe with custom high-res app.ico

$ErrorActionPreference = "Stop"

$ProjectRoot = (Get-Item $PSScriptRoot).FullName
$IconPath = Join-Path $ProjectRoot "src\assets\app.ico"
$MainScript = Join-Path $ProjectRoot "src\main.py"
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "AGY Quota Monitor.lnk"
$LegacyShortcutPath = Join-Path $DesktopPath "Token Quota Monitor.lnk"

# Locate pythonw.exe
$PythonExe = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) {
    $PythonExe = "python.exe"
}

$PythonwExe = $PythonExe -replace 'python\.exe$', 'pythonw.exe'
if (-not (Test-Path $PythonwExe)) {
    $PythonwExe = $PythonExe
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " AGY Token Monitor - 建立桌面捷徑 (Desktop Shortcut) " -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "• 專案目錄: $ProjectRoot"
Write-Host "• 執行程式: $PythonwExe"
Write-Host "• 啟動腳本: $MainScript"
Write-Host "• 圖示檔案: $IconPath"
Write-Host "• 捷徑位置: $ShortcutPath"

# Create or refresh the canonical shortcut and any existing legacy shortcut.
$WshShell = New-Object -ComObject WScript.Shell
$ShortcutPaths = @($ShortcutPath)
if (Test-Path $LegacyShortcutPath) {
    $ShortcutPaths += $LegacyShortcutPath
}

foreach ($Path in $ShortcutPaths) {
    $Shortcut = $WshShell.CreateShortcut($Path)
    $Shortcut.TargetPath = $PythonwExe
    $Shortcut.Arguments = "`"$MainScript`""
    $Shortcut.WorkingDirectory = $ProjectRoot
    $Shortcut.Description = "AGY Token Monitor - Multi-CLI Quota & Token Monitor HUD"

    if (Test-Path $IconPath) {
        $Shortcut.IconLocation = "$IconPath,0"
    }

    $Shortcut.Save()
}

Write-Host "--------------------------------------------------" -ForegroundColor Cyan
Write-Host "捷徑已成功建立在桌面: $ShortcutPath" -ForegroundColor Green
Write-Host "現在您可以直接雙擊桌面上的「AGY Quota Monitor」圖示啟動監控！" -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Cyan
