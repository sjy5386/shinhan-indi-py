"""국내 현물 포트폴리오 데이터 수집.

3개 TR을 호출해서 dict를 만든다:
- SABA200QB: 종목별 잔고 (positions)
- SABA610Q1: 계좌 현금/평가 요약
- SABA655Q1: 총자산(전 자산군 합계)
- SC: 종목별 현재가 (SABA200QB 결과 보강)
"""
from __future__ import annotations

from PyQt5.QAxContainer import QAxWidget

from indi_tr import call_tr


def fetch_account_list(ocx: QAxWidget) -> list[dict]:
    """AccountList TR — 로그인된 사용자의 전체 계좌 목록.

    INPUT: 없음
    OUTPUT (Multi): 0=계좌번호(11), 1=계좌명(20)
    """
    res = call_tr(
        ocx,
        "AccountList",
        single_inputs=(),
        output_multi_cols=[0, 1],
        debug=True,
    )
    return [
        {"account_no": (r.get(0, "") or "").strip(),
         "account_name": (r.get(1, "") or "").strip()}
        for r in res.multi
        if (r.get(0, "") or "").strip()
    ]


def _to_int(s: str) -> int:
    s = (s or "").strip()
    return int(s) if s and s.lstrip("-").isdigit() else 0


def _to_float(s: str) -> float:
    s = (s or "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def fetch_positions(ocx: QAxWidget, account_no: str, account_pw: str) -> list[dict]:
    """SABA200QB — 종목별 보유 (잔고/평균단가/현재가/미체결)."""
    res = call_tr(
        ocx,
        "SABA200QB",
        single_inputs=[(0, account_no), (1, "01"), (2, account_pw)],
        output_multi_cols=[0, 1, 2, 3, 4, 5, 6, 7, 8],
    )
    positions = []
    for row in res.multi:
        qty = _to_int(row.get(2, "0"))
        if qty == 0 and _to_int(row.get(3, "0")) == 0 and _to_int(row.get(4, "0")) == 0:
            continue
        last = _to_float(row.get(5, "0"))
        avg = _to_float(row.get(6, "0"))
        eval_amt = qty * last
        cost = qty * avg
        pnl = eval_amt - cost
        pnl_pct = (pnl / cost * 100) if cost else 0.0
        positions.append({
            "symbol_full": row.get(0, "").strip(),
            "name": row.get(1, "").strip(),
            "qty": qty,
            "pending_sell_qty": _to_int(row.get(3, "0")),
            "pending_buy_qty": _to_int(row.get(4, "0")),
            "last": last,
            "avg_price": avg,
            "eval": eval_amt,
            "cost": cost,
            "pnl": pnl,
            "pnl_pct": round(pnl_pct, 2),
            "credit_qty": _to_int(row.get(7, "0")),
        })
    return positions


def fetch_account_summary(ocx: QAxWidget, account_no: str, account_pw: str) -> dict:
    """SABA610Q1 — 계좌 현금/평가 요약 (국내 현물 기준)."""
    indices = [2, 9, 12, 15, 16, 17, 18, 19, 21, 22, 28]
    res = call_tr(
        ocx,
        "SABA610Q1",
        single_inputs=[
            (0, account_no), (1, "01"), (2, account_pw),
            (3, "1"), (4, "1"), (5, "0"), (6, "0"), (7, "0"),
        ],
        output_single_indices=indices,
    )
    s = res.single
    return {
        "deposit": _to_float(s.get(2, "0")),
        "withdrawable": _to_float(s.get(9, "0")),
        "cash_orderable": _to_float(s.get(12, "0")),
        "stock_buy_amount": _to_float(s.get(15, "0")),
        "realized_pnl": _to_float(s.get(16, "0")),
        "bond_eval": _to_float(s.get(17, "0")),
        "stock_eval": _to_float(s.get(18, "0")),
        "unrealized_pnl": _to_float(s.get(19, "0")),
        "net_assets": _to_float(s.get(21, "0")),
        "unrealized_pnl_pct": _to_float(s.get(22, "0")),
        "product_net_assets": _to_float(s.get(28, "0")),
    }


def fetch_total_assets(ocx: QAxWidget, account_no: str, account_pw: str) -> dict:
    """SABA655Q1 — 전 자산군 합계 (해외주식 포함은 '외화자산' 한 줄)."""
    indices = [0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 13, 17, 19, 32, 33, 38]
    res = call_tr(
        ocx,
        "SABA655Q1",
        single_inputs=[(0, account_no), (1, "01"), (2, account_pw)],
        output_single_indices=indices,
    )
    s = res.single
    return {
        "net_assets_total": _to_float(s.get(0, "0")),
        "total_assets": _to_float(s.get(1, "0")),
        "loans_unpaid": _to_float(s.get(2, "0")),
        "stock_eval": _to_float(s.get(3, "0")),
        "kospi_futopt_eval": _to_float(s.get(4, "0")),
        "bond_eval": _to_float(s.get(5, "0")),
        "rp_eval": _to_float(s.get(6, "0")),
        "fund_eval": _to_float(s.get(7, "0")),
        "domestic_mutual_eval": _to_float(s.get(9, "0")),
        "overseas_mutual_eval": _to_float(s.get(10, "0")),
        "foreign_currency_assets_eval": _to_float(s.get(13, "0")),
        "deposit_total": _to_float(s.get(17, "0")),
        "withdrawable_total": _to_float(s.get(19, "0")),
        "els_eval": _to_float(s.get(32, "0")),
        "warrant_eval": _to_float(s.get(33, "0")),
        "cma_eval": _to_float(s.get(38, "0")),
    }


def enrich_positions_with_quote(ocx: QAxWidget, positions: list[dict]) -> None:
    """SC TR로 시가/고가/저가/전일대비 추가 (선택)."""
    for p in positions:
        full = p["symbol_full"]
        short = full[1:7] if full.startswith("A") and len(full) >= 7 else full[-6:]
        p["symbol"] = short
        try:
            res = call_tr(
                ocx, "SC",
                single_inputs=[(0, short)],
                output_single_indices=[2, 3, 4, 5, 6, 7, 10, 11, 12, 20, 21],
            )
            s = res.single
            p["quote"] = {
                "trade_time": s.get(2, ""),
                "price": _to_float(s.get(3, "0")),
                "change_dir": s.get(4, ""),
                "change": _to_float(s.get(5, "0")),
                "change_pct": _to_float(s.get(6, "0")),
                "volume": _to_int(s.get(7, "0")),
                "open": _to_float(s.get(10, "0")),
                "high": _to_float(s.get(11, "0")),
                "low": _to_float(s.get(12, "0")),
                "ask1": _to_float(s.get(20, "0")),
                "bid1": _to_float(s.get(21, "0")),
            }
        except (TimeoutError, RuntimeError) as e:
            p["quote_error"] = str(e)
