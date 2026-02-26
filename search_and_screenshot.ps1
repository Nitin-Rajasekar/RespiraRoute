Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Press Ctrl+Home to scroll to top first
[System.Windows.Forms.SendKeys]::SendWait("^{HOME}")
Start-Sleep -Milliseconds 500

# Tab into the first input (start location)
[System.Windows.Forms.SendKeys]::SendWait("{TAB}{TAB}{TAB}{TAB}")
Start-Sleep -Milliseconds 300

# Type start location
[System.Windows.Forms.SendKeys]::SendWait("Connaught Place, Delhi")
Start-Sleep -Milliseconds 500

# Tab to destination input
[System.Windows.Forms.SendKeys]::SendWait("{TAB}")
Start-Sleep -Milliseconds 300

# Type destination
[System.Windows.Forms.SendKeys]::SendWait("India Gate, Delhi")
Start-Sleep -Milliseconds 500

# Tab to button and press Enter
[System.Windows.Forms.SendKeys]::SendWait("{TAB}")
Start-Sleep -Milliseconds 200
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")

# Wait for API response
Start-Sleep -Seconds 8

# Scroll down to see the map
[System.Windows.Forms.SendKeys]::SendWait("{PGDN}")
Start-Sleep -Milliseconds 1000

# Take screenshot
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$bitmap.Save("C:\Thons\green-hackathon\aqi-app-2\screenshot_map.png", [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()
Write-Output "Screenshot saved"
