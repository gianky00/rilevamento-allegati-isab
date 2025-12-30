; Script generato per Intelleo PDF Splitter
; Compatibile con struttura Nuitka Standalone

#define MyAppName "Intelleo PDF Splitter"
#define MyAppPublisher "Giancarlo Allegretti"
#define MyAppExeName "Intelleo PDF Splitter.exe"
#define MyAppURL "https://intelleo-pdf-splitter.netlify.app"

; Default values if not defined via command line
#ifndef MyAppVersion
  #define MyAppVersion "1.0"
#endif
#ifndef BuildDir
  ; Fallback relativo se non passato da riga di comando
  #define BuildDir "..\..\dist\Intelleo PDF Splitter"
#endif

[Setup]
; ID univoco per l'applicazione
AppId={{C0D3-1234-5678-90AB-CDEF12345678}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppCopyright=Copyright (C) 2024 {#MyAppPublisher}

; Installa in C:\Program Files\Intelleo PDF Splitter
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes

; Richiedi privilegi di amministratore per l'installazione e l'esecuzione
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; === OUTPUT DIRECTORY ===
OutputDir=Setup
OutputBaseFilename=IntelleoPDFSplitter_Setup_v{#MyAppVersion}

; === ICONA ===
SetupIconFile=..\..\src\resources\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

Compression=lzma
SolidCompression=yes
WizardStyle=modern

; Informazioni versione nel file setup
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Intelleo PDF Splitter Setup
VersionInfoCopyright=Copyright (C) 2024 {#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Registry]
; Menu contestuale "Dividi con Intelleo PDF Splitter" (PDF Singolo)
Root: HKCU; Subkey: "Software\Classes\.pdf\shell\IntelleoPDFSplitter"; ValueType: string; ValueName: ""; ValueData: "Dividi con Intelleo PDF Splitter"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\.pdf\shell\IntelleoPDFSplitter"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\.pdf\shell\IntelleoPDFSplitter\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletekey

; Menu contestuale per Cartelle
Root: HKCU; Subkey: "Software\Classes\Directory\shell\IntelleoPDFSplitter"; ValueType: string; ValueName: ""; ValueData: "Elabora cartella con Intelleo PDF Splitter"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Directory\shell\IntelleoPDFSplitter"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Directory\shell\IntelleoPDFSplitter\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletekey

[Files]
; === CONFIGURATION FILE ===
; Installa nella cartella dell'applicazione (Fallback/Template per Admin)
Source: "{#BuildDir}\config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall

; Installa nella cartella APPDATA dell'utente che esegue l'installazione (Priorità Utente)
; Nota: In installazioni amministrative, questo andrà nel profilo dell'Admin.
Source: "{#BuildDir}\config.json"; DestDir: "{userappdata}\{#MyAppName}"; Flags: onlyifdoesntexist uninsneveruninstall

; === ESEGUIBILE E DIPENDENZE PYTHON (EXCLUDE CONFIG.JSON TO AVOID DUPLICATION/OVERWRITE) ===
; Excludes allows us to handle config.json separately above
Source: "{#BuildDir}\*"; DestDir: "{app}"; Excludes: "config.json,admin"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
; Crea le directory necessarie in APPDATA
Name: "{userappdata}\{#MyAppName}"; Flags: uninsneveruninstall
Name: "{userappdata}\{#MyAppName}\Log"; Flags: uninsneveruninstall

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Avvia l'app dopo l'installazione usando shellexec per gestire correttamente l'elevazione UAC
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: shellexec postinstall skipifsilent
; Riavvio automatico dopo update (attivato da flag /FORCESTART)
Filename: "{app}\{#MyAppExeName}"; Flags: shellexec; Check: IsForceStart

[Code]
function IsForceStart: Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 1 to ParamCount do
  begin
    if CompareText(ParamStr(I), '/FORCESTART') = 0 then
    begin
      Result := True;
      Exit;
    end;
  end;
end;

[UninstallDelete]
; === PULIZIA ===
Type: files; Name: "{app}\*.log"
Type: filesandordirs; Name: "{app}\Licenza"

; === PULIZIA DATI UTENTE (PRESERVA CONFIG.JSON) ===
; Cancella solo il file di sessione, lasciando il resto.
Type: files; Name: "{userappdata}\{#MyAppName}\session.json"
; Cancella la cartella dei log.
Type: filesandordirs; Name: "{userappdata}\{#MyAppName}\Log"

; Rimuove la cartella principale dell'applicazione alla fine
Type: filesandordirs; Name: "{app}"
