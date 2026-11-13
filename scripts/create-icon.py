"""Generate the small code-native orb icon. No external asset or license required."""
import math
import struct
from pathlib import Path

size = 32
pixels = bytearray()
for y in range(size - 1, -1, -1):
    for x in range(size):
        radius = math.hypot(x - 15.5, y - 15.5)
        light = max(0, 1 - math.hypot(x - 11, y - 9) / 28)
        pixels.extend((int(70 + light * 85), int(60 + light * 135), int(22 + light * 120), 255 if radius < 14.5 else 0))
bitmap = struct.pack('<IIIHHIIIIII',40,size,size*2,1,32,0,len(pixels),0,0,0,0)+pixels+bytes(size*size//8)
ico = struct.pack('<HHH',0,1,1)+struct.pack('<BBBBHHII',size,size,0,0,1,32,len(bitmap),22)+bitmap
target=Path(__file__).resolve().parents[1]/'apps/desktop/src-tauri/icons/icon.ico'
target.parent.mkdir(parents=True,exist_ok=True)
target.write_bytes(ico)
