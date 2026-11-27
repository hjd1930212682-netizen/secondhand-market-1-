# Author: Hao Jinde
# Turn the .docx produced by scripts/make_report.py into the final Word file + PDF.
#
# Usage: powershell -ExecutionPolicy Bypass -File scripts/build_pdf.ps1 [-DocsDir <path>]
# Kept ASCII-only on purpose: PS 5.1 reads a BOM-less script as ANSI, and Chinese
# literals in a .ps1 file get mangled on some machines. The document name is found
# by wildcard instead of being written out here.
#
# Five things learned the hard way, all encoded below:
#
#   * Word's COM Documents.Open() does not fail on a path with Chinese characters --
#     it just never returns (measured > 4 min, no error). So the work happens in an
#     ASCII temp directory and the results are copied back at the end.
#
#   * Two phases, not one. Doing TablesOfContents.Update() + Save() + SaveAs2(pdf)
#     in a single Word session hangs this machine at SaveAs2: no error, no PDF, the
#     Word process just spins. Splitting into "open + update + save" and then
#     "open + export" makes each phase finish in 12-15 s. Phase 1 writes the
#     resolved TOC back into the .docx, so phase 2 only has to export.
#
#   * Do NOT set $word.Options.UpdateLinksAtOpen = $false. Every hang reproduced so
#     far had that line set, every clean run did not. It looks harmless; it is not.
#
#   * ExportAsFixedFormat() crashes the Word instance once the document carries
#     seven 2x-resolution figures; SaveAs2(..., 17) exports the same PDF in ~13 s.
#     ExportAsFixedFormat stays as a fallback only. Document.Close()/Quit() block
#     forever after the export (some invisible dialog), so each phase kills only the
#     WINWORD processes it started itself and then copies its output back to docs/.
#
#   * Phase 2 is still flaky: on the same unchanged document SaveAs2 sometimes
#     returns in ~13 s and sometimes never returns (Word sits at 100% CPU, no
#     error). A blocking COM call cannot be timed out from inside the script, so
#     there is no retry here -- if "pdf" is not printed within a minute, kill
#     WINWORD in Task Manager and run the script again. Nothing is corrupted by
#     the retry: phase 1 only re-updates the TOC and phase 2 overwrites the PDF.
param([string]$DocsDir)

$ErrorActionPreference = 'Stop'

function Get-WinwordIds {
    return @(Get-Process -Name WINWORD -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
}

function Stop-NewWinword {
    param([int[]]$Keep)
    Get-Process -Name WINWORD -ErrorAction SilentlyContinue |
        Where-Object { $Keep -notcontains $_.Id } |
        Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    [GC]::Collect()
}

function Copy-Back {
    param([string]$From, [string]$To)
    for ($i = 0; $i -lt 5; $i++) {
        try {
            Copy-Item -LiteralPath $From -Destination $To -Force
            return
        } catch {
            if ($i -eq 4) { throw }
            Start-Sleep -Seconds 2
        }
    }
}

if (-not $DocsDir) {
    $here = $PSScriptRoot
    if (-not $here) { $here = Split-Path -Parent $MyInvocation.MyCommand.Path }
    $DocsDir = Join-Path $here '..\docs'
}
$DocsDir = (Resolve-Path -LiteralPath $DocsDir).Path

$src = Get-ChildItem -LiteralPath $DocsDir -Filter '*.docx' |
    Where-Object { $_.Name -notlike '~$*' } |
    Select-Object -First 1
if (-not $src) { throw "no .docx found in $DocsDir" }
$pdfPath = Join-Path $src.DirectoryName ($src.BaseName + '.pdf')

# ASCII-only scratch space; see the note above about non-ASCII paths. A fresh
# directory per run: a leftover Word instance holding the previous copy is enough
# to make Document.Open wait forever, and the symptom looks identical to a hang.
$work = Join-Path $env:TEMP ('secondhand-report-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $work | Out-Null
$tmpDocx = Join-Path $work 'report.docx'
$tmpPdf = Join-Path $work 'report.pdf'

# ---- phase 1: resolve the TOC field and save the .docx ----------------------
# python-docx can only write a placeholder; page numbers need Word's layout.
# TOC 1 / TOC 2 styles only exist after the first field update, so they are
# compressed afterwards. Single line spacing keeps the 28-page report at 28
# pages instead of spilling the TOC onto a second page.
Copy-Item -LiteralPath $src.FullName -Destination $tmpDocx -Force
$keep = Get-WinwordIds
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0

    $doc = $word.Documents.Open($tmpDocx, $false, $false, $false)

    foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
    foreach ($name in @('TOC 1', 'TOC 2')) {
        try {
            $style = $doc.Styles.Item($name)
            $style.ParagraphFormat.LineSpacingRule = 0
            $style.ParagraphFormat.SpaceBefore = 0
            $style.ParagraphFormat.SpaceAfter = 0
        } catch { }
    }
    $doc.Repaginate()
    $pages = $doc.ComputeStatistics(2)      # 2 = wdStatisticPages
    $doc.Save()
    Write-Output ("docx : " + $src.FullName)
    Write-Output ("pages: " + $pages)
}
finally {
    Stop-NewWinword -Keep $keep
}
Copy-Back -From $tmpDocx -To $src.FullName

# ---- phase 2: export the PDF from the now-resolved .docx --------------------
# SaveAs2 is the fast path here; see the header note about ExportAsFixedFormat
# and about this phase occasionally hanging.
$keep = Get-WinwordIds
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0

    $doc = $word.Documents.Open($tmpDocx, $false, $false, $false)
    try {
        $doc.SaveAs2($tmpPdf, 17)            # 17 = wdFormatPDF
    } catch {
        $doc.ExportAsFixedFormat($tmpPdf, 17)
    }
    Write-Output ("pdf  : " + $pdfPath)
}
finally {
    Stop-NewWinword -Keep $keep
}
Copy-Back -From $tmpPdf -To $pdfPath
