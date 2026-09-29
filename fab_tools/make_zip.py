import sys, zipfile
from pathlib import Path

data = Path(sys.argv[1])          # DATA 폴더
out = sys.argv[2]                 # 만들 zip 이름
dates = sys.argv[3:]              # 날짜들 (예: 20260911 20260912 ...)

files = [f for f in sorted(data.iterdir())
         if f.suffix.lower() == ".csv" and any(d in f.name for d in dates)]
if not files:
    sys.exit("해당 날짜 파일이 없습니다. 파일명/날짜 형식을 확인하세요.")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for f in files:
        z.write(f, f.name)
        print("추가:", f.name)
