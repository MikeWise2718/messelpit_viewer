# Add Windows Firewall inbound rules for the Messel Pit streaming setup.
#
# Run this ONCE, as Administrator, before testing browser streaming
# from another device on the LAN (e.g. Meta Quest 2 / Quest 3 browser).
# Rules are scoped to the Private profile only (your home network),
# not Public.
#
# To run as admin:
#   1. Right-click this file in Explorer -> "Run with PowerShell"
#      (will prompt for elevation), OR
#   2. Open PowerShell as Administrator, then:
#      cd D:\senckenberg\messelpit_viewer
#      .\tools\add-firewall-rules.ps1
#
# To remove the rules later:
#   Remove-NetFirewallRule -DisplayName "Messelpit *"

# Self-elevate if not already running as admin.
$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Not running as Administrator. Re-launching elevated..." -ForegroundColor Yellow
    Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoExit","-ExecutionPolicy","Bypass","-File",$PSCommandPath
    exit
}

Write-Host "Adding firewall rules for Messel Pit streaming..." -ForegroundColor Cyan

# Rule 1: WebRTC signaling port (TCP 49100). This is what Kit's
# omni.kit.livestream.app serves; the browser client uses it for the
# initial handshake.
try {
    $existing = Get-NetFirewallRule -DisplayName "Messelpit Kit WebRTC signaling (TCP 49100)" -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "  [skip] TCP 49100 rule already exists" -ForegroundColor Gray
    } else {
        New-NetFirewallRule `
            -DisplayName "Messelpit Kit WebRTC signaling (TCP 49100)" `
            -Direction Inbound `
            -Protocol TCP `
            -LocalPort 49100 `
            -Action Allow `
            -Profile Private | Out-Null
        Write-Host "  [ok]   added TCP 49100 (signaling)" -ForegroundColor Green
    }
} catch {
    Write-Host "  [fail] TCP 49100: $($_.Exception.Message)" -ForegroundColor Red
}

# Rule 2: Media UDP traffic, scoped to the Kit executable. WebRTC
# negotiates ephemeral UDP ports for the actual video, so we can't
# pre-enumerate them -- but we can allow inbound UDP for kit.exe
# specifically. Scoped to the streaming kit's binary path.
$kitExe = "D:\senckenberg\messelpit_viewer\kit-app-template\_build\windows-x86_64\release\kit\kit.exe"
if (-not (Test-Path $kitExe)) {
    Write-Host "  [warn] kit.exe not found at expected path: $kitExe" -ForegroundColor Yellow
    Write-Host "         Run 'repo.bat build' inside kit-app-template/ first." -ForegroundColor Yellow
} else {
    try {
        $existing = Get-NetFirewallRule -DisplayName "Messelpit Kit WebRTC media (UDP)" -ErrorAction SilentlyContinue
        if ($existing) {
            Write-Host "  [skip] UDP kit.exe rule already exists" -ForegroundColor Gray
        } else {
            New-NetFirewallRule `
                -DisplayName "Messelpit Kit WebRTC media (UDP)" `
                -Direction Inbound `
                -Protocol UDP `
                -Action Allow `
                -Profile Private `
                -Program $kitExe | Out-Null
            Write-Host "  [ok]   added UDP for kit.exe (media)" -ForegroundColor Green
        }
    } catch {
        Write-Host "  [fail] UDP kit.exe: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Rule 3: Vite dev server (TCP 5173). The web-viewer-sample is served
# from this port; the Quest browser needs to reach it to load the
# HTML/JS client. Vite binds to all interfaces by default once you
# pass --host or set host:true in vite.config (some setups already
# do this; if not, the rule is harmless either way).
try {
    $existing = Get-NetFirewallRule -DisplayName "Messelpit Vite dev server (TCP 5173)" -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "  [skip] TCP 5173 rule already exists" -ForegroundColor Gray
    } else {
        New-NetFirewallRule `
            -DisplayName "Messelpit Vite dev server (TCP 5173)" `
            -Direction Inbound `
            -Protocol TCP `
            -LocalPort 5173 `
            -Action Allow `
            -Profile Private | Out-Null
        Write-Host "  [ok]   added TCP 5173 (Vite dev server)" -ForegroundColor Green
    }
} catch {
    Write-Host "  [fail] TCP 5173: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Done. Listing the rules just added:" -ForegroundColor Cyan
Get-NetFirewallRule -DisplayName "Messelpit *" |
    Select-Object DisplayName, Enabled, Direction, Action, Profile |
    Format-Table -AutoSize

Write-Host ""
Write-Host "If you need to remove them later:" -ForegroundColor Gray
Write-Host "  Remove-NetFirewallRule -DisplayName 'Messelpit *'" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Enter to close this window..." -ForegroundColor Yellow
$null = Read-Host
