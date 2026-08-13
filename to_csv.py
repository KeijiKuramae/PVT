"""
PVT-B のバックアップ JSON を解析用の CSV に変換する。

使い方:
    python to_csv.py                  # 記録/ の中で最新のバックアップを使う
    python to_csv.py 記録/pvt-backup-20260901.json

出力は 記録/csv/ に trials.csv, sessions.csv, events.csv。

注意:
  日次ファイル pvt-YYYYMMDD.json は復旧と欠測確認のためのもので、
  解析には使わない（バックアップと重複するため二重計上になる）。
  ここが読むのは pvt-backup-*.json のみ。
"""

import csv
import json
import sys
from pathlib import Path

BASE = Path(__file__).parent
REC = BASE / "記録"
OUT = REC / "csv"

COLS = {
    "trials": ["session_id", "trial", "isi_ms", "isi_actual_ms",
               "rt_ms", "false_start", "stim_ts", "resp_ts"],
    "sessions": ["session_id", "started_at", "label", "tau_min",
                 "subjective_kss", "wake_time_self_report", "note"],
    "events": ["event_ts", "event_type", "value"],
}


def latest_backup() -> Path:
    files = sorted(REC.glob("pvt-backup-*.json"))
    if not files:
        sys.exit(f"バックアップが見つかりません: {REC}/pvt-backup-*.json")
    return files[-1]


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else latest_backup()
    data = json.loads(src.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)

    for table, cols in COLS.items():
        rows = data.get(table, [])
        path = OUT / f"{table}.csv"
        # utf-8-sig: Excel で開いても文字化けしない
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow({c: r.get(c, "") for c in cols})
        print(f"{path}  {len(rows)} 行")

    summarize(data)


def summarize(data: dict) -> None:
    """取りこぼしに早く気づくための最小限の確認."""
    sessions = data.get("sessions", [])
    if not sessions:
        return

    # 計測日ごとのセッション数（午前4時を日付の境界にする＝アプリ側と同じ規則）
    from collections import Counter
    from datetime import datetime, timedelta

    def study_day(ts: str) -> str:
        d = datetime.fromisoformat(ts)
        if d.hour < 4:
            d -= timedelta(days=1)
        return d.strftime("%Y-%m-%d")

    per_day = Counter(study_day(s["started_at"]) for s in sessions)
    labels = Counter(s["label"] for s in sessions)

    print(f"\n計測日数 {len(per_day)} 日 / セッション {len(sessions)} / "
          f"試行 {len(data.get('trials', []))}")

    print("\nラベル別:")
    for k, v in sorted(labels.items()):
        print(f"  {k:<14} {v}")

    thin = [d for d, n in sorted(per_day.items()) if n < 4]
    if thin:
        print(f"\nセッションが4回未満の日（{len(thin)}日）:")
        for d in thin:
            print(f"  {d}  {per_day[d]}回")

    if labels.get("off_schedule"):
        print(f"\noff_schedule が {labels['off_schedule']} 件あります。"
              " tau_min で扱えるので捨てないこと。")


if __name__ == "__main__":
    main()
