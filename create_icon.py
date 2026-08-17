"""生成插件图标"""
import struct, zlib

width, height = 16, 16
pixels = []
for y in range(height):
    row = b'\x00'
    for x in range(width):
        dx, dy = x - 7.5, y - 7.5
        if (dx*dx + dy*dy) ** 0.5 <= 6.5:
            row += b'\x10\xb9\x81\xff'
        else:
            row += b'\x00\x00\x00\x00'
    pixels.append(row)

raw = b''.join(pixels)

def chunk(ctype, data):
    c = ctype + data
    return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)

ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')

with open('extension/icon.png', 'wb') as f:
    f.write(png)
print('icon.png created')
