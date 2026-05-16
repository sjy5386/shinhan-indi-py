"""포트폴리오 스냅샷 → JSON 덤프 entry point.

기본은 **로그인된 사용자의 모든 계좌**를 enumerate해 순회.
인증서 비번이 .env에 비어있으면 시세조회 전용 모드로 로그인.

사용:
    python dump_portfolio.py                    # 전체 계좌
    python dump_portfolio.py --no-quote         # 시세 보강 생략 (빠름)
    python dump_portfolio.py --dry-run          # 로그인 + 계좌 목록까지만
    python dump_portfolio.py --account 12345... # 특정 계좌만
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta

# Windows 콘솔(cp949)에서 한글 print가 깨지지 않도록.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from indi_session import IndiSession, load_creds  # noqa: E402
from indi_portfolio import (  # noqa: E402
    fetch_account_list,
    fetch_positions,
    fetch_account_summary,
    fetch_total_assets,
    fetch_total_assets_z622,
    fetch_saaa612qb_holdings,
    fetch_customer_num,
    enrich_positions_with_quote,
)


KST = timezone(timedelta(hours=9))


class _Tee:
    """stdout/stderr를 콘솔 + 파일에 동시 출력."""
    def __init__(self, *streams):
        self.streams = streams
    def write(self, s):
        for st in self.streams:
            st.write(s)
            st.flush()
    def flush(self):
        for st in self.streams:
            st.flush()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="로그인 + 계좌 목록까지만")
    p.add_argument("--no-quote", action="store_true", help="종목별 SC 시세 보강 생략")
    p.add_argument("--account", default=None, help="특정 계좌 1개만 (기본: 전체)")
    p.add_argument("--out", default=None, help="저장 파일명")
    p.add_argument("--use-existing", action="store_true",
                   help="INDI HTS를 미리 수동 로그인했으면 그 세션 재활용 (자동로그인 거치지 않음)")
    args = p.parse_args(argv)

    creds = load_creds()
    account_pw = os.environ.get("INDI_ACCOUNT_PW", "").strip()
    if not args.dry_run and not account_pw:
        sys.exit(".env 누락: INDI_ACCOUNT_PW (계좌 비밀번호)")

    # 출력 파일명 미리 결정 → 같은 prefix로 .log 자동 생성
    out = args.out
    if not out:
        ts = datetime.now(KST).strftime("%Y%m%d_%H%M")
        out = f"portfolio_{ts}.json"
    log_path = out.removesuffix(".json") + ".log"
    log_f = open(log_path, "w", encoding="utf-8")
    sys.stdout = _Tee(sys.__stdout__, log_f)
    sys.stderr = _Tee(sys.__stderr__, log_f)

    cert_mode = "인증서 모드" if creds.cert_pw else "시세조회 모드 (인증서 없음)"
    print(f"[INFO] {cert_mode}")
    print(f"[INFO] log: {log_path}")

    with IndiSession(creds, use_existing=args.use_existing) as sess:
        print(f"[OK] INDI 로그인 완료 (ProgID={creds.progid})")

        customer_num = fetch_customer_num(sess.tr)
        print(f"[+] 고객번호: {_mask_customer(customer_num)}")
        _now = datetime.now(KST)
        today_yyyymmdd = _now.strftime("%Y%m%d")
        # SAAA612QB는 영업일 기준 — 주말 보정 (공휴일 X, 검증용)
        _delta = 3 if _now.weekday() == 0 else 2 if _now.weekday() == 6 else 1
        prev_bday_yyyymmdd = (_now - timedelta(days=_delta)).strftime("%Y%m%d")
        print(f"[+] today={today_yyyymmdd}, prev_bday={prev_bday_yyyymmdd}")

        accounts = fetch_account_list(sess.tr)
        print(f"[+] 등록된 계좌: {len(accounts)}개")
        for a in accounts:
            print(f"    - {_mask_account(a['account_no'])}  {a['account_name']}")

        if args.account:
            accounts = [a for a in accounts if a["account_no"] == args.account]
            if not accounts:
                sys.exit(f"--account {args.account} 가 계좌 목록에 없음")

        if args.dry_run:
            return 0

        portfolios = []
        for i, acc in enumerate(accounts, 1):
            no = acc["account_no"]
            print(f"\n[{i}/{len(accounts)}] {_mask_account(no)} ({acc['account_name']})")
            try:
                positions = fetch_positions(sess.tr, no, account_pw)
                print(f"    positions: {len(positions)}")
                if not args.no_quote and positions:
                    enrich_positions_with_quote(sess.tr, positions)
                summary = fetch_account_summary(sess.tr, no, account_pw)
                totals = fetch_total_assets(sess.tr, no, account_pw)
                totals_z622 = fetch_total_assets_z622(
                    sess.tr, customer_num, no, today_yyyymmdd,
                )
                try:
                    saaa612qb = fetch_saaa612qb_holdings(
                        sess.tr, no, prev_bday_yyyymmdd, account_pw,
                    )
                    print(f"    saaa612qb rows: {len(saaa612qb)}")
                except (TimeoutError, RuntimeError) as e:
                    print(f"    [WARN] SAAA612QB: {e}")
                    saaa612qb = None
                portfolios.append({
                    "account_no_masked": _mask_account(no),
                    "account_name": acc["account_name"],
                    "summary": summary,
                    "totals": totals,
                    "totals_z622": totals_z622,
                    "saaa612qb": saaa612qb,
                    "positions": positions,
                })
            except Exception as e:
                print(f"    [ERROR] {type(e).__name__}: {e}")
                portfolios.append({
                    "account_no_masked": _mask_account(no),
                    "account_name": acc["account_name"],
                    "error": f"{type(e).__name__}: {e}",
                })

    snapshot = {
        "as_of": datetime.now(KST).isoformat(timespec="seconds"),
        "mode": "cert" if creds.cert_pw else "quote_only",
        "accounts": portfolios,
    }

    with open(out, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    print(f"\n[DONE] {out}")
    return 0


def _mask_account(s: str) -> str:
    if len(s) < 5:
        return "***"
    return s[:3] + "*" * (len(s) - 6) + s[-3:]


def _mask_customer(s: str) -> str:
    if len(s) < 4:
        return "***"
    return s[:2] + "*" * (len(s) - 4) + s[-2:]


if __name__ == "__main__":
    sys.exit(main())
