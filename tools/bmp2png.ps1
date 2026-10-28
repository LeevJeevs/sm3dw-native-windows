param([string]$In,[string]$Out)
Add-Type -AssemblyName System.Drawing
$b=[System.Drawing.Bitmap]::FromFile((Resolve-Path $In)); $b.Save((Join-Path (Get-Location) $Out),[System.Drawing.Imaging.ImageFormat]::Png); $b.Dispose(); "ok $Out"
