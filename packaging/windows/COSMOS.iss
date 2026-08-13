#define MyAppName "COSMOS Media"
#ifndef MyAppVersion
  #define MyAppVersion "0.2.0"
#endif
#define MyAppPublisher "Cory Davis / NavisWORLD"
#define MyAppExeName "COSMOS-Media.exe"

[Setup]
AppId={{C76F653D-41EE-4B27-9EA8-9D72858C11E7}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\COSMOS Media
DefaultGroupName=COSMOS Media
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\..\dist\installer
OutputBaseFilename=COSMOS-Media-Setup-Windows-x86_64
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupLogging=yes

[Files]
Source: "..\..\dist\COSMOS-Media.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\dist\cosmos-media.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\COSMOS Media"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\COSMOS Media"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{autoprograms}\COSMOS Media CLI"; Filename: "{cmd}"; Parameters: "/K \"\"{app}\cosmos-media.exe\" status\""; WorkingDir: "{app}"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch COSMOS Media"; Flags: nowait postinstall skipifsilent
