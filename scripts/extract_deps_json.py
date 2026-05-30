from pathlib import Path

p = Path(r"C:\xiangmuyunxing\biancheng\2026\bidking-lab\src\AuctionAnalyzer4.13.3\AuctionAnalyzer4.13.3.exe")
d = p.read_bytes()
idx = d.rfind(b"MapBidCalculator.deps.json")
print("deps name at", idx)
for back in range(100, 12000):
    pos = idx - back
    if d[pos : pos + 1] == b"{" and b'"libraries"' in d[pos:idx]:
        text = d[pos : idx + len("MapBidCalculator.deps.json")]
        s = text.decode("utf-8", errors="replace")
        print("found json at", pos, "len", len(s))
        print(s[:1200])
        out = Path(r"C:\xiangmuyunxing\biancheng\2026\bidking-lab\src\AuctionAnalyzer4.13.3\_extracted\MapBidCalculator.deps.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        # write only json part
        json_end = s.find("MapBidCalculator.deps.json")
        out.write_text(s[:json_end], encoding="utf-8")
        print("written to", out)
        break
