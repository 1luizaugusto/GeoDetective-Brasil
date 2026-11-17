# Triagem das regiões candidatas aos três pares-piloto (perda, ganho, estabilidade).
$py = "$env:USERPROFILE\.venvs\geodet\Scripts\python.exe"
$s  = Join-Path $PSScriptRoot 'screen_region.py'
$o  = Join-Path $PSScriptRoot '..\..\data\screening'
& $py $s --name apui_am       --lon -59.89 --lat -7.20  --size 24000 --season 06-01 09-30 --out $o
& $py $s --name brumadinho_mg --lon -44.12 --lat -20.13 --size 16000 --season 05-01 08-31 --out $o
& $py $s --name tres_lagoas_ms --lon -52.05 --lat -20.75 --size 30000 --season 05-01 08-31 --out $o
& $py $s --name manaus_ducke  --lon -59.95 --lat -2.95  --size 16000 --season 07-01 10-31 --out $o
& $py $s --name rio_tijuca    --lon -43.28 --lat -22.95 --size 12000 --season 05-01 09-30 --out $o
