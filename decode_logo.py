import base64
import sys

b64 = sys.argv[1]

# Strip any whitespace
b64 = b64.strip().replace('\n', '').replace('\r', '').replace(' ', '')

# Fix padding
b64 += '=' * (-len(b64) % 4)

data = base64.b64decode(b64, validate=False)
with open('assets/logo.jpg', 'wb') as f:
    f.write(data)
print(f'Saved {len(data)} bytes')
