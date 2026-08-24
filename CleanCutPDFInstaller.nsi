!include "MUI2.nsh"


; ─────────────────────────────────────────────
; CLEAN CUT PDF INSTALLER
; ─────────────────────────────────────────────

!define APP_NAME "CleanCutPDF"
!define APP_VERSION "1.9.18"
!define APP_PUBLISHER "CleanCutPDF"

!define APP_EXE "CleanCutPDF.exe"
!define UPDATER_EXE "CleanCutPDFUpdater.exe"

!define INSTALL_DIR "$LOCALAPPDATA\Programs\CleanCutPDF"
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\CleanCutPDF"

!define APP_ICON "FullApp\resources\favicon.ico"


; ─────────────────────────────────────────────
; INSTALLER CONFIGURATION
; ─────────────────────────────────────────────

Name "${APP_NAME}"
OutFile "Output\CleanCutPDFv${APP_VERSION}.exe"

InstallDir "${INSTALL_DIR}"
RequestExecutionLevel user

Unicode True
CRCCheck On
SetCompressor /SOLID lzma
SetDatablockOptimize On
ShowInstDetails show
ShowUninstDetails show


; ─────────────────────────────────────────────
; VERSION INFORMATION
; ─────────────────────────────────────────────

VIProductVersion "1.8.0.0"

VIAddVersionKey "ProductName" "${APP_NAME}"
VIAddVersionKey "ProductVersion" "${APP_VERSION}"
VIAddVersionKey "FileDescription" "${APP_NAME} Installer"
VIAddVersionKey "FileVersion" "${APP_VERSION}"
VIAddVersionKey "CompanyName" "${APP_PUBLISHER}"
VIAddVersionKey "LegalCopyright" "CleanCutPDF"


; ─────────────────────────────────────────────
; INSTALLER ICONS
; ─────────────────────────────────────────────

!define MUI_ICON "${APP_ICON}"
!define MUI_UNICON "${APP_ICON}"


; ─────────────────────────────────────────────
; MODERN UI SETTINGS
; ─────────────────────────────────────────────

!define MUI_ABORTWARNING

!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch CleanCutPDF"


; ─────────────────────────────────────────────
; INSTALL PAGES
; ─────────────────────────────────────────────

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH


; ─────────────────────────────────────────────
; UNINSTALL PAGES
; ─────────────────────────────────────────────

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES


; ─────────────────────────────────────────────
; LANGUAGE
; ─────────────────────────────────────────────

!insertmacro MUI_LANGUAGE "English"


; ─────────────────────────────────────────────
; MAIN INSTALL
; ─────────────────────────────────────────────

Section "CleanCutPDF" SecMain

    SetOutPath "$INSTDIR"

    ; Remove obsolete updater names from older versions
    Delete "$INSTDIR\CleanCutPDFUpdaterv1.0.exe"

    ; Install main application
    File "dist\${APP_EXE}"

    ; Install updater
    File "dist\${UPDATER_EXE}"

    ; Create Start Menu directory
    CreateDirectory "$SMPROGRAMS\CleanCutPDF"

    ; Start Menu shortcut
    CreateShortcut \
        "$SMPROGRAMS\CleanCutPDF\CleanCutPDF.lnk" \
        "$INSTDIR\${APP_EXE}" \
        "" \
        "$INSTDIR\${APP_EXE}"

    ; Desktop shortcut
    CreateShortcut \
        "$DESKTOP\CleanCutPDF.lnk" \
        "$INSTDIR\${APP_EXE}" \
        "" \
        "$INSTDIR\${APP_EXE}"

    ; Create uninstaller
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
        "$INSTDIR\${APP_EXE}"

    WriteRegDWORD HKCU \
        "${UNINSTALL_KEY}" \
        "NoModify" \
        1

    WriteRegDWORD HKCU \
        "${UNINSTALL_KEY}" \
        "NoRepair" \
        1

SectionEnd


; ─────────────────────────────────────────────
; UNINSTALL
; ─────────────────────────────────────────────

Section "Uninstall"

    ; ─────────────────────────────────────────
    ; REMOVE APPLICATION FILES
    ; ─────────────────────────────────────────

    Delete "$INSTDIR\${APP_EXE}"
    Delete "$INSTDIR\${UPDATER_EXE}"

    ; Legacy updater from 1.6.7
    Delete "$INSTDIR\CleanCutPDFUpdaterv1.0.exe"

    ; Previous-version rollback copy
    Delete "$INSTDIR\CleanCutPDF.old.exe"


    ; ─────────────────────────────────────────
    ; REMOVE SHORTCUTS
    ; ─────────────────────────────────────────

    Delete "$DESKTOP\CleanCutPDF.lnk"

    Delete \
        "$SMPROGRAMS\CleanCutPDF\CleanCutPDF.lnk"

    RMDir "$SMPROGRAMS\CleanCutPDF"


    ; ─────────────────────────────────────────
    ; REMOVE WINDOWS INSTALLED APPS ENTRY
    ; ─────────────────────────────────────────

    DeleteRegKey HKCU "${UNINSTALL_KEY}"


    ; ─────────────────────────────────────────
    ; USER DATA
    ; ─────────────────────────────────────────

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