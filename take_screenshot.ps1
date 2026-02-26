Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Activate the browser with HealthyRoute, send scroll keys
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
using System.Collections.Generic;
public class WinHelper {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    public static IntPtr FindWindowByTitle(string search) {
        IntPtr found = IntPtr.Zero;
        EnumWindows(delegate(IntPtr hWnd, IntPtr lParam) {
            if (IsWindowVisible(hWnd)) {
                StringBuilder sb = new StringBuilder(256);
                GetWindowText(hWnd, sb, 256);
                if (sb.ToString().Contains(search)) {
                    found = hWnd;
                    return false;
                }
            }
            return true;
        }, IntPtr.Zero);
        return found;
    }
}
"@

$hwnd = [WinHelper]::FindWindowByTitle("HealthyRoute AI")
if ($hwnd -ne [IntPtr]::Zero) {
    [WinHelper]::ShowWindow($hwnd, 9) | Out-Null
    [WinHelper]::SetForegroundWindow($hwnd) | Out-Null
    Write-Output "Activated HealthyRoute window"
} else {
    Write-Output "Not found, opening fresh"
    Start-Process "http://localhost:3000"
}

Start-Sleep -Seconds 2

# Scroll down twice
[System.Windows.Forms.SendKeys]::SendWait("{PGDN}")
Start-Sleep -Milliseconds 400
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
