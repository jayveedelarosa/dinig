; Dinig setup wizard. Build it on Windows with packaging\build_setup.bat.
; The teacher double-clicks DinigSetup.exe: Next, Install, Finish, then the Desktop icon.

#define AppName "Dinig"
#define AppVersion "1.0.0"
#define AppPublisher "Dinig"

[Setup]
AppId={{7F3A9C2E-1B84-4D6A-8E20-6C5B4A1900D1}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
; Per-user folder: no administrator password.
DefaultDirName={localappdata}\Dinig
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
OutputDir=output
OutputBaseFilename=DinigSetup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#AppName}
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
WelcomeLabel2=Dinig stays on this laptop and works with Wi-Fi off. It needs about 6GB free. No account.
FinishedHeadingLabel=Dinig is ready
FinishedLabel=Dinig is on this laptop.%n%nDouble-click the Dinig icon on the Desktop whenever you want to use it. The first time, click Allow when the browser asks for the microphone.

[CustomMessages]
StartDinig=Start Dinig. When the browser asks for the microphone, click Allow.

[Files]
; App code. seed.py is left out so a later install cannot wipe the class.
Source: "staging\backend\*"; DestDir: "{app}\backend"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "seed.py,__pycache__\*,*.pyc"
Source: "staging\frontend\*"; DestDir: "{app}\frontend"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "staging\python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "staging\models\*"; DestDir: "{app}\models"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "staging\start_dinig.bat"; DestDir: "{app}"; Flags: ignoreversion
; Keep readings and teacher-added pupils across a reinstall.
Source: "staging\data\dinig.db"; DestDir: "{app}\data"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "redist\OllamaSetup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{userdesktop}\Dinig"; Filename: "{app}\start_dinig.bat"; WorkingDir: "{app}"; Comment: "Start Dinig"
Name: "{userprograms}\Dinig"; Filename: "{app}\start_dinig.bat"; WorkingDir: "{app}"; Comment: "Start Dinig"

[Run]
Filename: "{tmp}\OllamaSetup.exe"; Parameters: "/VERYSILENT /NORESTART /SUPPRESSMSGBOXES"; StatusMsg: "Installing Ollama..."; Flags: waituntilterminated; Check: not OllamaInstalled
Filename: "{app}\start_dinig.bat"; Description: "{cm:StartDinig}"; Flags: postinstall nowait skipifsilent

[Code]
var
  ModelPage: TWizardPage;
  Model3B: TNewRadioButton;
  Model15B: TNewRadioButton;

function OllamaInstalled: Boolean;
begin
  Result := FileExists(ExpandConstant('{localappdata}\Programs\Ollama\ollama.exe'))
    or FileExists(ExpandConstant('{pf}\Ollama\ollama.exe'));
end;

procedure InitializeWizard;
begin
  ModelPage := CreateCustomPage(wpSelectDir,
    'Which AI should Dinig use?',
    'Qwen 2.5 3B is the usual choice. Pick 1.5B when this laptop has 8GB of memory and feels full.');

  Model3B := TNewRadioButton.Create(WizardForm);
  Model3B.Parent := ModelPage.Surface;
  Model3B.Caption := 'Qwen 2.5 3B (recommended)';
  Model3B.Checked := True;
  Model3B.Left := 0;
  Model3B.Top := 0;
  Model3B.Width := ModelPage.SurfaceWidth;

  Model15B := TNewRadioButton.Create(WizardForm);
  Model15B.Parent := ModelPage.Surface;
  Model15B.Caption := 'Qwen 2.5 1.5B (for a crowded 8GB laptop)';
  Model15B.Left := 0;
  Model15B.Top := Model3B.Top + ScaleY(28);
  Model15B.Width := ModelPage.SurfaceWidth;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  FreeBytes, TotalBytes: Int64;
begin
  Result := True;
  if CurPageID = wpSelectDir then
  begin
    if GetSpaceOnDisk64(ExtractFileDrive(WizardDirValue), FreeBytes, TotalBytes) then
    begin
      { 6GB: app, Whisper, both Qwen sizes, and the Ollama program. }
      if FreeBytes < (Int64(6) * 1024 * 1024 * 1024) then
      begin
        MsgBox('This disk needs about 6GB free for Dinig. Free some space, or choose another folder.', mbError, MB_OK);
        Result := False;
      end;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  EnvPath, Model, Body: String;
begin
  if CurStep <> ssPostInstall then
    Exit;
  { First install writes .env. A later install leaves the teacher's choice alone. }
  EnvPath := ExpandConstant('{app}\.env');
  if FileExists(EnvPath) then
    Exit;
  if Model15B.Checked then
    Model := 'qwen2.5:1.5b'
  else
    Model := 'qwen2.5:3b';
  Body :=
    'OLLAMA_MODEL=' + Model + #13#10 +
    'OLLAMA_URL=http://127.0.0.1:11434' + #13#10 +
    'WHISPER_MODEL_DIR=models/faster-whisper-small' + #13#10 +
    'WHISPER_COMPUTE_TYPE=int8' + #13#10 +
    'WHISPER_CPU_THREADS=0' + #13#10 +
    'READING_CHECK=plan_a' + #13#10 +
    'QUIZ_TIMEOUT_SECONDS=8' + #13#10;
  SaveStringToFile(EnvPath, Body, False);
end;
