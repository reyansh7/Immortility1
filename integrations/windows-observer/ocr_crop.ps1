# Local OCR of a small crop around one point (M2/P4 fallback). Windows.Media.Ocr only.
# The crop stays in memory (no file, no network) and is disposed before exit. The broker
# runs this only after the UIA worker found no text and did not refuse the target.
param([int]$X, [int]$Y, [int]$W = 420, [int]$H = 96)

# Windows PowerShell 5.1 writes pipes in the OEM code page; emit ASCII-only JSON (\uXXXX escapes).
function Protect-Ascii {
    process { [regex]::Replace($_, '[^\x00-\x7F]', { param($m) '\u{0:x4}' -f [int][char]$m.Value }) }
}
$ErrorActionPreference = 'Stop'
try {
    Add-Type -AssemblyName System.Drawing
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
    $null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]
    Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public static class ImmDpi { [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr v); }'
    [void][ImmDpi]::SetProcessDpiAwarenessContext([IntPtr](-4))
    $asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
    function Wait-Op($op, [Type]$type) {
        $task = $asTask.MakeGenericMethod($type).Invoke($null, @($op))
        if (-not $task.Wait(8000)) { throw 'ocr_timeout' }
        $task.Result
    }
    $W = [Math]::Min([Math]::Max($W, 64), 800); $H = [Math]::Min([Math]::Max($H, 24), 240)
    $left = [Math]::Max(0, $X - [int]($W / 2)); $top = [Math]::Max(0, $Y - [int]($H / 2))
    $started = [Diagnostics.Stopwatch]::StartNew()
    $bitmap = New-Object System.Drawing.Bitmap $W, $H
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen($left, $top, 0, 0, $bitmap.Size)
    $graphics.Dispose()
    $memory = New-Object System.IO.MemoryStream
    $bitmap.Save($memory, [System.Drawing.Imaging.ImageFormat]::Png)
    $bitmap.Dispose()
    $memory.Position = 0
    $stream = [System.IO.WindowsRuntimeStreamExtensions]::AsRandomAccessStream($memory)
    $decoder = Wait-Op ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $soft = Wait-Op ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    if ($null -eq $engine) { throw 'ocr_language_unavailable' }
    $result = Wait-Op ($engine.RecognizeAsync($soft)) ([Windows.Media.Ocr.OcrResult])
    $lines = @()
    foreach ($line in $result.Lines) {
        $words = @()
        foreach ($word in $line.Words) {
            $r = $word.BoundingRect
            $words += @{ t = $word.Text; x = [int]($left + $r.X); y = [int]($top + $r.Y); w = [int]$r.Width; h = [int]$r.Height }
        }
        $lines += @{ text = $line.Text; words = $words }
    }
    $soft.Dispose(); $memory.Dispose()
    @{ ok = $true; language = $engine.RecognizerLanguage.LanguageTag; crop = @{ x = $left; y = $top; w = $W; h = $H }; lines = $lines; elapsed_ms = $started.ElapsedMilliseconds } | ConvertTo-Json -Compress -Depth 6 | Protect-Ascii
} catch {
    @{ ok = $false; error = ($_.Exception.Message -replace '[\r\n]+', ' ').Substring(0, [Math]::Min(120, ($_.Exception.Message).Length)) } | ConvertTo-Json -Compress | Protect-Ascii
}
