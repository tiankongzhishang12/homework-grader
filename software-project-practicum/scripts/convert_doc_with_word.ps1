param(
    [Parameter(Mandatory = $true)]
    [string]$InputPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $InputPath)) {
    throw "Input file not found: $InputPath"
}

$outputDir = Split-Path -Parent $OutputPath
if (-not (Test-Path -LiteralPath $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

$word = $null
$document = $null

try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0

    $document = $word.Documents.Open($InputPath, $false, $true)
    $wdFormatXMLDocument = 16
    $document.SaveAs([ref]$OutputPath, [ref]$wdFormatXMLDocument)
    $document.Close()
    $word.Quit()
}
catch {
    if ($document -ne $null) {
        try { $document.Close() } catch {}
    }
    if ($word -ne $null) {
        try { $word.Quit() } catch {}
    }
    throw
}
