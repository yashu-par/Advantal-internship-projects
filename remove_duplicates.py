import hashlib
from pathlib import Path

root = Path(r"C:\Users\yasha\OneDrive\Desktop\yoga recognition")

def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

image_files = [f for f in root.rglob("*") 
               if f.suffix.lower() in {".jpg", ".jpeg", ".png"}]

hashes = {}
removed = 0
for fp in image_files:
    h = md5(fp)
    if h in hashes:
        fp.unlink()  # duplicate delete karo
        removed += 1
    else:
        hashes[h] = fp

print(f"Duplicates removed : {removed}")
print(f"Images remaining   : {len(hashes)}")