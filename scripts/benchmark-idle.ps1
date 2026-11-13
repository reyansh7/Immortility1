param(
  [Parameter(Mandatory=$true)][int]$AppPid,
  [ValidateRange(10,86400)][int]$DurationSeconds=600,
  [ValidateRange(0,300)][int]$WarmupSeconds=30,
  [string]$Output='data/benchmarks/idle.json'
)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$target=Get-Process -Id $AppPid
if ($target.Path -ne (Join-Path $root 'apps/desktop/src-tauri/target/debug/immortility-desktop.exe')) {throw 'Target is not this project desktop'}
$path=[IO.Path]::GetFullPath((Join-Path $root $Output))
if (!$path.StartsWith($root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {throw 'Report must remain inside the workspace'}
New-Item -ItemType Directory -Force (Split-Path $path -Parent) | Out-Null
$clock=[Diagnostics.Stopwatch]::StartNew()
$previous=[Collections.Generic.Dictionary[int,double]]::new()
$samples=[Collections.Generic.List[object]]::new()
$last=0.0
$complete=$false
$failure=$null
try {
  while($clock.Elapsed.TotalSeconds -lt ($DurationSeconds+$WarmupSeconds)) {
    if(!(Get-Process -Id $AppPid -ErrorAction SilentlyContinue)){throw 'App exited; benchmark incomplete'}
    $all=Get-CimInstance Win32_Process
    $ids=[Collections.Generic.HashSet[int]]::new()
    [void]$ids.Add($AppPid)
    for($depth=0;$depth -lt 8;$depth++){
      foreach($entry in $all){if($ids.Contains([int]$entry.ParentProcessId)){[void]$ids.Add([int]$entry.ProcessId)}}
    }
    $elapsed=$clock.Elapsed.TotalSeconds
    $uiCpu=0.0; $brokerCpu=0.0; $cumulative=0.0
    $working=0L; $private=0L; $broker=0L; $total=0L
    foreach($entry in $all){
      $processId=[int]$entry.ProcessId
      if (!$ids.Contains($processId)) {continue}
      $process=Get-Process -Id $processId -ErrorAction SilentlyContinue
      if ($null -eq $process) {continue}
      if ($null -eq $entry.KernelModeTime -or $null -eq $entry.UserModeTime) {throw 'CPU timing unavailable; refusing to report zero'}
      $seconds=([double]$entry.KernelModeTime+[double]$entry.UserModeTime)/10000000
      $delta=0.0
      if($previous.ContainsKey($processId)){$delta=[Math]::Max(0,($seconds-$previous[$processId]))}
      $previous[$processId]=$seconds
      $total+=$process.WorkingSet64
      if($process.ProcessName -eq 'python'){
        $broker+=$process.WorkingSet64; $brokerCpu+=$delta
      } else {
        $working+=$process.WorkingSet64; $private+=$process.PrivateMemorySize64
        $uiCpu+=$delta; $cumulative+=$seconds
      }
    }
    $gpu=$null
    try {
      $engines=(Get-Counter '\GPU Engine(*)\Utilization Percentage' -ErrorAction Stop).CounterSamples
      $matching=@($engines | Where-Object {$_.InstanceName -match 'pid_(\d+)_' -and $ids.Contains([int]$Matches[1])})
      if($matching.Count){$gpu=($matching | Measure-Object CookedValue -Sum).Sum}
    }catch{}
    if($last -gt 0 -and $elapsed -ge $WarmupSeconds){
      $factor=100/($elapsed-$last)/[Environment]::ProcessorCount
      $samples.Add([PSCustomObject]@{
        ElapsedSeconds=$elapsed-$WarmupSeconds; CpuPercent=$uiCpu*$factor
        BrokerCpuPercent=$brokerCpu*$factor; TotalCpuPercent=($uiCpu+$brokerCpu)*$factor
        UiCpuCumulativeSeconds=$cumulative; UiWorkingSetMB=$working/1MB
        UiPrivateMB=$private/1MB; BrokerWorkingSetMB=$broker/1MB
        TotalWorkingSetMB=$total/1MB; GpuEngineSumPercent=$gpu; ProcessCount=$ids.Count
      })
    }
    $last=$elapsed
    Start-Sleep -Seconds 5
  }
  $complete=$true
} catch {
  $failure=$_.Exception.Message
} finally {
  $gpuSamples=@($samples | Where-Object {$null -ne $_.GpuEngineSumPercent})
  $report=[PSCustomObject]@{
    SchemaVersion='1.1'; Completed=$complete; Failure=$failure; AppPid=$AppPid
    Condition='Compact native app idle; no capture/inference; other development work may run. CPU normalized by logical cores; GPU is sum of matching engine counters.'
    RequestedSeconds=$DurationSeconds; WarmupSeconds=$WarmupSeconds
    ElapsedSeconds=$clock.Elapsed.TotalSeconds; Samples=$samples.Count
    CpuAveragePercent=($samples|Measure-Object CpuPercent -Average).Average
    TotalCpuAveragePercent=($samples|Measure-Object TotalCpuPercent -Average).Average
    UiWorkingSetAverageMB=($samples|Measure-Object UiWorkingSetMB -Average).Average
    UiWorkingSetMaximumMB=($samples|Measure-Object UiWorkingSetMB -Maximum).Maximum
    UiPrivateAverageMB=($samples|Measure-Object UiPrivateMB -Average).Average
    BrokerWorkingSetAverageMB=($samples|Measure-Object BrokerWorkingSetMB -Average).Average
    TotalWorkingSetAverageMB=($samples|Measure-Object TotalWorkingSetMB -Average).Average
    GpuAvailable=($gpuSamples.Count -gt 0)
    GpuAverageEngineSumPercent=if($gpuSamples.Count){($gpuSamples|Measure-Object GpuEngineSumPercent -Average).Average}else{$null}
    Measurements=$samples
  }
  $report|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $path -Encoding utf8
}
if (!$complete) {throw $failure}
Write-Output ('Completed idle benchmark: '+$path)
