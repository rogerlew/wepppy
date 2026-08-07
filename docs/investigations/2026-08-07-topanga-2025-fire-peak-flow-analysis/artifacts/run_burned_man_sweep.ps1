$ErrorActionPreference = "Stop"

$root = "C:\tmp\topanga-h106-20260807"
$sweepRoot = Join-Path $root "burned-man-sweep"
$exe = "C:\WEPP\wepp\wepp_2024.exe"
$baseManagement = Get-Content -Raw (Join-Path $root "p106-burned.man")
$results = @()

# Each bit replaces one burned-management record with its undisturbed value.
$replacements = @(
    @("0.42000 1.00000", "0.42000 2.00000"),
    @("1.00000 0.20000 0.33000", "1.00000 0.50000 0.33000"),
    @("-40.00000 2.00000 0.00000", "-40.00000 5.00000 0.00000"),
    @("1.50000 0.27000 330 1000 0.00000 0.55000", "1.50000 0.70000 330 1000 0.00000 0.90000"),
    @("400.00000 0.06000 0.55000 0.06000 2.00000", "400.00000 0.06000 0.90000 0.06000 2.00000")
)

New-Item -ItemType Directory -Force -Path $sweepRoot | Out-Null

for ($mask = 0; $mask -lt 32; $mask++) {
    $name = "m{0:D2}" -f $mask
    $lane = Join-Path $sweepRoot $name
    $runs = Join-Path $lane "runs"
    $output = Join-Path $lane "output"
    New-Item -ItemType Directory -Force -Path $runs, $output | Out-Null

    $management = $baseManagement
    for ($bit = 0; $bit -lt $replacements.Count; $bit++) {
        if (($mask -band (1 -shl $bit)) -ne 0) {
            $management = $management.Replace($replacements[$bit][0], $replacements[$bit][1])
        }
    }

    Set-Content -NoNewline -Encoding ascii -Path (Join-Path $runs "p106.man") -Value $management
    foreach ($file in @("p106.cli", "p106.run", "p106.slp")) {
        Copy-Item -Force (Join-Path $root $file) (Join-Path $runs $file)
    }
    Copy-Item -Force (Join-Path $root "p106-burned-ar10-7778.sol") (Join-Path $runs "p106.sol")

    $process = Start-Process -FilePath $exe -WorkingDirectory $runs `
        -RedirectStandardInput (Join-Path $runs "p106.run") `
        -RedirectStandardOutput (Join-Path $runs "stdout.txt") `
        -RedirectStandardError (Join-Path $runs "stderr.txt") `
        -Wait -PassThru

    $wat = Get-Content (Join-Path $output "H106.wat.dat")
    $ep = 0.0
    $es = 0.0
    $er = 0.0
    $lat = 0.0
    $maxLat = 0.0
    foreach ($line in $wat) {
        if ($line -notmatch '^\s+1\s+\d+\s+\d{4}\s+') { continue }
        $fields = $line.Trim() -split '\s+'
        $ep += [double]$fields[6]
        $es += [double]$fields[7]
        $er += [double]$fields[8]
        $dailyLat = [double]$fields[12]
        $lat += $dailyLat
        if ($dailyLat -gt $maxLat) { $maxLat = $dailyLat }
    }

    $loss = Get-Content (Join-Path $output "H106.loss.dat")
    $precipLine = $loss | Where-Object { $_ -match 'Mean annual precipitation' }
    $runoffLine = $loss | Where-Object { $_ -match 'Mean annual runoff from rainfall' }
    $precip = [double]([regex]::Match($precipLine, '([0-9.]+)\s+mm').Groups[1].Value)
    $runoff = [double]([regex]::Match($runoffLine, '([0-9.]+)\s+mm').Groups[1].Value)

    $results += [pscustomobject]@{
        Lane = $name
        Mask = $mask
        NonFragileResidue = [bool]($mask -band 1)
        RootDepth = [bool]($mask -band 2)
        MaxLAI = [bool]($mask -band 4)
        InitialCanopyInterrill = [bool]($mask -band 8)
        InitialRillCover = [bool]($mask -band 16)
        ExitCode = $process.ExitCode
        PrecipitationMm = [math]::Round($precip, 2)
        RunoffMm = [math]::Round($runoff, 2)
        ETMm = [math]::Round(($ep + $es + $er) / 45.0, 2)
        LateralFlowMm = [math]::Round($lat / 45.0, 2)
        MaximumDailyLateralFlowMm = [math]::Round($maxLat, 2)
    }
}

$results | Export-Csv -NoTypeInformation (Join-Path $sweepRoot "summary.csv")
$results | Sort-Object { [math]::Abs($_.ETMm - 346.0) }, { [math]::Abs($_.RunoffMm - 246.0) } |
    Format-Table -AutoSize
