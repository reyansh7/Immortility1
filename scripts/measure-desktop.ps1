param([int]$Seconds = 5)
# Diagnostic: samples CPU and memory of the desktop shell, its WebView2 children and the broker,
# then prints NVIDIA GPU utilization if nvidia-smi is available.
$shell = Get-Process immortility-desktop -ErrorAction Stop | Select-Object -First 1
$all = Get-CimInstance Win32_Process
$ids = @($shell.Id)
$frontier = @($shell.Id)
while ($frontier.Count) {
    $children = @($all | Where-Object { $frontier -contains $_.ParentProcessId } | ForEach-Object { [int]$_.ProcessId })
    $ids += $children
    $frontier = $children
}
$before = @{}
foreach ($id in $ids) { $p = Get-Process -Id $id -ErrorAction SilentlyContinue; if ($p) { $before[$id] = $p.TotalProcessorTime.TotalMilliseconds } }
Start-Sleep -Seconds $Seconds
$cores = [Environment]::ProcessorCount
$rows = foreach ($id in $ids) {
    $p = Get-Process -Id $id -ErrorAction SilentlyContinue
    if (-not $p -or -not $before.ContainsKey($id)) { continue }
    [pscustomobject]@{
        Name = $p.ProcessName
        Id = $id
        CpuPercent = [math]::Round(($p.TotalProcessorTime.TotalMilliseconds - $before[$id]) / ($Seconds * 10 * $cores), 2)
        WorkingSetMB = [math]::Round($p.WorkingSet64 / 1MB, 1)
        PrivateMB = [math]::Round($p.PrivateMemorySize64 / 1MB, 1)
    }
}
$rows | Sort-Object CpuPercent -Descending | Format-Table -AutoSize
"Total CPU % of all cores: {0}" -f [math]::Round(($rows | Measure-Object CpuPercent -Sum).Sum, 2)
"Total working set MB: {0}" -f [math]::Round(($rows | Measure-Object WorkingSetMB -Sum).Sum, 1)
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total --format=csv,noheader
    nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader
}
