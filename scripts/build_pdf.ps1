# Author: Hao Jinde
# Turn the .docx produced by scripts/make_report.py into the final Word file + PDF:
#   1) update the TOC field (python-docx can only write a placeholder; page numbers need Word layout)
#   2) TOC 1 / TOC 2 styles only exist after the first field update, so compress them afterwards
#   3) save back to .docx (keeps the resolved TOC), then export a PDF next to it
# Usage: powershell -ExecutionPolicy Bypass -File scripts/build_pdf.ps1 [-DocsDir <path>]
# Kept ASCII-only on purpose: PS 5.1 reads a BOM-less script as ANSI, and Chinese
# literals in a .ps1 file get mangled on some machines. The document name is found
# by wildcard instead of being written out here.
#
# Two things learned the hard way, both encoded below:
#   * Word's COM Documents.Open() does not fail on a path with Chinese characters --
#     it just never returns (measured > 4 min, no error). So the work happens in an
#     ASCII temp directory and the results are copied back at the end.
#   * ExportAsFixedFormat() crashes the Word instance on this machine once the
#     document carries seven 2x-resolution figures; SaveAs2(..., 17) exports the
#     same PDF in ~13 s. ExportAsFixedFormat stays as a fallback only.
#   * Document.Close() / Application.Quit() block forever after the export (some
#     invisible dialog). The script therefore kills only the WINWORD processes it
#     started itself, then copies the two output files back to docs/.
param([string]$DocsDir)

$ErrorActionPreference = 'Stop'

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
Copy-Item -LiteralPath $src.FullName -Destination $tmpDocx -Force

$word = $null
$doc = $null
$startedAt = Get-Date
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    # do not ask about updating links / templates while running headless
    $word.Options.UpdateLinksAtOpen = $false

    $doc = $word.Documents.Open($tmpDocx, $false, $false, $false)

    foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
    $doc.Repaginate()

    # single line spacing for TOC entries, otherwise a 29-page report grows to 30
    # and the TOC starts spilling onto a second page
    foreach ($name in @('TOC 1', 'TOC 2')) {
        try {
            $style = $doc.Styles.Item($name)
            $style.ParagraphFormat.LineSpacingRule = 0
            $style.ParagraphFormat.SpaceBefore = 0
            $style.ParagraphFormat.SpaceAfter = 0
        } catch { }
    }
    $doc.Repaginate()

    $pages = $doc.ComputeStatistics(2)          # 2 = wdStatisticPages
    $doc.Save()                                  # write the resolved TOC back into the .docx

    try {
        $doc.SaveAs2($tmpPdf, 17)                # 17 = wdFormatPDF, the fast path here
    } catch {
        $doc.ExportAsFixedFormat($tmpPdf, 17)    # fallback: slower, occasionally crashes Word
    }

    Write-Output ("docx : " + $src.FullName)
    Write-Output ("pdf  : " + $pdfPath)
    Write-Output ("pages: " + $pages)
}
finally {
    # Close()/Quit() hang here; kill only the instance this run created so a Word
    # window the user has open with their own document is left alone. The process
    # is ended without closing the document, which is safe because both outputs
    # were already written to disk by then.
    Get-Process -Name WINWORD -ErrorAction SilentlyContinue |
        Where-Object { $_.StartTime -ge $startedAt } |
        Stop-Process -Force
    Start-Sleep -Seconds 2
    [GC]::Collect()
}

# Copy back only after Word released its handles: copying while the document is still
# open fails with "file is being used by another process". Retry briefly in case the
# COM server needs a moment to exit.
foreach ($pair in @(@($tmpDocx, $src.FullName), @($tmpPdf, $pdfPath))) {
    for ($i = 0; $i -lt 5; $i++) {
        try {
            Copy-Item -LiteralPath $pair[0] -Destination $pair[1] -Force
            break
        } catch {
            if ($i -eq 4) { throw }
            Start-Sleep -Seconds 2
        }
    }
}
