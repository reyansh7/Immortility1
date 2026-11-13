param([string]$Process = "immortility-desktop")
# Diagnostic: prints the visible top-level windows of the desktop app with their physical bounds.
Add-Type @"
using System; using System.Collections.Generic; using System.Runtime.InteropServices; using System.Text;
public static class WindowRect {
  delegate bool Enum(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumWindows(Enum e, IntPtr l);
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
  [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out R r);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern bool IsZoomed(IntPtr h);
  [DllImport("user32.dll")] static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll")] static extern bool SetProcessDPIAware();
  struct R { public int L, T, Rt, B; }
  public static List<string> For(uint pid) {
    SetProcessDPIAware();
    var found = new List<string>();
    EnumWindows((h, l) => {
      uint owner; GetWindowThreadProcessId(h, out owner);
      if (owner == pid && IsWindowVisible(h)) {
        R r; GetWindowRect(h, out r); var s = new StringBuilder(200); GetWindowText(h, s, 200);
        found.Add(string.Format("{0} [{1},{2}] {3}x{4} maximized={5} minimized={6}", s, r.L, r.T,
          r.Rt - r.L, r.B - r.T, IsZoomed(h), IsIconic(h)));
      }
      return true;
    }, IntPtr.Zero);
    return found;
  }
}
"@
foreach ($p in Get-Process $Process -ErrorAction SilentlyContinue) { [WindowRect]::For([uint32]$p.Id) }
