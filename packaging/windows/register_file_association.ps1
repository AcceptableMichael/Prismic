<#
.SYNOPSIS
    Registers the .prismic file extension for the current Windows user, so
    double-clicking a .prismic file launches Prismic open to that file.

.DESCRIPTION
    Per requirements-amendments.md, a .prismic file should open Prismic when
    double-clicked. That's an OS-level file-type association, not something
    the app or the file itself can do at runtime -- it has to be registered
    once, e.g. by an installer.

    This writes to HKEY_CURRENT_USER\Software\Classes, not HKLM: it's a
    per-user association that needs no administrator elevation and doesn't
    affect other accounts on the machine. That's deliberately the smaller,
    less invasive change -- an HKLM (all-users) association is a machine-wide
    installer's job, not this script's.

    This script is NOT run automatically by any Claude session or build
    step. Registering a file association edits the real Windows registry on
    whichever machine runs it, which is outside what an agent should do on
    its own -- run it yourself, deliberately, when you want the association
    in place. Re-running it is safe (it just overwrites the same keys).

.PARAMETER ExePath
    Path to the Prismic executable to associate .prismic files with.
    Defaults to dist\prismic.exe next to this script's repo, i.e. the
    PyInstaller build output from packaging\prismic.spec.

.EXAMPLE
    .\register_file_association.ps1
    .\register_file_association.ps1 -ExePath "C:\Program Files\Prismic\prismic.exe"
#>
[CmdletBinding()]
param(
    [string]$ExePath = (Join-Path $PSScriptRoot "..\..\dist\prismic.exe")
)

$ErrorActionPreference = "Stop"

$ExePath = (Resolve-Path $ExePath).Path
if (-not (Test-Path $ExePath)) {
    throw "Prismic executable not found at '$ExePath'. Build it first (see packaging\prismic.spec) or pass -ExePath."
}

$progId = "Prismic.Collection"
$classesRoot = "HKCU:\Software\Classes"

New-Item -Path "$classesRoot\.prismic" -Force | Out-Null
Set-ItemProperty -Path "$classesRoot\.prismic" -Name "(Default)" -Value $progId

New-Item -Path "$classesRoot\$progId" -Force | Out-Null
Set-ItemProperty -Path "$classesRoot\$progId" -Name "(Default)" -Value "Prismic Collection"

New-Item -Path "$classesRoot\$progId\DefaultIcon" -Force | Out-Null
Set-ItemProperty -Path "$classesRoot\$progId\DefaultIcon" -Name "(Default)" -Value "`"$ExePath`",0"

New-Item -Path "$classesRoot\$progId\shell\open\command" -Force | Out-Null
Set-ItemProperty -Path "$classesRoot\$progId\shell\open\command" -Name "(Default)" -Value "`"$ExePath`" `"%1`""

# Tell the shell the association changed, so File Explorer picks it up
# without a logoff/logon.
$signature = @"
[DllImport("shell32.dll")]
public static extern void SHChangeNotify(int wEventId, int uFlags, IntPtr dwItem1, IntPtr dwItem2);
"@
Add-Type -MemberDefinition $signature -Namespace "Win32" -Name "Shell"
[Win32.Shell]::SHChangeNotify(0x08000000, 0x0000, [IntPtr]::Zero, [IntPtr]::Zero) # SHCNE_ASSOCCHANGED

Write-Host "Registered .prismic -> $ExePath for the current user."
