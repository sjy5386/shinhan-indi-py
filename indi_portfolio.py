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
    """SABA655Q1 — 종합계좌 자산 분해 (사양서 원문 39필드).

    주의: 종합계좌 전용. 연금/신탁 자산은 잘못된 필드(예: CP평가금액)에 매핑되거나
    안 잡힘. 연금/신탁은 SABZ622Q2 사용.
    """
    res = call_tr(
        ocx,
        "SABA655Q1",
        single_inputs=[(0, account_no), (1, "01"), (2, account_pw)],
        output_single_indices=list(range(39)),
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
        "missed_secured": _to_float(s.get(8, "0")),
        "domestic_mutual_eval": _to_float(s.get(9, "0")),
        "overseas_mutual_eval": _to_float(s.get(10, "0")),
        "cd_eval": _to_float(s.get(11, "0")),
        "cp_eval": _to_float(s.get(12, "0")),
        "foreign_currency_assets_eval": _to_float(s.get(13, "0")),
        "rights_collateral": _to_float(s.get(14, "0")),
        "product_subscription": _to_float(s.get(15, "0")),
        "credit_margin": _to_float(s.get(16, "0")),
        "deposit_total": _to_float(s.get(17, "0")),
        "cash_margin_total": _to_float(s.get(18, "0")),
        "withdrawable_total": _to_float(s.get(19, "0")),
        "missed_amount": _to_float(s.get(20, "0")),
        "credit_loan": _to_float(s.get(21, "0")),
        "unrepaid_loan": _to_float(s.get(22, "0")),
        "deposit_collateral_loan": _to_float(s.get(23, "0")),
        "subscription_collateral_loan": _to_float(s.get(24, "0")),
        "check_deposit": _to_float(s.get(25, "0")),
        "unpaid_interest": _to_float(s.get(26, "0")),
        "short_collateral": _to_float(s.get(27, "0")),
        "etc_check_deposit": _to_float(s.get(28, "0")),
        "collateral_shortage": _to_float(s.get(29, "0")),
        "current_collateral_ratio": _to_float(s.get(30, "0")),
        "min_maintenance_ratio": _to_float(s.get(31, "0")),
        "els_eval": _to_float(s.get(32, "0")),
        "warrant_eval": _to_float(s.get(33, "0")),
        "short_collateral_amount": _to_float(s.get(34, "0")),
        "purchase_fund_loan": _to_float(s.get(35, "0")),
        "bank_minus_loan": _to_float(s.get(36, "0")),
        "reverse_trade_date": (s.get(37, "") or "").strip(),
        "cma_eval": _to_float(s.get(38, "0")),
    }


def fetch_customer_num(ocx: QAxWidget) -> str:
    """CustomerNum TR — INPUT 없음, OUTPUT Single.0 = 고객번호(10자)."""
    res = call_tr(ocx, "CustomerNum", output_single_indices=[0])
    return (res.single.get(0, "") or "").strip()


def fetch_total_assets_z622(
    ocx: QAxWidget, customer_num: str, account_no: str, date_yyyymmdd: str,
) -> dict:
    """SABZ622Q2 — 종합계좌기간별자산평가 (연금/신탁/해외주식까지 분해).

    사양서엔 OUTPUT이 [Single]로 표기됐지만 실측은 Multi (기간 N일 → N행).
    여기선 1일 호출이라 row[0] 추출.
    """
    res = call_tr(
        ocx, "SABZ622Q2",
        single_inputs=[
            (0, customer_num), (1, account_no), (2, "1"),
            (3, date_yyyymmdd), (4, date_yyyymmdd),
            (5, "1"), (6, ""), (7, ""),
        ],
        output_multi_cols=list(range(34)),
    )
    if not res.multi:
        return {}
    r = res.multi[0]
    return {
        "as_of": (r.get(0, "") or "").strip(),
        "asset_total": _to_float(r.get(1, "0")),
        "net_assets_total": _to_float(r.get(2, "0")),
        "debt_total": _to_float(r.get(3, "0")),
        "deposit": _to_float(r.get(4, "0")),
        "cma_eval": _to_float(r.get(5, "0")),
        "rp_eval": _to_float(r.get(6, "0")),
        "fund_eval": _to_float(r.get(7, "0")),
        "stock_eval": _to_float(r.get(8, "0")),
        "bond_eval": _to_float(r.get(9, "0")),
        "futopt_eval": _to_float(r.get(10, "0")),
        "els_eval": _to_float(r.get(11, "0")),
        "foreign_deposit": _to_float(r.get(12, "0")),
        "foreign_stock_eval": _to_float(r.get(13, "0")),
        "foreign_futfx_eval": _to_float(r.get(14, "0")),
        "foreign_rp_eval": _to_float(r.get(15, "0")),
        "trust_pension_eval": _to_float(r.get(16, "0")),
        "fund_subscription": _to_float(r.get(17, "0")),
        "subscription_margin": _to_float(r.get(18, "0")),
        "loan": _to_float(r.get(19, "0")),
        "annuity_savings_eval": _to_float(r.get(20, "0")),
        "service_eval": _to_float(r.get(21, "0")),
        "wrap_eval": _to_float(r.get(22, "0")),
        "short_collateral": _to_float(r.get(23, "0")),
        "physical_product_eval": _to_float(r.get(24, "0")),
        "deposit_balance": _to_float(r.get(25, "0")),
        "trade_balance": _to_float(r.get(26, "0")),
        "financial_product_balance": _to_float(r.get(27, "0")),
        "product_balance": _to_float(r.get(28, "0")),
        "consignment_balance": _to_float(r.get(29, "0")),
        "a_deposit_in": _to_float(r.get(30, "0")),
        "a_deposit_out": _to_float(r.get(31, "0")),
        "a_stock_in": _to_float(r.get(32, "0")),
        "a_stock_out": _to_float(r.get(33, "0")),
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
