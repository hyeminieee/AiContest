"""FlyWire v783 원본 데이터 3개를 data/raw/에 내려받기 (팀원 누구나)

실행:  python src/download_data.py
이미 받은 파일(크기가 같은 파일)은 건너뜁니다. 합계 약 136MB.
"""
import argparse
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [  # (저장 경로, 주소, 크기(바이트), 설명)
    ("annotations/Supplemental_file1_neuron_annotations.tsv",
     "https://raw.githubusercontent.com/flyconnectome/flywire_annotations/main/supplemental_files/Supplemental_file1_neuron_annotations.tsv",
     31720298, "뉴런 이름표"),
    ("shiu/Connectivity_783.parquet",
     "https://github.com/philshiu/Drosophila_brain_model/raw/HEAD/Connectivity_783.parquet",
     100804642, "뉴런 사이 연결"),
    ("shiu/Completeness_783.csv",
     "https://github.com/philshiu/Drosophila_brain_model/raw/HEAD/Completeness_783.csv",
     3327347, "뉴런 ID 목록"),
]


def progress(name):
    last = [-1]

    def hook(blocks, block_size, total):
        if total > 0:
            pct = min(100, blocks * block_size * 100 // total)
            if pct // 10 != last[0]:
                last[0] = pct // 10
                sys.stdout.write(f"\r  {name}: {pct:3d}%")
                sys.stdout.flush()
    return hook


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default=str(ROOT / "data" / "raw"), help="저장 폴더 (기본: data/raw)")
    ap.add_argument("--only", help="이름에 이 글자가 들어간 파일만 받기 (시험용)")
    args = ap.parse_args()
    dest = Path(args.dest)
    for rel, url, size, desc in FILES:
        if args.only and args.only not in rel:
            continue
        path = dest / rel
        if path.exists() and path.stat().st_size == size:
            print(f"  {rel}: 이미 있음 (건너뜀)")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"{desc} 받는 중 ({size / 1e6:.0f}MB)")
        tmp = path.with_suffix(path.suffix + ".part")
        urllib.request.urlretrieve(url, tmp, progress(rel))
        print()
        if tmp.stat().st_size != size:
            tmp.unlink()
            sys.exit(f"  {rel}: 크기가 다릅니다. 원본이 바뀌었을 수 있으니 팀장에게 알려 주세요.")
        tmp.replace(path)
    print(f"완료: {dest}\n다음 단계: python src/extract_circuit.py")


if __name__ == "__main__":
    main()
