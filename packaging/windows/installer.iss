; Windows 安装向导脚本（Inno Setup 6）
; CI 通过 ISCC /D 传入：MyAppVersion、SourceExe、SourceIco、OutputBase

#define MyAppName "Stellar Search Everything"
#define MyAppExeName "StellarSearchEverything.exe"

[Setup]
AppId={{7E4C2D46-9C1B-4E6A-8F3D-2A5B8C9D0E17}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=StellarStar255
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename={#OutputBase}
SetupIconFile={#SourceIco}
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: unchecked

[Files]
Source: "{#SourceExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
