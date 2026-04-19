param(
    [string]$DatabaseDir = "C:\UGP - SHIKHA MISRA\New folder\UGP DATABASE",
    [string]$OutputDir = "C:\UGP - SHIKHA MISRA\New folder\UGP DATABASE\pld_filtered",
    [ValidateSet("FullText", "TitleAbstract", "Title")]
    [string]$MatchScope = "FullText"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName Microsoft.VisualBasic

$pldPattern = "(?i)\bPLD\b|pulsed\s+laser\s+deposition|pulsed-laser\s+deposition"

$sources = @(
    @{
        Name = "acs"
        SentencePath = Join-Path $DatabaseDir "Sentence split with doi\Sentences_Kept_All_Columns_acs.csv"
        ParagraphPath = Join-Path $DatabaseDir "acs_para.csv"
    },
    @{
        Name = "aip"
        SentencePath = Join-Path $DatabaseDir "Sentence split with doi\Sentences_Kept_All_Columns_aip.csv"
        ParagraphPath = Join-Path $DatabaseDir "aip_para.csv"
    },
    @{
        Name = "els"
        SentencePath = Join-Path $DatabaseDir "Sentence split with doi\Sentences_Kept_All_Columns_els.csv"
        ParagraphPath = Join-Path $DatabaseDir "els_para.csv"
    }
)

function New-CsvParser {
    param([Parameter(Mandatory = $true)][string]$Path)

    $parser = [Microsoft.VisualBasic.FileIO.TextFieldParser]::new($Path, [System.Text.Encoding]::UTF8)
    $parser.TextFieldType = [Microsoft.VisualBasic.FileIO.FieldType]::Delimited
    $parser.SetDelimiters(",")
    $parser.HasFieldsEnclosedInQuotes = $true
    return $parser
}

function Escape-CsvField {
    param([AllowNull()][string]$Value)

    if ($null -eq $Value) {
        return ""
    }

    if ($Value -match '[,"\r\n]') {
        return '"' + ($Value -replace '"', '""') + '"'
    }

    return $Value
}

function Normalize-FlatText {
    param([AllowNull()][string]$Value)

    if ($null -eq $Value) {
        return ""
    }

    return (($Value -replace "\r\n", " ") -replace "[\r\n\t]+", " ") -replace "\s{2,}", " "
}

function Write-CsvRow {
    param(
        [Parameter(Mandatory = $true)][System.IO.StreamWriter]$Writer,
        [Parameter(Mandatory = $true)][AllowEmptyString()][string[]]$Fields
    )

    $escaped = foreach ($field in $Fields) {
        Escape-CsvField $field
    }
    $Writer.WriteLine(($escaped -join ","))
}

function Add-PldArticleIfMatched {
    param(
        [Parameter(Mandatory = $true)][hashtable]$PldArticles,
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Doi,
        [Parameter(Mandatory = $true)][string]$Title,
        [Parameter(Mandatory = $true)][string]$Abstract,
        [Parameter(Mandatory = $true)][System.Text.StringBuilder]$SentenceText
    )

    if ([string]::IsNullOrWhiteSpace($Doi)) {
        return
    }

    $articleText = switch ($script:MatchScope) {
        "Title" { $Title }
        "TitleAbstract" { "$Title $Abstract" }
        default { "$Title $Abstract $($SentenceText.ToString())" }
    }
    if ($articleText -match $script:pldPattern) {
        $normalizedDoi = $Doi.Trim()
        if (-not $PldArticles.ContainsKey($normalizedDoi)) {
            $PldArticles[$normalizedDoi] = [pscustomobject]@{
                Source = $Source
                Doi = $normalizedDoi
                Title = $Title.Trim()
            }
        }
    }
}

function Find-PldDoisFromSentenceFile {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$SentencePath,
        [Parameter(Mandatory = $true)][hashtable]$PldArticles
    )

    Write-Host "Scanning sentence file for PLD papers: $Source"

    $parser = New-CsvParser $SentencePath
    [void]$parser.ReadFields()

    $currentDoi = $null
    $currentTitle = ""
    $currentAbstract = ""
    $sentenceText = New-Object System.Text.StringBuilder

    while (-not $parser.EndOfData) {
        $fields = $parser.ReadFields()
        if ($fields.Count -lt 4) {
            continue
        }

        $doi = $fields[0].Trim()
        if ($null -ne $currentDoi -and $doi -ne $currentDoi) {
            Add-PldArticleIfMatched `
                -PldArticles $PldArticles `
                -Source $Source `
                -Doi $currentDoi `
                -Title $currentTitle `
                -Abstract $currentAbstract `
                -SentenceText $sentenceText
            $sentenceText = New-Object System.Text.StringBuilder
        }

        if ($doi -ne $currentDoi) {
            $currentDoi = $doi
            $currentTitle = $fields[1]
            $currentAbstract = $fields[2]
        }

        [void]$sentenceText.Append($fields[3]).Append(" ")
    }

    Add-PldArticleIfMatched `
        -PldArticles $PldArticles `
        -Source $Source `
        -Doi $currentDoi `
        -Title $currentTitle `
        -Abstract $currentAbstract `
        -SentenceText $sentenceText

    $parser.Close()
}

function Write-PldDoiManifest {
    param(
        [Parameter(Mandatory = $true)][hashtable]$PldArticles,
        [Parameter(Mandatory = $true)][string]$OutputPath
    )

    $writer = [System.IO.StreamWriter]::new($OutputPath, $false, [System.Text.UTF8Encoding]::new($true))
    try {
        Write-CsvRow $writer @("source", "doi", "title")
        $PldArticles.Values |
            Sort-Object Source, Doi |
            ForEach-Object {
                Write-CsvRow $writer @($_.Source, $_.Doi, $_.Title)
            }
    }
    finally {
        $writer.Close()
    }
}

function Filter-ParagraphFileToPldPapers {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$ParagraphPath,
        [Parameter(Mandatory = $true)][hashtable]$PldArticles,
        [Parameter(Mandatory = $true)][string]$OutputPath
    )

    Write-Host "Filtering paragraph file to PLD papers: $Source"

    $parser = New-CsvParser $ParagraphPath
    $header = $parser.ReadFields()
    if ($header.Count -lt 4 -or $header[0] -ne "doi") {
        throw "Unexpected paragraph CSV header in $ParagraphPath"
    }

    $writer = [System.IO.StreamWriter]::new($OutputPath, $false, [System.Text.UTF8Encoding]::new($true))
    $seenDois = [System.Collections.Generic.HashSet[string]]::new()
    $writtenRows = 0

    try {
        Write-CsvRow $writer $header

        $currentDoi = $null
        $keepCurrentArticle = $false

        while (-not $parser.EndOfData) {
            $fields = $parser.ReadFields()
            if ($fields.Count -lt $header.Count) {
                $padded = New-Object string[] $header.Count
                for ($i = 0; $i -lt $fields.Count; $i++) {
                    $padded[$i] = $fields[$i]
                }
                $fields = $padded
            }

            $rowDoi = $fields[0].Trim()

            # Blank DOI rows are continuation paragraphs for the previous paper.
            if (-not [string]::IsNullOrWhiteSpace($rowDoi)) {
                $currentDoi = $rowDoi
                $keepCurrentArticle = $PldArticles.ContainsKey($currentDoi)
                if ($keepCurrentArticle) {
                    [void]$seenDois.Add($currentDoi)
                }
            }

            if ($keepCurrentArticle) {
                Write-CsvRow $writer $fields
                $writtenRows++
            }
        }
    }
    finally {
        $writer.Close()
        $parser.Close()
    }

    return [pscustomobject]@{
        Source = $Source
        OutputPath = $OutputPath
        PapersWritten = $seenDois.Count
        RowsWritten = $writtenRows
    }
}

function Write-FlatPldParagraphFile {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$ParagraphPath,
        [Parameter(Mandatory = $true)][hashtable]$PldArticles,
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [Parameter(Mandatory = $true)][System.IO.StreamWriter]$CombinedWriter
    )

    Write-Host "Writing flat paragraph file for easy loading: $Source"

    $parser = New-CsvParser $ParagraphPath
    [void]$parser.ReadFields()

    $writer = [System.IO.StreamWriter]::new($OutputPath, $false, [System.Text.UTF8Encoding]::new($true))
    $seenDois = [System.Collections.Generic.HashSet[string]]::new()
    $writtenRows = 0

    try {
        Write-CsvRow $writer @("source", "doi", "title", "abstract", "paragraph_index", "paragraph")

        $currentDoi = $null
        $currentTitle = ""
        $currentAbstract = ""
        $keepCurrentArticle = $false
        $paragraphIndex = 0

        while (-not $parser.EndOfData) {
            $fields = $parser.ReadFields()
            if ($fields.Count -lt 4) {
                continue
            }

            $rowDoi = $fields[0].Trim()
            if (-not [string]::IsNullOrWhiteSpace($rowDoi)) {
                $currentDoi = $rowDoi
                $currentTitle = $fields[1]
                $currentAbstract = $fields[2]
                $keepCurrentArticle = $PldArticles.ContainsKey($currentDoi)
                $paragraphIndex = 0
                if ($keepCurrentArticle) {
                    [void]$seenDois.Add($currentDoi)
                }
            }

            if ($keepCurrentArticle) {
                $paragraphIndex++
                $flatRow = @(
                    $Source,
                    (Normalize-FlatText $currentDoi),
                    (Normalize-FlatText $currentTitle),
                    (Normalize-FlatText $currentAbstract),
                    ([string]$paragraphIndex),
                    (Normalize-FlatText $fields[3])
                )
                Write-CsvRow $writer $flatRow
                Write-CsvRow $CombinedWriter $flatRow
                $writtenRows++
            }
        }
    }
    finally {
        $writer.Close()
        $parser.Close()
    }

    return [pscustomobject]@{
        Source = $Source
        OutputPath = $OutputPath
        PapersWritten = $seenDois.Count
        RowsWritten = $writtenRows
    }
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$pldArticles = @{}
foreach ($source in $sources) {
    Find-PldDoisFromSentenceFile `
        -Source $source.Name `
        -SentencePath $source.SentencePath `
        -PldArticles $pldArticles
}

$manifestPath = Join-Path $OutputDir "pld_dois.csv"
Write-PldDoiManifest -PldArticles $pldArticles -OutputPath $manifestPath

$filterStats = foreach ($source in $sources) {
    $outputPath = Join-Path $OutputDir ("{0}_para_pld_only.csv" -f $source.Name)
    Filter-ParagraphFileToPldPapers `
        -Source $source.Name `
        -ParagraphPath $source.ParagraphPath `
        -PldArticles $pldArticles `
        -OutputPath $outputPath
}

$combinedFlatPath = Join-Path $OutputDir "pld_paragraphs_flat.csv"
$combinedFlatWriter = [System.IO.StreamWriter]::new($combinedFlatPath, $false, [System.Text.UTF8Encoding]::new($true))
try {
    Write-CsvRow $combinedFlatWriter @("source", "doi", "title", "abstract", "paragraph_index", "paragraph")
    $flatStats = foreach ($source in $sources) {
        $flatOutputPath = Join-Path $OutputDir ("{0}_para_pld_only_flat.csv" -f $source.Name)
        Write-FlatPldParagraphFile `
            -Source $source.Name `
            -ParagraphPath $source.ParagraphPath `
            -PldArticles $pldArticles `
            -OutputPath $flatOutputPath `
            -CombinedWriter $combinedFlatWriter
    }
}
finally {
    $combinedFlatWriter.Close()
}

Write-Host ""
Write-Host "Done."
Write-Host "PLD DOI manifest: $manifestPath"
Write-Host "Unique PLD papers found: $($pldArticles.Count)"
Write-Host ""
Write-Host "Filtered paragraph outputs:"
$filterStats | Format-Table Source, PapersWritten, RowsWritten, OutputPath -AutoSize
Write-Host ""
Write-Host "Easy-load flat paragraph outputs:"
$flatStats | Format-Table Source, PapersWritten, RowsWritten, OutputPath -AutoSize
Write-Host "Combined flat paragraph output: $combinedFlatPath"
