; Duplicate Finder - Windows installer (Inno Setup 7.1 or newer).
;
; Do not compile this file directly. Build with:
;
;     python tools/build_installer.py
;
; That script freezes the app with PyInstaller and passes the values below
; (version, paths, IDs) from the app's own code, so they are defined in one
; place only.

#if Ver < EncodeVer(7, 1, 0)
  #error Inno Setup 7.1 or newer is required.
#endif

; ---- Values supplied by tools/build_installer.py ---------------------------
#ifndef AppVersion
  #error AppVersion is not defined. Build with: python tools/build_installer.py
#endif
#ifndef AppNumericVersion
  #error AppNumericVersion is not defined. Build with: python tools/build_installer.py
#endif
#ifndef AppExeName
  #error AppExeName is not defined. Build with: python tools/build_installer.py
#endif
#ifndef AppUserModelID
  #error AppUserModelID is not defined. Build with: python tools/build_installer.py
#endif
#ifndef SettingsDirName
  #error SettingsDirName is not defined. Build with: python tools/build_installer.py
#endif
#ifndef BundleDir
  #error BundleDir is not defined. Build with: python tools/build_installer.py
#endif
#ifndef IconFile
  #error IconFile is not defined. Build with: python tools/build_installer.py
#endif
#ifndef OutputDir
  #error OutputDir is not defined. Build with: python tools/build_installer.py
#endif

; ---- Installer identity ----------------------------------------------------
#define AppName "Duplicate Finder"
#define AppPublisher "Kianoosh"
#define AppURL       "https://github.com/kianoush-samandi"

[Setup]
; AppId identifies the app to Windows across versions. NEVER change it, or
; upgrades will install side by side instead of replacing the old version.
AppId={{606CFEFB-73B1-4A82-B83A-C9CD5B7BAA45}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoVersion={#AppNumericVersion}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}

; The bundled Python runtime is 64-bit. This also makes ArchitecturesAllowed
; and ArchitecturesInstallIn64BitMode default to x64compatible.
SetupArchitecture=x64
MinVersion=10.0

; The app needs no administrator rights, so install per user by default
; (no UAC prompt); the user may still choose "all users" in a dialog.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE

; "dynamic" follows the Windows light/dark setting, like the app itself.
WizardStyle=modern dynamic
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}

; Persian Windows gets the Persian wizard automatically; the language
; dialog appears only when the Windows UI language matches neither.
ShowLanguageDialog=auto

OutputDir={#OutputDir}
OutputBaseFilename=DuplicateFinder-{#AppVersion}-Setup
Compression=lzma2/max
SolidCompression=yes

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
; Farsi.isl: community translation from the Inno Setup project
; (Files/Languages/Unofficial), distributed under the Inno Setup license.
Name: "fa"; MessagesFile: "languages\Farsi.isl"

[CustomMessages]
en.RemoveSettingsPrompt=Also remove your {#AppName} settings (theme and language)?%n%nFiles in your quarantine folders are not affected.
fa.RemoveSettingsPrompt=تنظیمات {#AppName} (پوسته و زبان) هم حذف شود؟%n%nفایل‌های داخل پوشه‌های قرنطینه دست نمی‌خورند.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
; PyInstaller's support folder changes between versions; clear it on upgrade
; so no stale DLLs or modules from the previous version are left behind.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; AppUserModelID must match the one the app registers at startup, so a
; pinned taskbar icon and the running window are treated as one app.
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; AppUserModelID: "{#AppUserModelID}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; AppUserModelID: "{#AppUserModelID}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[Code]
{ Settings live in the current user's profile, so they are only offered for
  removal in a per-user install; an all-users uninstall runs elevated and
  could not reach the right profile. "No" is the default button, and silent
  uninstalls keep the settings. }

function SettingsDir: String;
begin
  Result := ExpandConstant('{userappdata}\{#SettingsDirName}');
end;

function ConfirmRemoveSettings: Boolean;
begin
  Result := SuppressibleMsgBox(CustomMessage('RemoveSettingsPrompt'),
    mbConfirmation, MB_YESNO or MB_DEFBUTTON2, IDNO) = IDYES;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and not IsAdminInstallMode
    and DirExists(SettingsDir) and ConfirmRemoveSettings then
    DelTree(SettingsDir, True, True, True);
end;
