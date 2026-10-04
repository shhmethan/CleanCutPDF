# Builds the CleanCutPDF 2.x Windows installer.
#
#   powershell -ExecutionPolicy Bypass -File packaging\build-installer.ps1
#   powershell -ExecutionPolicy Bypass -File packaging\build-installer.ps1 -WriteManifest
#
# Steps: publish a self-contained win-x64 build (no .NET needed on the office
# computers), build the installer with NSIS, and print its SHA-256.
# -WriteManifest also puts the SHA-256 and download link into version.json.
# -Version overrides the version from Directory.Build.props (used for update rehearsals).
#
# Nothing is uploaded. After building, attach the installer to a GitHub release
# whose tag is v<version>, then push version.json.
#
# Keep this file ASCII: Windows PowerShell 5.1 misreads UTF-8 without a BOM.

param(
    [string]$Version = "",
    [string]$OutDir = "",
    [switch]$WriteManifest
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not $OutDir) { $OutDir = Join-Path $PSScriptRoot "out" }

if (-not $Version) {
    $props = [IO.File]::ReadAllText((Join-Path $root "Directory.Build.props"))
    if ($props -notmatch "<InformationalVersion>([^<]+)</InformationalVersion>") { throw "InformationalVersion not found in Directory.Build.props" }
    $Version = $Matches[1]
}
if ($Version -notmatch "^(\d+\.\d+\.\d+)") { throw "Version '$Version' must start with three numbers, for example 2.0.0-alpha.6" }
$numeric = $Matches[1]

$makensis = @("${env:ProgramFiles(x86)}\NSIS\makensis.exe", "$env:ProgramFiles\NSIS\makensis.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $makensis) { throw "NSIS was not found. Install it from https://nsis.sourceforge.io (the 1.x installer uses it too)." }

$publish = Join-Path $OutDir "publish"
$installer = Join-Path $OutDir "CleanCutPDF-$Version-Setup.exe"
$uninstallList = Join-Path $OutDir "uninstall-files.nsh"
if (Test-Path $publish) { Remove-Item -Recurse -Force $publish }
New-Item -ItemType Directory -Force $OutDir | Out-Null

Write-Host "Publishing CleanCutPDF $Version (self-contained, win-x64)..."
& dotnet publish (Join-Path $root "src\CleanCutPDF.App") -c Release -r win-x64 --self-contained true `
    "-p:InformationalVersion=$Version" -p:DebugType=none -p:DebugSymbols=false -o $publish -nologo -v q
if ($LASTEXITCODE -ne 0) { throw "dotnet publish failed" }
if (-not (Test-Path (Join-Path $publish "CleanCutPDF.exe"))) { throw "CleanCutPDF.exe was not produced" }

# The uninstaller removes exactly what was installed: files first, then folders, deepest first.
$lines = New-Object System.Collections.Generic.List[string]
Get-ChildItem $publish -Recurse -File | ForEach-Object {
    $lines.Add('Delete "$INSTDIR\' + $_.FullName.Substring($publish.Length + 1) + '"')
}
Get-ChildItem $publish -Recurse -Directory | Sort-Object { $_.FullName.Length } -Descending | ForEach-Object {
    $lines.Add('RMDir "$INSTDIR\' + $_.FullName.Substring($publish.Length + 1) + '"')
}
[IO.File]::WriteAllLines($uninstallList, $lines, (New-Object System.Text.UTF8Encoding($true)))

Write-Host "Building the installer..."
& $makensis /V2 "/DAPP_VERSION=$Version" "/DAPP_VERSION_NUMERIC=$numeric" "/DPUBLISH_DIR=$publish" "/DOUT_FILE=$installer" `
    "/DUNINSTALL_LIST=$uninstallList" "/DAPP_ICON=$(Join-Path $root 'src\CleanCutPDF.App\Assets\favicon.ico')" `
    (Join-Path $PSScriptRoot "CleanCutPDF.nsi")
if ($LASTEXITCODE -ne 0) { throw "makensis failed" }

$hash = (Get-FileHash $installer -Algorithm SHA256).Hash.ToLowerInvariant()
$url = "https://github.com/shhmethan/CleanCutPDF/releases/download/v$Version/CleanCutPDF-$Version-Setup.exe"
$sizeMb = [Math]::Round((Get-Item $installer).Length / 1MB, 1)

Write-Host ""
Write-Host "Installer : $installer ($sizeMb MB)"
Write-Host "SHA-256   : $hash"
Write-Host "Link      : $url"

if ($WriteManifest) {
    # Edited as text so the changelog (and its emoji) is left byte-for-byte alone.
    $manifestPath = Join-Path $root "version.json"
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    $text = [IO.File]::ReadAllText($manifestPath, $utf8)
    $text = [regex]::Replace($text, '"download_url"\s*:\s*"[^"]*"', ('"download_url": "' + $url + '"'), 1)
    $text = [regex]::Replace($text, '"sha256"\s*:\s*"[^"]*"', ('"sha256": "' + $hash + '"'), 1)
    [IO.File]::WriteAllText($manifestPath, $text, $utf8)
    Write-Host "version.json now has this link and SHA-256."
} else {
    Write-Host "Run again with -WriteManifest to put the link and SHA-256 into version.json."
}
