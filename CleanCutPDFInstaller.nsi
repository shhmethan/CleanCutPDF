!include "MUI2.nsh"

Name "CleanCutPDF"
OutFile "CleanCutPDF_Setup_v1.6.7.exe"

InstallDir "$LOCALAPPDATA\Programs\CleanCutPDF"

RequestExecutionLevel user

!define APP_NAME "CleanCutPDF"
!define APP_VERSION "1.6.7"
!define APP_PUBLISHER "CleanCutPDF"

!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\CleanCutPDF"

!define MUI_ABORTWARNING

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\CleanCutPDF.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch CleanCutPDF"

!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"


Section "CleanCutPDF" SecMain

    SetOutPath "$INSTDIR"

    File "dist\CleanCutPDF.exe"
    File "dist\CleanCutPDFUpdater.exe"

    CreateDirectory "$SMPROGRAMS\CleanCutPDF"

    CreateShortcut \
        "$SMPROGRAMS\CleanCutPDF\CleanCutPDF.lnk" \
        "$INSTDIR\CleanCutPDF.exe"

    CreateShortcut \
        "$DESKTOP\CleanCutPDF.lnk" \
        "$INSTDIR\CleanCutPDF.exe"

    WriteUninstaller "$INSTDIR\Uninstall.exe"


    ; ─────────────────────────────────────────
    ; WINDOWS INSTALLED APPS ENTRY
    ; ─────────────────────────────────────────

    WriteRegStr HKCU \
        "${UNINSTALL_KEY}" \
        "DisplayName" \
        "${APP_NAME}"

    WriteRegStr HKCU \
        "${UNINSTALL_KEY}" \
        "DisplayVersion" \
        "${APP_VERSION}"

    WriteRegStr HKCU \
        "${UNINSTALL_KEY}" \
        "Publisher" \
        "${APP_PUBLISHER}"

    WriteRegStr HKCU \
        "${UNINSTALL_KEY}" \
        "InstallLocation" \
        "$INSTDIR"

    WriteRegStr HKCU \
        "${UNINSTALL_KEY}" \
        "UninstallString" \
        '"$INSTDIR\Uninstall.exe"'

    WriteRegStr HKCU \
        "${UNINSTALL_KEY}" \
        "QuietUninstallString" \
        '"$INSTDIR\Uninstall.exe" /S'

    WriteRegStr HKCU \
        "${UNINSTALL_KEY}" \
        "DisplayIcon" \
        "$INSTDIR\CleanCutPDF.exe"

    WriteRegDWORD HKCU \
        "${UNINSTALL_KEY}" \
        "NoModify" \
        1

    WriteRegDWORD HKCU \
        "${UNINSTALL_KEY}" \
        "NoRepair" \
        1

SectionEnd


Section "Uninstall"

    ; Remove program files
    Delete "$INSTDIR\CleanCutPDF.exe"
    Delete "$INSTDIR\CleanCutPDFUpdater.exe"
    Delete "$INSTDIR\CleanCutPDF.old.exe"

    ; Remove shortcuts
    Delete "$DESKTOP\CleanCutPDF.lnk"

    Delete \
        "$SMPROGRAMS\CleanCutPDF\CleanCutPDF.lnk"

    RMDir \
        "$SMPROGRAMS\CleanCutPDF"

    ; Remove Windows Installed Apps entry
    DeleteRegKey HKCU \
        "${UNINSTALL_KEY}"

    ; Ask whether to delete user data
    MessageBox MB_YESNO|MB_ICONQUESTION \
        "Would you also like to remove all CleanCutPDF user data?$\r$\n$\r$\nThis includes settings, logs, saved sessions, keybinds, and license information.$\r$\n$\r$\nChoose No if you may reinstall CleanCutPDF later." \
        IDYES removeuserdata \
        IDNO keepuserdata

    removeuserdata:

        RMDir /r "$PROFILE\.cleancutpdf"

        Goto continueuninstall


    keepuserdata:

        Goto continueuninstall


    continueuninstall:

        Delete "$INSTDIR\Uninstall.exe"

        RMDir "$INSTDIR"

SectionEnd