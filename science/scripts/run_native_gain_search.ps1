# Busca de ganho de vegetacao nativa (MapBiomas Col. 11) em regioes candidatas.
$env:PYTHONIOENCODING = 'utf-8'
$py = "$env:USERPROFILE\.venvs\geodet\Scripts\python.exe"
$s  = Join-Path $PSScriptRoot 'gee_find_native_gain.py'
$p  = 'geodetective-brasil'
& $py $s --project $p --label mata_atlantica_vale_paraiba --bbox -46.5 -23.6 -44.0 -22.3 --top 10 --exclude-fire
& $py $s --project $p --label amazonia_nordeste_para --bbox -48.5 -2.0 -46.0 -0.7 --top 10 --exclude-fire
& $py $s --project $p --label cerrado_go_df --bbox -49.5 -16.5 -47.0 -14.5 --top 10 --exclude-fire
& $py $s --project $p --label pantanal_mt --bbox -57.5 -17.8 -56.0 -16.5 --top 10
