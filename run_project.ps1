param(
    [Parameter(Mandatory = $false)]
    [string[]]$InputFiles = @("data/raw/bts_2024_01.zip")
)

$ErrorActionPreference = "Stop"
python src/analyze.py @InputFiles --output-dir data/processed
python -m unittest discover -s tests -v
node tools/build_workbook.mjs

Write-Output "Project outputs refreshed."

