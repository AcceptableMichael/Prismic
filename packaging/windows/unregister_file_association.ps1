<#
.SYNOPSIS
    Undoes register_file_association.ps1: removes the .prismic association
    for the current Windows user.

.DESCRIPTION
    Same not-run-automatically note as register_file_association.ps1 --
    this edits the real registry and is meant to be run deliberately, by a
    person, not by a Claude session.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$progId = "Prismic.Collection"
$classesRoot = "HKCU:\Software\Classes"

Remove-Item -Path "$classesRoot\.prismic" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$classesRoot\$progId" -Recurse -Force -ErrorAction SilentlyContinue

$signature = @"
[DllImport("shell32.dll")]
public static extern void SHChangeNotify(int wEventId, int uFlags, IntPtr dwItem1, IntPtr dwItem2);
"@
Add-Type -MemberDefinition $signature -Namespace "Win32" -Name "Shell"
[Win32.Shell]::SHChangeNotify(0x08000000, 0x0000, [IntPtr]::Zero, [IntPtr]::Zero)

Write-Host "Removed the .prismic file association for the current user."
