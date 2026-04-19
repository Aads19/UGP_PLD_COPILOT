param(
    [string]$DatabaseDir = "C:\UGP - SHIKHA MISRA\New folder\UGP DATABASE",
    [string]$OutputDir = "C:\UGP - SHIKHA MISRA\New folder\UGP DATABASE\pld_pvd_classification_output"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName Microsoft.VisualBasic

$sources = @(
    @{
        Name = "acs"
        ParagraphPath = Join-Path $DatabaseDir "acs_para.csv"
    },
    @{
        Name = "aip"
        ParagraphPath = Join-Path $DatabaseDir "aip_para.csv"
    },
    @{
        Name = "els"
        ParagraphPath = Join-Path $DatabaseDir "els_para.csv"
    }
)

$PLDPattern = "(?i)\bPLD\b|pulsed\s+laser\s+deposition|pulsed-laser\s+deposition|laser\s+ablation\s+deposition|excimer\s+laser\s+deposition|KrF\s+laser|laser-deposited|ablation\s+target|laser\s+fluence"
$PVDPattern = "(?i)\bPVD\b|physical\s+vapou?r\s+deposition|sputter(?:ing|ed)?|magnetron\s+sputter(?:ing|ed)?|RF\s+sputter(?:ing|ed)?|DC\s+sputter(?:ing|ed)?|thermal\s+evaporation|e[- ]beam\s+evaporation|electron[- ]beam\s+evaporation|\bMBE\b|molecular\s+beam\s+epitaxy|cathodic\s+arc"
$ALDPattern = "(?i)\bALD\b|atomic\s+layer\s+deposition|atomic-layer\s+deposition|\bPEALD\b|plasma[- ]enhanced\s+atomic\s+layer\s+deposition"
$CVDPattern = "(?i)\bCVD\b|chemical\s+vapou?r\s+deposition|MOCVD|PECVD|LPCVD"
$OtherTechniquePattern = "(?i)\bALD\b|atomic\s+layer\s+deposition|atomic-layer\s+deposition|\bPEALD\b|plasma[- ]enhanced\s+atomic\s+layer\s+deposition|\bCVD\b|chemical\s+vapou?r\s+deposition|MOCVD|PECVD|LPCVD|sol[- ]gel|spin[- ]coat(?:ing)?|hydrothermal|electrodeposition|spray\s+pyrolysis|chemical\s+bath|molecular\s+layer\s+deposition|\bMLD\b"
$ComparisonPattern = "(?i)compare|compared|comparison|benchmark|versus|\bvs\.?\b|table\s+\d|tab\.\s*\d|reported|previously reported|literature|in contrast|whereas|higher than|lower than|similar to|relative to"
$QuantPattern = "(?i)\b\d+(?:\.\d+)?\s*(?:nm|μm|um|mm|cm|mTorr|Torr|Pa|mbar|°C|degC|K|eV|keV|W|mW|J|mJ|J/cm2|Hz|kHz|MHz|GHz|V|mV|A|mA|Ω|ohm|Ω·cm|cm2/V)"

function New-CsvParser {
    param([Parameter(Mandatory = $true)][string]$Path)

    $parser = [Microsoft.VisualBasic.FileIO.TextFieldParser]::new($Path, [System.Text.Encoding]::UTF8)
    $parser.TextFieldType = [Microsoft.VisualBasic.FileIO.FieldType]::Delimited
    $parser.SetDelimiters(",")
    $parser.HasFieldsEnclosedInQuotes = $true
    return $parser
}

function Normalize-FlatText {
    param([AllowNull()][string]$Value)

    if ($null -eq $Value) {
        return ""
    }

    $Value = [regex]::Replace($Value, "[\r\n\t]+", " ")
    $Value = [regex]::Replace($Value, "\s{2,}", " ")
    return $Value.Trim()
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

function Get-RegexCount {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)][string]$Pattern
    )

    return [regex]::Matches($Text, $Pattern).Count
}

function Get-RelevanceReason {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][bool]$MentionsPld,
        [Parameter(Mandatory = $true)][bool]$MentionsPvd,
        [Parameter(Mandatory = $true)][bool]$HasComparisonData,
        [Parameter(Mandatory = $true)][bool]$OtherTechniquePrimary
    )

    switch ($Label) {
        "CORE_PLD" {
            return "The title, abstract, and body repeatedly discuss PLD-specific deposition conditions, process details, or outcomes, so this paper is primarily about PLD."
        }
        "CORE_PVD" {
            return "The paper is primarily centered on non-PLD PVD methods such as sputtering, evaporation, MBE, or cathodic arc, with direct process discussion in the main content."
        }
        "RELEVANT_PLD_PVD" {
            if ($OtherTechniquePrimary) {
                return "The paper is primarily about another technique, but the body includes PLD/PVD comparisons, benchmark values, or quantitative references useful for PLD/PVD retrieval."
            }
            if ($HasComparisonData) {
                return "The paper is not primarily PLD/PVD, but it includes meaningful PLD/PVD comparison or benchmark content in the body text."
            }
            return "The body contains repeated PLD/PVD mentions that make the paper useful as supporting context even though PLD/PVD is not the primary topic."
        }
        default {
            if (-not $MentionsPld -and -not $MentionsPvd) {
                return "The paper does not contain meaningful PLD or PVD content in the title, abstract, or body text."
            }
            return "The paper only contains incidental PLD/PVD mentions without enough direct, quantitative, or comparative content to support PLD/PVD retrieval."
        }
    }
}

function Classify-Paper {
    param(
        [AllowEmptyString()][string]$Title,
        [AllowEmptyString()][string]$Abstract,
        [Parameter(Mandatory = $true)][string]$FullText
    )

    $titleNorm = Normalize-FlatText $Title
    $abstractNorm = Normalize-FlatText $Abstract
    $titleAbstract = "$titleNorm $abstractNorm"
    $fullNorm = Normalize-FlatText $FullText

    $mentionsPld = $fullNorm -match $script:PLDPattern
    $mentionsPvd = $fullNorm -match $script:PVDPattern
    $pldTitleAbstract = $titleAbstract -match $script:PLDPattern
    $pvdTitleAbstract = $titleAbstract -match $script:PVDPattern
    $aldPrimary = $titleAbstract -match $script:ALDPattern
    $otherTechniquePrimary = $titleAbstract -match $script:OtherTechniquePattern

    $pldCountFull = Get-RegexCount -Text $fullNorm -Pattern $script:PLDPattern
    $pvdCountFull = Get-RegexCount -Text $fullNorm -Pattern $script:PVDPattern
    $comparisonData = (($mentionsPld -or $mentionsPvd) -and (($fullNorm -match $script:ComparisonPattern) -or ($fullNorm -match $script:QuantPattern)))

    $label = "NOT_RELEVANT"

    if ($pldTitleAbstract) {
        $label = "CORE_PLD"
    }
    elseif ($pvdTitleAbstract -and -not $pldTitleAbstract) {
        $label = "CORE_PVD"
    }
    elseif ($aldPrimary -and ($mentionsPld -or $mentionsPvd)) {
        $label = "RELEVANT_PLD_PVD"
    }
    elseif ($otherTechniquePrimary -and ($mentionsPld -or $mentionsPvd)) {
        $label = "RELEVANT_PLD_PVD"
    }
    elseif (-not $otherTechniquePrimary -and $pldCountFull -ge 5 -and $pldCountFull -ge ($pvdCountFull + 1)) {
        $label = "CORE_PLD"
    }
    elseif (-not $otherTechniquePrimary -and $pvdCountFull -ge 5 -and $pvdCountFull -gt $pldCountFull) {
        $label = "CORE_PVD"
    }
    elseif (($mentionsPld -or $mentionsPvd) -and ($comparisonData -or (($pldCountFull + $pvdCountFull) -ge 2))) {
        $label = "RELEVANT_PLD_PVD"
    }

    return [pscustomobject]@{
        Label = $label
        MentionsPld = [bool]$mentionsPld
        MentionsPvd = [bool]$mentionsPvd
        HasComparisonData = [bool]$comparisonData
        RelevanceReason = Get-RelevanceReason -Label $label -MentionsPld ([bool]$mentionsPld) -MentionsPvd ([bool]$mentionsPvd) -HasComparisonData ([bool]$comparisonData) -OtherTechniquePrimary ([bool]$otherTechniquePrimary)
    }
}

function Add-PaperResult {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Doi,
        [AllowEmptyString()][object]$TitleText,
        [AllowEmptyString()][object]$AbstractText,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][object]$Paragraphs,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][System.Collections.Generic.List[object]]$PaperResults,
        [Parameter(Mandatory = $true)][hashtable]$SelectedDois
    )

    if ([string]::IsNullOrWhiteSpace($Doi)) {
        return
    }

    if ([string]$TitleText -eq "__EMPTY__") {
        $TitleText = ""
    }
    if ([string]$AbstractText -eq "__EMPTY__") {
        $AbstractText = ""
    }

    $titleNorm = Normalize-FlatText $TitleText
    $abstractNorm = Normalize-FlatText $AbstractText
    $paragraphItems = @()
    if ($Paragraphs -is [System.Collections.IEnumerable] -and -not ($Paragraphs -is [string])) {
        $paragraphItems = @($Paragraphs)
    }
    elseif ($null -ne $Paragraphs) {
        $paragraphItems = @([string]$Paragraphs)
    }
    $paragraphText = ($paragraphItems | ForEach-Object { Normalize-FlatText ([string]$_) }) -join " "
    $classification = Classify-Paper -Title $titleNorm -Abstract $abstractNorm -FullText $paragraphText

    $paper = [pscustomobject]@{
        Source = $Source
        Doi = $Doi.Trim()
        Title = $titleNorm
        Abstract = $abstractNorm
        PldPvdLabel = $classification.Label
        MentionsPld = $classification.MentionsPld
        MentionsPvd = $classification.MentionsPvd
        HasComparisonData = $classification.HasComparisonData
        RelevanceReason = $classification.RelevanceReason
        ParagraphCount = $paragraphItems.Count
    }

    [void]$PaperResults.Add($paper)

    if ($classification.Label -in @("CORE_PLD", "RELEVANT_PLD_PVD")) {
        $SelectedDois[$Doi.Trim()] = $true
    }
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$paperResults = New-Object System.Collections.Generic.List[object]
$selectedDois = @{}

foreach ($source in $sources) {
    Write-Host "Reconstructing and classifying papers from $($source.Name)..."

    $parser = New-CsvParser $source.ParagraphPath
    $header = $parser.ReadFields()
    if ($header.Count -lt 4 -or $header[0] -ne "doi") {
        throw "Unexpected header in $($source.ParagraphPath)"
    }

    $currentDoi = $null
    $currentTitle = ""
    $currentAbstract = ""
    $currentParagraphs = New-Object System.Collections.Generic.List[string]

    while (-not $parser.EndOfData) {
        $fields = $parser.ReadFields()
        if ($fields.Count -lt 4) {
            continue
        }

        $rowDoi = $fields[0].Trim()
        if (-not [string]::IsNullOrWhiteSpace($rowDoi)) {
            if ($null -ne $currentDoi) {
                Add-PaperResult -Source $source.Name -Doi $currentDoi -TitleText $(if ([string]::IsNullOrEmpty([string]$currentTitle)) { "__EMPTY__" } else { [string]$currentTitle }) -AbstractText $(if ([string]::IsNullOrEmpty([string]$currentAbstract)) { "__EMPTY__" } else { [string]$currentAbstract }) -Paragraphs $currentParagraphs -PaperResults $paperResults -SelectedDois $selectedDois
            }

            $currentDoi = $rowDoi
            $currentTitle = $fields[1]
            $currentAbstract = $fields[2]
            $currentParagraphs = New-Object System.Collections.Generic.List[string]
        }

        [void]$currentParagraphs.Add($fields[3])
    }

    Add-PaperResult -Source $source.Name -Doi $currentDoi -TitleText $(if ([string]::IsNullOrEmpty([string]$currentTitle)) { "__EMPTY__" } else { [string]$currentTitle }) -AbstractText $(if ([string]::IsNullOrEmpty([string]$currentAbstract)) { "__EMPTY__" } else { [string]$currentAbstract }) -Paragraphs $currentParagraphs -PaperResults $paperResults -SelectedDois $selectedDois
    $parser.Close()
}

$duplicatePaperCount = @($paperResults | Group-Object Doi | Where-Object { $_.Count -gt 1 }).Count
$paperResults = @(
    $paperResults |
        Group-Object Doi |
        ForEach-Object { $_.Group[0] }
)

$classifiedCsvPath = Join-Path $OutputDir "classified_pld_pvd_papers.csv"
$classifiedWriter = [System.IO.StreamWriter]::new($classifiedCsvPath, $false, [System.Text.UTF8Encoding]::new($true))
try {
    Write-CsvRow $classifiedWriter @("doi", "title", "abstract", "pld_pvd_label", "mentions_pld", "mentions_pvd", "has_comparison_data", "relevance_reason")
    foreach ($paper in $paperResults | Sort-Object Source, Doi) {
        Write-CsvRow $classifiedWriter @(
            $paper.Doi,
            $paper.Title,
            $paper.Abstract,
            $paper.PldPvdLabel,
            ([string]$paper.MentionsPld).ToLower(),
            ([string]$paper.MentionsPvd).ToLower(),
            ([string]$paper.HasComparisonData).ToLower(),
            $paper.RelevanceReason
        )
    }
}
finally {
    $classifiedWriter.Close()
}

$chatbotCsvPath = Join-Path $OutputDir "pld_chatbot_database.csv"
$chatbotWriter = [System.IO.StreamWriter]::new($chatbotCsvPath, $false, [System.Text.UTF8Encoding]::new($true))
$chatbotRowsWritten = 0
try {
    Write-CsvRow $chatbotWriter @("doi", "title", "abstract", "paragraph")

    foreach ($source in $sources) {
        Write-Host "Exporting selected paragraph rows from $($source.Name)..."
        $parser = New-CsvParser $source.ParagraphPath
        [void]$parser.ReadFields()

        $currentDoi = $null
        $currentTitle = ""
        $currentAbstract = ""
        $keepCurrent = $false

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
                $keepCurrent = $selectedDois.ContainsKey($currentDoi)
            }

            if ($keepCurrent) {
                $doiOut = Normalize-FlatText $currentDoi
                $titleOut = Normalize-FlatText $currentTitle
                $abstractOut = Normalize-FlatText $currentAbstract
                $paragraphOut = Normalize-FlatText $fields[3]
                Write-CsvRow $chatbotWriter @($doiOut, $titleOut, $abstractOut, $paragraphOut)
                $chatbotRowsWritten++
            }
        }

        $parser.Close()
    }
}
finally {
    $chatbotWriter.Close()
}

$summaryLines = New-Object System.Collections.Generic.List[string]
$labelCounts = $paperResults | Group-Object PldPvdLabel | Sort-Object Name
$sourceCounts = $paperResults | Group-Object Source | Sort-Object Name
$selectedPaperCount = @($paperResults | Where-Object { $_.PldPvdLabel -in @("CORE_PLD", "RELEVANT_PLD_PVD") }).Count

[void]$summaryLines.Add("SUMMARY STATS")
[void]$summaryLines.Add("Total papers processed: $($paperResults.Count)")
[void]$summaryLines.Add("Duplicate DOIs removed from classified output: $duplicatePaperCount")
[void]$summaryLines.Add("Total selected for pld_chatbot_database.csv: $selectedPaperCount")
[void]$summaryLines.Add("Total paragraph rows exported: $chatbotRowsWritten")
[void]$summaryLines.Add("Papers mentioning PLD: $( @($paperResults | Where-Object { $_.MentionsPld }).Count )")
[void]$summaryLines.Add("Papers mentioning PVD: $( @($paperResults | Where-Object { $_.MentionsPvd }).Count )")
[void]$summaryLines.Add("Papers with comparison data: $( @($paperResults | Where-Object { $_.HasComparisonData }).Count )")
[void]$summaryLines.Add("")
[void]$summaryLines.Add("Counts by label:")
foreach ($group in $labelCounts) {
    [void]$summaryLines.Add("- $($group.Name): $($group.Count)")
}
[void]$summaryLines.Add("")
[void]$summaryLines.Add("Counts by source:")
foreach ($sourceGroup in $sourceCounts) {
    [void]$summaryLines.Add("- $($sourceGroup.Name): $($sourceGroup.Count) papers")
    $sourceLabelCounts = $sourceGroup.Group | Group-Object PldPvdLabel | Sort-Object Name
    foreach ($labelGroup in $sourceLabelCounts) {
        [void]$summaryLines.Add("  - $($labelGroup.Name): $($labelGroup.Count)")
    }
}

$summaryPath = Join-Path $OutputDir "summary_stats.txt"
[System.IO.File]::WriteAllLines($summaryPath, $summaryLines, [System.Text.UTF8Encoding]::new($true))

Write-Host ""
Write-Host "Done."
Write-Host "Classified per-paper CSV: $classifiedCsvPath"
Write-Host "Merged chatbot database: $chatbotCsvPath"
Write-Host "Summary stats: $summaryPath"
Write-Host ""
$summaryLines | ForEach-Object { Write-Host $_ }
