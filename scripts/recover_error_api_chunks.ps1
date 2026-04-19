param(
    [string]$InputCsv = "C:\Users\Aadi Jain\Downloads\Highly_Relevant_Batch3_Classified (1).csv",
    [string]$OutputCsv = "C:\UGP - SHIKHA MISRA\Highly_Relevant_Batch3_Classified_Recovered.csv",
    [string]$CorrectionsCsv = "C:\UGP - SHIKHA MISRA\Highly_Relevant_Batch3_Error_API_Replacements.csv"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$orderedTags = @("Background", "Synthesis", "Characterization", "Analysis")

function Get-NormalizedText {
    param([AllowNull()][string]$Text)

    if ($null -eq $Text) {
        return ""
    }

    $value = $Text.ToLowerInvariant()
    $value = [regex]::Replace($value, "\s+", " ")
    return $value.Trim()
}

function Test-Regex {
    param(
        [string]$Text,
        [string]$Pattern
    )

    return [regex]::IsMatch($Text, $Pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
}

function Get-RecoveredTags {
    param(
        [string]$Title,
        [string]$Chunk
    )

    $text = Get-NormalizedText("$Title $Chunk")
    $chunkOnly = Get-NormalizedText($Chunk)
    $tags = New-Object System.Collections.Generic.List[string]

    $ackOnly = (
        (Test-Regex $chunkOnly "(financial support|acknowledg|grant|supported by|conflict of interest|competing financial interests|thanks to|technical support|patent|patents|applications have been applied)") -and
        -not (Test-Regex $chunkOnly "(xrd|sem|tem|afm|raman|ftir|xps|deposit|deposition|sputter|pld|pvd|measured|results|shows|indicates)")
    )

    if ($ackOnly) {
        return @()
    }

    $backgroundPatterns = @(
        "has attracted much attention",
        "of considerable interest",
        "advantageous for use",
        "applications",
        "however",
        "recently",
        "previously",
        "over the last years",
        "in this study",
        "important",
        "challenge",
        "remains",
        "it is of extreme importance",
        "several studies",
        "reported"
    )

    $synthesisPatterns = @(
        "\bgrow(n|th)?\b",
        "\bdeposit(ed|ion)?\b",
        "\bfabricat(ed|ion)?\b",
        "\bprepar(ed|ation)?\b",
        "\bsputter(?:ed|ing)?\b",
        "\bpld\b",
        "pulsed laser deposition",
        "\bpvd\b",
        "\brf\b",
        "\bdc\b",
        "\btarget\b",
        "\bsubstrate\b",
        "\boxygen pressure\b",
        "\btemperature\b",
        "\bheated\b",
        "\bsonicat(?:ed|ing)\b",
        "\betch(?:ed|ing)?\b",
        "\banneal(?:ed|ing)?\b",
        "\bpulse\b",
        "\bgas\b",
        "\bchamber\b",
        "\bvoltage\b",
        "\bcurrent\b",
        "\bpower\b"
    )

    $characterizationPatterns = @(
        "\bxrd\b",
        "x-ray diffraction",
        "\brheed\b",
        "\bxps\b",
        "\bsem\b",
        "\btem\b",
        "\bhrtem\b",
        "\bed\b",
        "\bafm\b",
        "\bftir\b",
        "\braman\b",
        "\bgixrr\b",
        "\brbs\b",
        "\bsrim\b",
        "\buv\b",
        "\boptical\b",
        "micrograph",
        "surface image",
        "characteriz",
        "measur",
        "diffraction peak",
        "rocking curve",
        "\bphi-scan\b",
        "depth profile",
        "microhardness",
        "contact angle",
        "spectrometer",
        "microscope",
        "peak position",
        "electron mobility",
        "resistivity"
    )

    $analysisPatterns = @(
        "indicat",
        "suggest",
        "therefore",
        "thus",
        "because",
        "due to",
        "correlat",
        "consistent with",
        "showed that",
        "revealing",
        "resulted in",
        "lead(s|ing)? to",
        "improv",
        "decrease",
        "increase",
        "explained",
        "mechanism",
        "model",
        "simulation",
        "calculat",
        "fitting",
        "transition",
        "responsible for",
        "useful for",
        "chosen",
        "is unlikely",
        "compared to",
        "in contrast",
        "this is the reason"
    )

    foreach ($pattern in $backgroundPatterns) {
        if (Test-Regex $chunkOnly $pattern) {
            [void]$tags.Add("Background")
            break
        }
    }

    foreach ($pattern in $synthesisPatterns) {
        if (Test-Regex $chunkOnly $pattern) {
            [void]$tags.Add("Synthesis")
            break
        }
    }

    foreach ($pattern in $characterizationPatterns) {
        if (Test-Regex $chunkOnly $pattern) {
            [void]$tags.Add("Characterization")
            break
        }
    }

    foreach ($pattern in $analysisPatterns) {
        if (Test-Regex $chunkOnly $pattern) {
            [void]$tags.Add("Analysis")
            break
        }
    }

    if ((Test-Regex $chunkOnly "(mathematical modeling|one-dimensional model|pic method|simulation)") -and -not ($tags -contains "Analysis")) {
        [void]$tags.Add("Analysis")
    }

    if ((Test-Regex $chunkOnly "(studied|reported|demonstrates|demonstrated|importance|advantageous|interest)") -and -not ($tags -contains "Background")) {
        [void]$tags.Add("Background")
    }

    if ((Test-Regex $chunkOnly "(measured|measurements|scan|spectra|images|fitting result)") -and -not ($tags -contains "Characterization")) {
        [void]$tags.Add("Characterization")
    }

    if ((Test-Regex $chunkOnly "(deposition was performed|samples were|films were|substrates were|produced|synthesi[sz]e|synthesi[sz]ed)") -and -not ($tags -contains "Synthesis")) {
        [void]$tags.Add("Synthesis")
    }

    $uniqueOrdered = foreach ($tag in $orderedTags) {
        if ($tags -contains $tag) {
            $tag
        }
    }

    return @($uniqueOrdered)
}

$rows = Import-Csv $InputCsv
$corrections = New-Object System.Collections.Generic.List[object]
$errorCountBefore = 0

foreach ($row in $rows) {
    if ($row.tags -match "Error_API") {
        $errorCountBefore += 1
        $newTags = Get-RecoveredTags -Title $row.title -Chunk $row.text_chunk
        if (@($newTags).Count -eq 0) {
            $row.tags = '{"tags":[]}'
        }
        else {
            $row.tags = (@{ tags = @($newTags) } | ConvertTo-Json -Compress)
        }

        [void]$corrections.Add([pscustomobject]@{
            doi = $row.doi
            title = $row.title
            chunk_start_idx = $row.chunk_start_idx
            recovered_tags = $row.tags
        })
    }
}

$rows | Export-Csv -Path $OutputCsv -NoTypeInformation -Encoding UTF8
$corrections | Export-Csv -Path $CorrectionsCsv -NoTypeInformation -Encoding UTF8

$errorCountAfter = @(
    Import-Csv $OutputCsv | Where-Object { $_.tags -match "Error_API" }
).Count

Write-Host "Recovered rows:" $errorCountBefore
Write-Host "Remaining Error_API rows:" $errorCountAfter
Write-Host "Recovered file:" $OutputCsv
Write-Host "Corrections file:" $CorrectionsCsv
