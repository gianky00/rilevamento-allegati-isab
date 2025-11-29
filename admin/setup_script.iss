; Script generato per PDF-Splitter
; Compatibile con struttura PyInstaller OneDir

#define MyAppName "PDF-Splitter"
#define MyAppPublisher "Admin"
#define MyAppExeName "PDF-Splitter.exe"

; Default values if not defined via command line
#ifndef MyAppVersion
  #define MyAppVersion "1.0"
#endif
#ifndef BuildDir
  ; Fallback relativo se non passato da riga di comando
  #define BuildDir "..\dist\PDF-Splitter"
#endif

[Setup]
; ID univoco per l'applicazione
AppId={{C0D3-1234-5678-90AB-CDEF12345678}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; Installa in C:\Program Files\PDF-Splitter
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes

; === OUTPUT DIRECTORY ===
OutputDir=dist\Setup
OutputBaseFilename=PDF-Splitter_Setup_v{#MyAppVersion}

Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Registry]
; Menu contestuale "Dividi con PDF-Splitter" (PDF Singolo)
Root: HKCR; Subkey: "SystemFileAssociations\.pdf\shell\PDFSplitter"; ValueType: string; ValueName: ""; ValueData: "Dividi con PDF-Splitter"; Flags: uninsdeletekey
Root: HKCR; Subkey: "SystemFileAssociations\.pdf\shell\PDFSplitter"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletekey
Root: HKCR; Subkey: "SystemFileAssociations\.pdf\shell\PDFSplitter\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletekey

[Files]
; === ESEGUIBILE E DIPENDENZE PYTHON ===
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Avvia l'app dopo l'installazione
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; === PULIZIA ===
Type: files; Name: "{app}\*.log"
Type: filesandordirs; Name: "{app}\Licenza"
Type: filesandordirs; Name: "{app}"
