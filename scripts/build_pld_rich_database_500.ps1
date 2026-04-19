param(
    [string]$DatabaseDir = "C:\UGP - SHIKHA MISRA\New folder\UGP DATABASE",
    [string]$OutputDir = "C:\UGP - SHIKHA MISRA\New folder\UGP DATABASE\PLD RICH DATABASE 500",
    [int]$TargetPaperCount = 500
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName Microsoft.VisualBasic

$pldPattern = "(?i)\bPLD\b|pulsed\s+laser\s+deposition|pulsed-laser\s+deposition"
$pvdPattern = "(?i)\bPVD\b|physical\s+vapou?r\s+deposition"
$thinFilmPattern = "(?i)thin[- ]film|thin\s+films?|thin\s+film\s+growth|thin\s+film\s+deposition|film\s+growth|epitaxial\s+film|epitaxial\s+films|multilayer\s+film|coating|coatings"
$aldPattern = "(?i)\bALD\b|atomic\s+layer\s+deposition|atomic-layer\s+deposition|\bPEALD\b|plasma[- ]enhanced\s+atomic\s+layer\s+deposition"

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

$scorePatterns = @(
    @{Name="pld_title"; Weight=300; Pattern=$pldPattern; Scope="title"},
    @{Name="pld_abstract"; Weight=180; Pattern=$pldPattern; Scope="abstract"},
    @{Name="pvd_title"; Weight=160; Pattern=$pvdPattern; Scope="title"},
    @{Name="pvd_abstract"; Weight=90; Pattern=$pvdPattern; Scope="abstract"},
    @{Name="thin_film_title"; Weight=50; Pattern=$thinFilmPattern; Scope="title"},
    @{Name="thin_film_abstract"; Weight=25; Pattern=$thinFilmPattern; Scope="abstract"},
    @{Name="pulsed_laser_deposition_full"; Weight=45; Pattern="(?i)pulsed\s+laser\s+deposition|pulsed-laser\s+deposition"; Scope="full"},
    @{Name="pld_abbrev_full"; Weight=12; Pattern="(?i)\bPLD\b"; Scope="full"},
    @{Name="physical_vapor_deposition_full"; Weight=20; Pattern=$pvdPattern; Scope="full"},
    @{Name="laser_ablation"; Weight=18; Pattern="(?i)laser\s+ablation|ablation\s+plume|ablated"; Scope="full"},
    @{Name="plume"; Weight=22; Pattern="(?i)plasma\s+plume|plume\s+dynamics|plume\s+expansion|plume\s+propagation|laser[- ]induced\s+plume"; Scope="full"},
    @{Name="laser_fluence"; Weight=22; Pattern="(?i)laser\s+fluence|fluence|energy\s+density"; Scope="full"},
    @{Name="laser_parameters"; Weight=15; Pattern="(?i)laser\s+(energy|power|wavelength)|repetition\s+rate|pulse\s+(duration|frequency)|KrF|ArF|Nd:YAG|excimer"; Scope="full"},
    @{Name="oxygen_pressure"; Weight=22; Pattern="(?i)oxygen\s+(partial\s+)?pressure|oxygen\s+vacanc|background\s+gas|ambient\s+oxygen|O2\s+pressure"; Scope="full"},
    @{Name="substrate_temperature"; Weight=20; Pattern="(?i)substrate\s+temperature|growth\s+temperature|deposition\s+temperature|anneal"; Scope="full"},
    @{Name="target_substrate"; Weight=16; Pattern="(?i)target[- ]to[- ]substrate|target\s+substrate|target\s+distance|substrate\s+distance"; Scope="full"},
    @{Name="vacuum"; Weight=10; Pattern="(?i)base\s+pressure|vacuum|Torr|mbar|chamber\s+pressure"; Scope="full"},
    @{Name="droplets_particles"; Weight=16; Pattern="(?i)droplet|particulate|splashing|particles?"; Scope="full"},
    @{Name="thickness_uniformity"; Weight=14; Pattern="(?i)film\s+thickness|thickness\s+uniformity|non[- ]uniform|homogeneity|uniformity|growth\s+rate"; Scope="full"},
    @{Name="epitaxy_lattice"; Weight=20; Pattern="(?i)epitax|lattice\s+mismatch|strain|buffer\s+layer|single[- ]crystal|crystalline\s+quality"; Scope="full"},
    @{Name="crystallinity_amorphous"; Weight=18; Pattern="(?i)crystallinity|crystalline|amorphous|grain|phase|phase\s+segregation"; Scope="full"},
    @{Name="defects_resistivity"; Weight=14; Pattern="(?i)defect|oxygen\s+vacanc|resistivity|carrier\s+concentration|mobility|conductivity"; Scope="full"},
    @{Name="ZnO"; Weight=22; Pattern="(?i)\bZnO\b|zinc\s+oxide"; Scope="full"},
    @{Name="TiO2"; Weight=16; Pattern="(?i)\bTiO2\b|titanium\s+dioxide|titania"; Scope="full"},
    @{Name="complex_oxides"; Weight=14; Pattern="(?i)complex\s+oxide|perovskite|ferroelectric|manganite|ferrite|titanate|zirconate|GaN|SrTiO3"; Scope="full"},
    @{Name="characterization"; Weight=14; Pattern="(?i)\bXRD\b|x-ray\s+diffraction|AFM|atomic\s+force\s+microscop|SEM|TEM|XPS|Raman|photoluminescence|ellipsometry|profilometry|rocking\s+curve|roughness"; Scope="full"}
)

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

    return (($Value -replace "\r\n", " ") -replace "[\r\n\t]+", " ") -replace "\s{2,}", " "
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

function Get-ScopeText {
    param(
        [Parameter(Mandatory = $true)][string]$Scope,
        [Parameter(Mandatory = $true)][string]$Title,
        [Parameter(Mandatory = $true)][string]$Abstract,
        [Parameter(Mandatory = $true)][string]$Full
    )

    switch ($Scope) {
        "title" { return $Title }
        "abstract" { return $Abstract }
        default { return $Full }
    }
}

function Get-ArticleScore {
    param(
        [Parameter(Mandatory = $true)][string]$Title,
        [Parameter(Mandatory = $true)][string]$Abstract,
        [Parameter(Mandatory = $true)][string]$Full
    )

    $score = 0
    $reasons = New-Object System.Collections.Generic.List[string]

    foreach ($item in $script:scorePatterns) {
        $text = Get-ScopeText -Scope $item.Scope -Title $Title -Abstract $Abstract -Full $Full
        $matches = [regex]::Matches($text, $item.Pattern)
        if ($matches.Count -gt 0) {
            $boundedCount = [Math]::Min($matches.Count, 5)
            $score += ($item.Weight * $boundedCount)
            [void]$reasons.Add(("{0}x{1}" -f $item.Name, $matches.Count))
        }
    }

    return [pscustomobject]@{
        Score = $score
        Reasons = ($reasons -join ";")
    }
}

function Add-CandidateArticle {
    param(
        [Parameter(Mandatory = $true)][hashtable]$Articles,
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Doi,
        [Parameter(Mandatory = $true)][string]$Title,
        [Parameter(Mandatory = $true)][string]$Abstract,
        [Parameter(Mandatory = $true)][System.Text.StringBuilder]$SentenceText
    )

    if ([string]::IsNullOrWhiteSpace($Doi)) {
        return
    }

    $normalizedDoi = $Doi.Trim()
    if ($Articles.ContainsKey($normalizedDoi)) {
        return
    }

    $titleAbstract = "$Title $Abstract"
    if ($titleAbstract -match $script:aldPattern) {
        return
    }

    $hasPLD = $titleAbstract -match $script:pldPattern
    $hasPVD = $titleAbstract -match $script:pvdPattern
    $hasThinFilm = $titleAbstract -match $script:thinFilmPattern
    if (-not ($hasPLD -or $hasPVD -or $hasThinFilm)) {
        return
    }

    $full = "$Title $Abstract $($SentenceText.ToString())"
    $scored = Get-ArticleScore -Title $Title -Abstract $Abstract -Full $full

    $selectionTier = if ($hasPLD) {
        0
    }
    elseif ($hasPVD) {
        1
    }
    else {
        2
    }

    $Articles[$normalizedDoi] = [pscustomobject]@{
        Source = $Source
        Doi = $normalizedDoi
        Title = (Normalize-FlatText $Title.Trim())
        Abstract = (Normalize-FlatText $Abstract.Trim())
        Score = $scored.Score
        ScoreReasons = $scored.Reasons
        HasPLD = [bool]$hasPLD
        HasPVD = [bool]$hasPVD
        HasThinFilm = [bool]$hasThinFilm
        SelectionTier = $selectionTier
    }
}

function Read-CandidateArticles {
    param([Parameter(Mandatory = $true)][hashtable]$Articles)

    foreach ($source in $script:sources) {
        Write-Host "Scanning sentence file: $($source.Name)"
        $parser = New-CsvParser $source.SentencePath
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
                Add-CandidateArticle -Articles $Articles -Source $source.Name -Doi $currentDoi -Title $currentTitle -Abstract $currentAbstract -SentenceText $sentenceText
                $sentenceText = New-Object System.Text.StringBuilder
            }

            if ($doi -ne $currentDoi) {
                $currentDoi = $doi
                $currentTitle = $fields[1]
                $currentAbstract = $fields[2]
            }

            [void]$sentenceText.Append($fields[3]).Append(" ")
        }

        Add-CandidateArticle -Articles $Articles -Source $source.Name -Doi $currentDoi -Title $currentTitle -Abstract $currentAbstract -SentenceText $sentenceText
        $parser.Close()
    }
}

function Write-Manifest {
    param(
        [Parameter(Mandatory = $true)][object[]]$SelectedArticles,
        [Parameter(Mandatory = $true)][string]$OutputPath
    )

    $writer = [System.IO.StreamWriter]::new($OutputPath, $false, [System.Text.UTF8Encoding]::new($true))
    try {
        Write-CsvRow $writer @("rank", "source", "doi", "selection_tier", "score", "has_pld", "has_pvd", "has_thin_film", "title", "abstract", "score_reasons")
        $rank = 0
        foreach ($article in $SelectedArticles) {
            $rank++
            Write-CsvRow $writer @(
                ([string]$rank),
                $article.Source,
                $article.Doi,
                ([string]$article.SelectionTier),
                ([string]$article.Score),
                ([string]$article.HasPLD),
                ([string]$article.HasPVD),
                ([string]$article.HasThinFilm),
                $article.Title,
                $article.Abstract,
                $article.ScoreReasons
            )
        }
    }
    finally {
        $writer.Close()
    }
}

function Write-FlatParagraphs {
    param(
        [Parameter(Mandatory = $true)][object[]]$SelectedArticles,
        [Parameter(Mandatory = $true)][string]$OutputDir
    )

    $selectedByDoi = @{}
    foreach ($article in $SelectedArticles) {
        $selectedByDoi[$article.Doi] = $article
    }

    $combinedPath = Join-Path $OutputDir "PLD RICH DATABASE 500.csv"
    $combinedWriter = [System.IO.StreamWriter]::new($combinedPath, $false, [System.Text.UTF8Encoding]::new($true))
    $header = @("source", "doi", "selection_tier", "score", "has_pld", "has_pvd", "has_thin_film", "title", "abstract", "paragraph_index", "paragraph")

    try {
        Write-CsvRow $combinedWriter $header
        $stats = New-Object System.Collections.Generic.List[object]

        foreach ($source in $script:sources) {
            $sourcePath = Join-Path $OutputDir ("{0}_PLD_RICH_DATABASE_500.csv" -f $source.Name)
            $writer = [System.IO.StreamWriter]::new($sourcePath, $false, [System.Text.UTF8Encoding]::new($true))
            $parser = New-CsvParser $source.ParagraphPath
            [void]$parser.ReadFields()

            $seenDois = [System.Collections.Generic.HashSet[string]]::new()
            $rowsWritten = 0

            try {
                Write-CsvRow $writer $header
                $currentDoi = $null
                $currentArticle = $null
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
                        $keepCurrentArticle = $selectedByDoi.ContainsKey($currentDoi)
                        $currentArticle = if ($keepCurrentArticle) { $selectedByDoi[$currentDoi] } else { $null }
                        $paragraphIndex = 0
                        if ($keepCurrentArticle) {
                            [void]$seenDois.Add($currentDoi)
                        }
                    }

                    if ($keepCurrentArticle) {
                        $paragraphIndex++
                        $flatRow = @(
                            $source.Name,
                            $currentArticle.Doi,
                            ([string]$currentArticle.SelectionTier),
                            ([string]$currentArticle.Score),
                            ([string]$currentArticle.HasPLD),
                            ([string]$currentArticle.HasPVD),
                            ([string]$currentArticle.HasThinFilm),
                            $currentArticle.Title,
                            $currentArticle.Abstract,
                            ([string]$paragraphIndex),
                            (Normalize-FlatText $fields[3])
                        )
                        Write-CsvRow $writer $flatRow
                        Write-CsvRow $combinedWriter $flatRow
                        $rowsWritten++
                    }
                }
            }
            finally {
                $writer.Close()
                $parser.Close()
            }

            [void]$stats.Add([pscustomobject]@{
                Source = $source.Name
                PapersWritten = $seenDois.Count
                RowsWritten = $rowsWritten
                OutputPath = $sourcePath
            })
        }
    }
    finally {
        $combinedWriter.Close()
    }

    return [pscustomobject]@{
        CombinedPath = $combinedPath
        Stats = $stats
    }
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$candidateArticles = @{}
Read-CandidateArticles -Articles $candidateArticles

if ($candidateArticles.Count -lt $TargetPaperCount) {
    throw "Only found $($candidateArticles.Count) eligible candidates, but TargetPaperCount=$TargetPaperCount."
}

$selected = @(
    $candidateArticles.Values |
        Sort-Object @{Expression = "SelectionTier"; Ascending = $true}, @{Expression = "Score"; Descending = $true}, Source, Doi |
        Select-Object -First $TargetPaperCount
)

$manifestPath = Join-Path $OutputDir "PLD RICH DATABASE 500 manifest.csv"
Write-Manifest -SelectedArticles $selected -OutputPath $manifestPath
$paragraphResult = Write-FlatParagraphs -SelectedArticles $selected -OutputDir $OutputDir

Write-Host ""
Write-Host "Done."
Write-Host "Eligible non-ALD PLD/PVD/thin-film candidates: $($candidateArticles.Count)"
Write-Host "Final selected papers: $($selected.Count)"
Write-Host "Selected PLD papers: $( @($selected | Where-Object { $_.HasPLD }).Count )"
Write-Host "Selected PVD papers: $( @($selected | Where-Object { $_.HasPVD }).Count )"
Write-Host "Selected thin-film papers: $( @($selected | Where-Object { $_.HasThinFilm }).Count )"
Write-Host "Manifest: $manifestPath"
Write-Host "Combined flat database: $($paragraphResult.CombinedPath)"
Write-Host ""
Write-Host "Per-source outputs:"
$paragraphResult.Stats | Format-Table Source, PapersWritten, RowsWritten, OutputPath -AutoSize
