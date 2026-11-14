"""Unpack an unencrypted Android .ab backup into a folder."""
import io
import sys
import tarfile
import zlib
from pathlib import Path


def extract(ab_path: Path, out_dir: Path) -> list[Path]:
    data = ab_path.read_bytes()
    lines = data.split(b"\n", 4)
    if lines[0] != b"ANDROID BACKUP":
        raise ValueError("not an Android backup file")
    compressed, encryption = lines[2], lines[3]
    if encryption != b"none":
        raise ValueError("backup is encrypted")
    body = lines[4]
    if compressed == b"1":
        body = zlib.decompress(body)
    out_dir.mkdir(parents=True, exist_ok=True)
    extracted = []
    with tarfile.open(fileobj=io.BytesIO(body)) as tar:
        for m in tar.getmembers():
            if m.isfile():
                target = (out_dir / m.name).resolve()
                if out_dir.resolve() not in target.parents:
                    continue  # path traversal guard
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(tar.extractfile(m).read())
                extracted.append(target)
    return extracted


if __name__ == "__main__":
    files = extract(Path(sys.argv[1]), Path(sys.argv[2]))
    for f in files:
        print(f.stat().st_size, f)
