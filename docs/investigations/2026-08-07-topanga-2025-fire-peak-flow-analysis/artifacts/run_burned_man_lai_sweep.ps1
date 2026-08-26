$ErrorActionPreference = "Stop"

$root = "C:\tmp\topanga-h106-20260807"
$sweepRoot = Join-Path $root "burned-man-lai-sweep"
$exe = "C:\WEPP\wepp\wepp_2024.exe"
$baseManagement = Get-Content -Raw (Join-Path $root "p106-burned.man")
$baseManagement = $baseManagement.Replace(
    "1.00000 0.20000 0.33000", "1.00000 0.50000 0.33000"
).Replace(
    "1.50000 0.27000 330 1000 0.00000 0.55000",
    "1.50000 0.70000 330 1000 0.00000 0.90000"
)
$results = @()

New-Item -ItemType Directory -Force -Path $sweepRoot | Out-Null

foreach ($maxLai in @(2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 4.0)) {
    $label = $maxLai.ToString("0.00", [Globalization.CultureInfo]::InvariantCulture)
    $name = "lai-" + $label.Replace(".", "p")
    $lane = Join-Path $sweepRoot $name
    $runs = Join-Path $lane "runs"
    $output = Join-Path $lane "output"
    New-Item -ItemType Directory -Force -Path $runs, $output | Out-Null

    $laiRecord = "-40.00000 {0} 0.00000" -f $label
    $management = $baseManagement.Replace("-40.00000 2.00000 0.00000", $laiRecord)
    Set-Content -NoNewline -Encoding ascii -Path (Join-Path $runs "p106.man") -Value $management

    foreach ($file in @("p106.cli", "p106.slp")) {
        Copy-Item -Force (Join-Path $root $file) (Join-Path $runs $file)
    }
    Copy-Item -Force (Join-Path $root "p106-burned-ar10-7778.sol") (Join-Path $runs "p106.sol")
    $runControl = Get-Content -Raw (Join-Path $root "p106.run")
    $runControl = [regex]::Replace($runControl, '(?m)^45\r?$', '40')
    Set-Content -NoNewline -Encoding ascii -Path (Join-Path $runs "p106.run") -Value $runControl

    $process = Start-Process -FilePath $exe -WorkingDirectory $runs `
        -RedirectStandardInput (Join-Path $runs "p106.run") `
        -RedirectStandardOutput (Join-Path $runs "stdout.txt") `
        -RedirectStandardError (Join-Path $runs "stderr.txt") `
        -Wait -PassThru

    $ep = 0.0
    $es = 0.0
    $er = 0.0
    $lat = 0.0
    $maxLat = 0.0
    foreach ($line in Get-Content (Join-Path $output "H106.wat.dat")) {
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
        MaximumLAI = $maxLai
        ExitCode = $process.ExitCode
        PrecipitationMm = [math]::Round($precip, 2)
        RunoffMm = [math]::Round($runoff, 2)
        ETMm = [math]::Round(($ep + $es + $er) / 40.0, 2)
        LateralFlowMm = [math]::Round($lat / 40.0, 2)
        MaximumDailyLateralFlowMm = [math]::Round($maxLat, 2)
    }
}

$results | Export-Csv -NoTypeInformation (Join-Path $sweepRoot "summary.csv")
$results | Sort-Object { [math]::Abs($_.ETMm - 346.0) + [math]::Abs($_.RunoffMm - 246.0) } |
    Format-Table -AutoSize
