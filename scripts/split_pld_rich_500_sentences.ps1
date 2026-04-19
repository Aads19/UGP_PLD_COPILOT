param(
    [string]$InputPath = "C:\UGP - SHIKHA MISRA\New folder\UGP DATABASE\PLD RICH DATABASE 500\PLD RICH DATABASE 500.csv",
    [string]$OutputPath = "C:\UGP - SHIKHA MISRA\New folder\UGP DATABASE\PLD RICH DATABASE 500\PLD 500 SENTENCE SPLIT DATABASE.csv"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Normalize-Text {
    param([AllowNull()][string]$Text)

    if ($null -eq $Text) {
        return ""
    }

    $Text = [regex]::Replace($Text, "[\r\n\t]+", " ")
    $Text = [regex]::Replace($Text, "\s{2,}", " ")
    return $Text.Trim()
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

function Protect-ScientificText {
    param([Parameter(Mandatory = $true)][string]$Text)

    $protected = [ordered]@{}

    function Add-Protected {
        param([Parameter(Mandatory = $true)][string]$Value)
        $key = "__PROTECTED_$($protected.Count)__"
        $protected[$key] = $Value
        return $key
    }

    $abbreviations = @(
        "Fig.", "Figs.", "Eq.", "Eqs.", "Ref.", "Refs.",
        "Dr.", "Prof.", "et al.", "i.e.", "e.g.", "vs."
    )

    foreach ($abbr in $abbreviations) {
        if ($Text.Contains($abbr)) {
            $key = Add-Protected $abbr
            $Text = $Text.Replace($abbr, $key)
        }
    }

    # Protect DOI and URLs before protecting decimal points.
    $Text = [regex]::Replace($Text, "https?://\S+", { param($m) Add-Protected $m.Value })
    $Text = [regex]::Replace($Text, "\b10\.\d{4,9}/\S+", { param($m) Add-Protected $m.Value })

    # Protect decimal points in values and formulae, e.g. 0.12 or La0.7Sr0.3MnO3.
    $Text = [regex]::Replace($Text, "(?<=\d)\.(?=\d)", { param($m) Add-Protected $m.Value })

    return [pscustomobject]@{
        Text = $Text
        Protected = $protected
    }
}

function Restore-ScientificText {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)]$Protected
    )

    $changed = $true
    while ($changed) {
        $changed = $false
        foreach ($key in $Protected.Keys) {
            if ($Text.Contains($key)) {
                $Text = $Text.Replace($key, $Protected[$key])
                $changed = $true
            }
        }
    }

    return $Text
}

function Split-IntoSentences {
    param([AllowNull()][string]$Text)

    $Text = Normalize-Text $Text
    if ([string]::IsNullOrWhiteSpace($Text)) {
        return @()
    }

    $protectedResult = Protect-ScientificText $Text
    $protectedText = $protectedResult.Text
    $protected = $protectedResult.Protected

    # Split on terminal punctuation followed by whitespace and a likely next sentence.
    $parts = [regex]::Split($protectedText, "(?<=[.!?])\s+(?=[A-Z0-9`"'\(\[])")

    $sentences = New-Object System.Collections.Generic.List[string]
    foreach ($part in $parts) {
        $sentence = Restore-ScientificText $part $protected
        $sentence = Normalize-Text $sentence
        if (-not [string]::IsNullOrWhiteSpace($sentence)) {
            [void]$sentences.Add($sentence)
        }
    }

    return $sentences.ToArray()
}

$rows = Import-Csv -LiteralPath $InputPath
$writer = [System.IO.StreamWriter]::new($OutputPath, $false, [System.Text.UTF8Encoding]::new($true))
$totalSentences = 0

try {
    Write-CsvRow $writer @("doi", "title", "abstract", "sentence")

    foreach ($row in $rows) {
        $doi = Normalize-Text $row.doi
        $title = Normalize-Text $row.title
        $abstract = Normalize-Text $row.abstract
        $sentences = Split-IntoSentences $row.paragraph

        foreach ($sentence in $sentences) {
            Write-CsvRow $writer @($doi, $title, $abstract, $sentence)
            $totalSentences++
        }
    }
}
finally {
    $writer.Close()
}

Write-Output "input_paragraph_rows=$($rows.Count)"
Write-Output "output_sentences=$totalSentences"
Write-Output "output_file=$OutputPath"
