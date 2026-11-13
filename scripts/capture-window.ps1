param(
    [Parameter(Mandatory = $true)][string]$Out,
    [string]$Process = "immortility-desktop",
    [string]$Title = "Immortility"
)
# Diagnostic: captures the app's own window with PrintWindow, without focusing or moving it.
Add-Type -ReferencedAssemblies System.Drawing @"
using System; using System.Drawing; using System.Drawing.Imaging; using System.Runtime.InteropServices; using System.Text;
public static class Capture {
  delegate bool Enum(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumWindows(Enum e, IntPtr l);
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
  [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out R r);
  [DllImport("user32.dll")] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern bool PrintWindow(IntPtr h, IntPtr dc, uint flags);
  [DllImport("user32.dll")] static extern bool SetProcessDPIAware();
  struct R { public int L, T, Rt, B; }
  public static string Save(uint pid, string title, string path) {
    SetProcessDPIAware();
    IntPtr target = IntPtr.Zero;
    EnumWindows((h, l) => {
      uint owner; GetWindowThreadProcessId(h, out owner);
      var s = new StringBuilder(200); GetWindowText(h, s, 200);
      if (owner == pid && s.ToString() == title) { target = h; return false; }
      return true;
    }, IntPtr.Zero);
    if (target == IntPtr.Zero) return "window not found";
    R r; GetWindowRect(target, out r);
    int w = r.Rt - r.L, ht = r.B - r.T;
    using (var bmp = new Bitmap(w, ht, PixelFormat.Format32bppArgb)) {
      using (var g = Graphics.FromImage(bmp)) {
        g.Clear(Color.FromArgb(255, 40, 44, 52));
        IntPtr dc = g.GetHdc();
        PrintWindow(target, dc, 2);
        g.ReleaseHdc(dc);
      }
      bmp.Save(path, ImageFormat.Png);
    }
    return string.Format("{0}x{1} at {2},{3}", w, ht, r.L, r.T);
  }
}
"@
$p = Get-Process $Process -ErrorAction Stop | Select-Object -First 1
[Capture]::Save([uint32]$p.Id, $Title, (Join-Path (Get-Location) $Out))
