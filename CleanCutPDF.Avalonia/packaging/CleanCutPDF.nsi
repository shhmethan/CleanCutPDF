; CleanCutPDF 2.x installer (NSIS). Built by build-installer.ps1, which passes:
;   /DAPP_VERSION=2.0.0-alpha.6  /DAPP_VERSION_NUMERIC=2.0.0  /DPUBLISH_DIR=...  /DOUT_FILE=...  /DAPP_ICON=...
;
; It installs per user (no administrator prompt) into the same folder and
; Installed-apps entry as CleanCutPDF 1.x, so it upgrades 1.x in place. User
; data is never touched: 1.x keeps ~/.cleancutpdf, 2.x uses ~/.cleancutpdf-next.
;
; Command line (used by the in-app updater and the 1.x upgrade):
;   /S          silent
;   /RELAUNCH   start CleanCutPDF when finished (also when a silent install fails)
;   /PORTABLE   files only: no shortcuts, no Installed-apps entry, no uninstaller
;   /D=folder   install folder; must be last and unquoted

Unicode True
!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

!define APP_NAME "CleanCutPDF"
!define APP_PUBLISHER "CleanCutPDF"
!define APP_EXE "CleanCutPDF.exe"
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\CleanCutPDF"
!define MARKER "install.marker"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "${OUT_FILE}"
InstallDir "$LOCALAPPDATA\Programs\CleanCutPDF"
RequestExecutionLevel user
CRCCheck On
SetCompressor /SOLID lzma
ShowInstDetails nevershow
ShowUninstDetails nevershow

VIProductVersion "${APP_VERSION_NUMERIC}.0"
VIAddVersionKey "ProductName" "${APP_NAME}"
VIAddVersionKey "ProductVersion" "${APP_VERSION}"
VIAddVersionKey "FileDescription" "${APP_NAME} Installer"
VIAddVersionKey "FileVersion" "${APP_VERSION}"
VIAddVersionKey "CompanyName" "${APP_PUBLISHER}"
VIAddVersionKey "LegalCopyright" "${APP_PUBLISHER}"

Var Portable
Var Relaunch

!define MUI_ICON "${APP_ICON}"
!define MUI_UNICON "${APP_ICON}"
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch CleanCutPDF"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Function .onInit
    StrCpy $Portable 0
    StrCpy $Relaunch 0
    ${GetParameters} $R0
    ClearErrors
    ${GetOptions} $R0 "/PORTABLE" $R1
    ${IfNot} ${Errors}
        StrCpy $Portable 1
    ${EndIf}
    ClearErrors
    ${GetOptions} $R0 "/RELAUNCH" $R1
    ${IfNot} ${Errors}
        StrCpy $Relaunch 1
    ${EndIf}
    ClearErrors
FunctionEnd

Section "CleanCutPDF" SecMain

    ; ---- Wait for a running CleanCutPDF to close (the updater starts us, then the app exits).
    ; A running program's file cannot be opened for writing, so this needs no plugin.
    StrCpy $R2 0
    waitForApp:
    ${If} ${FileExists} "$INSTDIR\${APP_EXE}"
        ClearErrors
        FileOpen $R1 "$INSTDIR\${APP_EXE}" a
        ${If} ${Errors}
            IntOp $R2 $R2 + 1
            ${If} $R2 < 120
                Sleep 500
                Goto waitForApp
            ${EndIf}
            IfSilent stillRunning
            MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "CleanCutPDF is still open.$\r$\n$\r$\nClose it, then choose Retry." IDRETRY retryWait
            stillRunning:
            SetErrorLevel 2
            Abort "CleanCutPDF is still running."
            retryWait:
            StrCpy $R2 0
            Goto waitForApp
        ${Else}
            FileClose $R1
        ${EndIf}
    ${EndIf}

    ; ---- Remove the previous version's program files (never user data).
    ; Only when this folder already holds CleanCutPDF, so a folder chosen by mistake is left alone.
    ${If} ${FileExists} "$INSTDIR\${APP_EXE}"
        Delete "$INSTDIR\*.dll"
        Delete "$INSTDIR\*.pdb"
        Delete "$INSTDIR\CleanCutPDF.deps.json"
        Delete "$INSTDIR\CleanCutPDF.runtimeconfig.json"
        ; CleanCutPDF 1.x: its separate updater and rollback copy are no longer needed.
        Delete "$INSTDIR\CleanCutPDFUpdater.exe"
        Delete "$INSTDIR\CleanCutPDFUpdaterv1.0.exe"
        Delete "$INSTDIR\CleanCutPDF.old.exe"
    ${EndIf}

    SetOutPath "$INSTDIR"
    File /r "${PUBLISH_DIR}\*.*"

    ; ---- Tells the app how it was installed, so it knows it may update itself.
    FileOpen $R1 "$INSTDIR\${MARKER}" w
    ${If} $Portable == 1
        FileWrite $R1 "portable"
    ${Else}
        FileWrite $R1 "registered"
    ${EndIf}
    FileClose $R1

    ${If} $Portable != 1
        CreateDirectory "$SMPROGRAMS\CleanCutPDF"
        CreateShortcut "$SMPROGRAMS\CleanCutPDF\CleanCutPDF.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}"
        CreateShortcut "$DESKTOP\CleanCutPDF.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}"
        WriteUninstaller "$INSTDIR\Uninstall.exe"

        WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayName" "${APP_NAME}"
        WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayVersion" "${APP_VERSION}"
        WriteRegStr HKCU "${UNINSTALL_KEY}" "Publisher" "${APP_PUBLISHER}"
        WriteRegStr HKCU "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
        WriteRegStr HKCU "${UNINSTALL_KEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
        WriteRegStr HKCU "${UNINSTALL_KEY}" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
        WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
        WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoModify" 1
        WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoRepair" 1
    ${EndIf}

SectionEnd

Function .onInstSuccess
    ${If} $Relaunch == 1
        Exec '"$INSTDIR\${APP_EXE}"'
    ${EndIf}
FunctionEnd

; A failed update must not leave the user with nothing open: the old version starts again.
Function .onInstFailed
    ${If} $Relaunch == 1
    ${AndIf} ${FileExists} "$INSTDIR\${APP_EXE}"
        Exec '"$INSTDIR\${APP_EXE}"'
    ${EndIf}
FunctionEnd

Section "Uninstall"

    ; Exactly the files this version installed (list generated by build-installer.ps1).
    !include "${UNINSTALL_LIST}"
    Delete "$INSTDIR\${MARKER}"

    Delete "$DESKTOP\CleanCutPDF.lnk"
    Delete "$SMPROGRAMS\CleanCutPDF\CleanCutPDF.lnk"
    RMDir "$SMPROGRAMS\CleanCutPDF"
    DeleteRegKey HKCU "${UNINSTALL_KEY}"

    ; Silent uninstalls keep the data.
    MessageBox MB_YESNO|MB_ICONQUESTION "Would you also like to remove CleanCutPDF's settings and data?$\r$\n$\r$\nThis includes settings, workspaces, saved sessions, export history, logs, and license information.$\r$\n$\r$\nChoose No if you may reinstall CleanCutPDF later." /SD IDNO IDNO keepData
    RMDir /r "$PROFILE\.cleancutpdf-next"
    keepData:

    Delete "$INSTDIR\Uninstall.exe"
    RMDir "$INSTDIR"

SectionEnd
