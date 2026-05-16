"""TR 호출을 동기 함수처럼 쓸 수 있게 감싸는 헬퍼.

OCX 실제 시그니처: SetQueryName(QVariant), SetSingleData(int,QVariant),
RequestData(), ReceiveData(int), ReceiveSysMsg(int), GetSingleData(int),
GetMultiData(int,int), GetMultiRowCount().

이벤트는 한 번만 connect하고 rqid → callback dict로 라우팅하면 깔끔하지만,
v0는 단순화: 매 호출마다 lambda connect + EventLoop 대기.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Sequence

from PyQt5.QtCore import QEventLoop, QTimer
from PyQt5.QAxContainer import QAxWidget


@dataclass
class TrResult:
    rqid: int
    single: dict[int, str]
    multi: list[dict[int, str]]
    elapsed_ms: int


def call_tr(
    ocx: QAxWidget,
    tr_code: str,
    single_inputs: Sequence[tuple[int, str]] = (),
    output_single_indices: Sequence[int] = (),
    output_multi_cols: Sequence[int] = (),
    timeout_sec: float = 15.0,
    debug: bool = False,
) -> TrResult:
    """단발 TR을 동기적으로 호출하고 결과를 반환."""
    # 직접 호출 사용 (PyQt가 QVariant 자동 변환).
    ocx.SetQueryName(tr_code)
    for idx, val in single_inputs:
        ocx.SetSingleData(idx, str(val))
    rqid = ocx.RequestData()

    if debug:
        print(f"    [tr] {tr_code}: rqid={rqid}")
    if not isinstance(rqid, int) or rqid < 0:
        err_code = ocx.GetErrorCode()
        err_msg = ocx.GetErrorMessage()
        raise RuntimeError(
            f"RequestData 실패 (tr={tr_code}, rqid={rqid}, "
            f"code={err_code!r}, msg={err_msg!r})"
        )

    state = {"received": False, "sys_msg": None}
    loop = QEventLoop()

    def on_data(received_rqid):
        if debug:
            print(f"    [tr] ReceiveData(rqid={received_rqid})")
        if received_rqid == rqid:
            state["received"] = True
            loop.quit()

    def on_sys(msg_id):
        if debug:
            print(f"    [tr] ReceiveSysMsg(id={msg_id})")
        state["sys_msg"] = msg_id

    ocx.ReceiveData.connect(on_data)
    ocx.ReceiveSysMsg.connect(on_sys)
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)

    t0 = time.monotonic()
    timer.start(int(timeout_sec * 1000))
    loop.exec_()
    elapsed_ms = int((time.monotonic() - t0) * 1000)

    for sig, cb in ((ocx.ReceiveData, on_data), (ocx.ReceiveSysMsg, on_sys)):
        try:
            sig.disconnect(cb)
        except TypeError:
            pass

    if not state["received"]:
        err_code = ocx.GetErrorCode()
        err_msg = ocx.GetErrorMessage()
        raise TimeoutError(
            f"TR {tr_code} 응답 {timeout_sec}초 초과 "
            f"(sys_msg={state['sys_msg']!r}, code={err_code!r}, msg={err_msg!r})"
        )

    single = {i: str(ocx.GetSingleData(i)).strip()
              for i in output_single_indices}
    n_rows = int(ocx.GetMultiRowCount() or 0)
    multi = [
        {c: str(ocx.GetMultiData(row, c)).strip()
         for c in output_multi_cols}
        for row in range(n_rows)
    ]
    if debug:
        print(f"    [tr] {tr_code} done: rows={n_rows}, elapsed={elapsed_ms}ms")
    return TrResult(rqid=rqid, single=single, multi=multi, elapsed_ms=elapsed_ms)
