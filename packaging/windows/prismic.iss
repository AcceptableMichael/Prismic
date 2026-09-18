; Inno Setup script for Prismic. Produces a single PrismicSetup.exe that
; installs the app and (unlike a bare portable exe) can also register the
; .prismic file association automatically, as part of setup -- see the
; [Registry] section below. This is the "installer-driven registry
; entries" approach the original phase plan called for, as an alternative
; to running packaging/windows/register_file_association.ps1 by hand.
;
; Build (after building dist\prismic.exe from packaging\prismic.spec):
;   "C:\Users\<you>\AppData\Local\Programs\Inno Setup 6\ISCC.exe" packaging\windows\prismic.iss
; Output: dist\PrismicSetup.exe
;
; Per-user install (PrivilegesRequired=lowest): installs under the current
; user's AppData, no admin elevation and no UAC prompt required, and the
; file association it registers is HKCU (current user only) -- consistent
; with register_file_association.ps1's own choice, and the least invasive
; option. A machine-wide (HKLM, all-users) installer is a different,
; larger step (needs admin, affects every account) that hasn't been asked
; for.
;
; Same boundary as everywhere else in this project: nothing here is ever
; executed automatically by a Claude session. Compiling this script (which
; just reads dist\prismic.exe and writes PrismicSetup.exe, both inside the
; repo) is a local build step like the PyInstaller build. *Running* the
; resulting installer -- which does write to the real filesystem and
; registry -- is for a human to do deliberately.
;
; Streamlined wizard flow, user-requested: the desktop-icon choice is a
; checkbox on the same page as the install-location choice (rather than
; its own "Select Additional Tasks" page -- see [Code]/ShouldCreateDesktopIcon
; below, which is why there's no [Tasks] section), and the confirmation
; ("Ready to Install"), abort-confirmation ("Setup is not complete..."),
; and completion ("Completing the Setup Wizard") screens are all skipped --
; confirm the directory/icon page and it installs and launches immediately.

#define MyAppName "Prismic"
#define MyAppVersion "0.1.0"
#define MyAppExeName "prismic.exe"

[Setup]
AppId={{6C1B2C63-6E0A-4F6E-8D2E-6A6E4B8B9B9E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\..\dist
OutputBaseFilename=PrismicSetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\..\src\prismic\assets\icon\prismic.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64compatible
; Skip the "Ready to Install" confirmation and "Completing the Setup
; Wizard" finished page -- see [Code] for the matching CancelButtonClick
; override (skips the "Setup is not complete..." exit prompt) and the
; desktop-icon checkbox merged onto the directory page.
DisableReadyPage=yes
DisableFinishedPage=yes

[Files]
Source: "..\..\dist\prismic.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
; Governed by the checkbox added to the directory-selection page in
; [Code], not a [Tasks] entry -- there's deliberately no Select Additional
; Tasks page for this to live on.
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Check: ShouldCreateDesktopIcon

[UninstallDelete]
; Inno's uninstaller only removes files it explicitly installed, then
; tries to remove {app} itself -- which only succeeds if it's completely
; empty. Anything else that ends up in there (even something as
; innocuous as a Windows-generated desktop.ini/thumbs.db from browsing
; the folder) makes it leave the directory behind rather than guess at
; what's safe to delete. {app} is a directory dedicated solely to this
; app (preferences live in %APPDATA%\Prismic instead, never here -- see
; persistence/preferences.py), so it's safe to just force-remove it
; outright on uninstall.
Type: filesandordirs; Name: "{app}"

[Registry]
; Per-user .prismic association -- same keys register_file_association.ps1
; writes by hand, just done as part of setup instead. `uninsdeletekey` on
; the ProgID key means uninstalling cleanly removes the whole association,
; not just the app files.
Root: HKCU; Subkey: "Software\Classes\.prismic"; ValueType: string; ValueName: ""; ValueData: "Prismic.Collection"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Prismic.Collection"; ValueType: string; ValueName: ""; ValueData: "Prismic Collection"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Prismic.Collection\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"",0"
Root: HKCU; Subkey: "Software\Classes\Prismic.Collection\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Run]
; With the Finished page disabled (above), a postinstall Run entry fires
; immediately once installation completes instead of waiting for a
; "Finish" click -- see DisableFinishedPage's documented behavior. No
; `unchecked` flag: that flag controls a checkbox on the Finished page,
; which no longer exists, so it would have nothing to do.
Filename: "{app}\{#MyAppExeName}"; Flags: nowait postinstall skipifsilent

[Code]
var
  DesktopIconCheckBox: TNewCheckBox;

// Puts the desktop-icon choice directly on the Select Destination
// Location page instead of its own Select Additional Tasks page,
// per the user's request to combine the two. Unchecked by default.
procedure InitializeWizard;
begin
  DesktopIconCheckBox := TNewCheckBox.Create(WizardForm);
  DesktopIconCheckBox.Parent := WizardForm.SelectDirPage;
  DesktopIconCheckBox.Left := WizardForm.DirEdit.Left;
  DesktopIconCheckBox.Top :=
    WizardForm.DirBrowseButton.Top + WizardForm.DirBrowseButton.Height + ScaleY(24);
  DesktopIconCheckBox.Width := WizardForm.DirEdit.Width;
  DesktopIconCheckBox.Height := ScaleY(17);
  DesktopIconCheckBox.Caption := 'Create a &desktop icon';
  DesktopIconCheckBox.Checked := False;
end;

function ShouldCreateDesktopIcon: Boolean;
begin
  Result := DesktopIconCheckBox.Checked;
end;

// Skips the "Setup is not complete..." confirmation when the wizard is
// cancelled/closed early -- just exits, per the user's request.
procedure CancelButtonClick(CurPageID: Integer; var Cancel, Confirm: Boolean);
begin
  Confirm := False;
end;

// Tell the shell the file association changed so File Explorer picks it
// up immediately, without requiring a logoff/logon -- same call
// register_file_association.ps1 makes by hand.
procedure SHChangeNotify(wEventId: Integer; uFlags: Integer; dwItem1, dwItem2: Longint);
  external 'SHChangeNotify@shell32.dll stdcall';

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    SHChangeNotify($08000000, $0000, 0, 0); // SHCNE_ASSOCCHANGED, SHCNF_IDLIST
end;
