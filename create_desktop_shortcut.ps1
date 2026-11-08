$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [System.Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path -Path $DesktopPath -ChildPath "DFM Downloader.lnk"
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "d:\DFM\dist\DFM\DFM.exe"
$Shortcut.WorkingDirectory = "d:\DFM\dist\DFM"
$Shortcut.IconLocation = "d:\DFM\assets\dfm_icon.ico, 0"
$Shortcut.Description = "DFM - Fast Multi-Threaded Internet Download Manager"
$Shortcut.Save()
Write-Host "Desktop shortcut created successfully at: $ShortcutPath"
