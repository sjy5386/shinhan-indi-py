"""AG (해외주식 실시간 잔고) RT 등록 시도 + ReceiveRTData 캡처 → 필드 dump.

사양서 변경이력 L115에 등재됐지만 본 사양 누락 → OUTPUT 필드 인덱스 역공학용.
결과를 JSON + log 자동 저장. plan: shinhan-indi-py-v0-7-ag-rt-reverse.md Stage 1.
"""
from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone, timedelta

# Windows 콘솔(cp949) 한글 보호
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from PyQt5.QtCore import QEventLoop, QTimer  # noqa: E402

from indi_session import IndiSession, load_creds  # noqa: E402


KST = timezone(timedelta(hours=9))
CAPTURE_SECONDS = 30
DUMP_INDICES = list(range(31))  # 0~30 광범위 dump


class _Tee:
    def __init__(self, *streams):
        self.streams = streams
    def write(self, s):
        for st in self.streams:
            st.write(s)
            st.flush()
    def flush(self):
        for st in self.streams:
            st.flush()


def main() -> int:
    ts = datetime.now(KST).strftime("%Y%m%d_%H%M")
    out_json = f"ag_probe_{ts}.json"
    out_log = f"ag_probe_{ts}.log"
    log_f = open(out_log, "w", encoding="utf-8")
    sys.stdout = _Tee(sys.__stdout__, log_f)
    sys.stderr = _Tee(sys.__stderr__, log_f)

    creds = load_creds()
    cert_mode = "인증서 모드" if creds.cert_pw else "시세조회 모드 (인증서 없음)"
    print(f"[INFO] {cert_mode}")
    print(f"[INFO] log: {out_log}, json: {out_json}")

    captures: list[dict] = []
    register_ok: bool | None = None
    register_err: dict | None = None

    with IndiSession(creds) as sess:
        # 사양서 L1442 "하나의 컨트롤로 여러 RT 처리 가능" → 이미 로그인된 self.tr 사용
        ocx = sess.tr

        def on_rt(strType):
            t = datetime.now(KST).isoformat(timespec="seconds")
            single = {}
            for i in DUMP_INDICES:
                try:
                    v = str(ocx.GetSingleData(i)).strip()
                except Exception as e:
                    v = f"<ERR:{type(e).__name__}:{e}>"
                single[i] = v
            captures.append({"ts": t, "strType": str(strType), "single": single})
            nonzero = " ".join(f"{i}={v!r}" for i, v in single.items() if v)
            print(f"  [RT] {strType} #{len(captures)}: {nonzero}")

        # ReceiveRTData connect
        try:
            ocx.ReceiveRTData.connect(on_rt)
            print("[INFO] ReceiveRTData connected")
        except Exception as e:
            print(f"[ERR] ReceiveRTData connect 실패: {type(e).__name__}: {e}")
            traceback.print_exc()
            return 1

        # AG 등록
        try:
            register_ok = bool(ocx.RequestRTReg("AG", "*"))
        except Exception as e:
            print(f"[ERR] RequestRTReg 호출 예외: {type(e).__name__}: {e}")
            traceback.print_exc()
            register_ok = False
        print(f"[INFO] RequestRTReg('AG', '*') → {register_ok}")
        if not register_ok:
            try:
                register_err = {
                    "code": str(ocx.GetErrorCode()),
                    "msg": str(ocx.GetErrorMessage()),
                }
                print(f"  err_code={register_err['code']!r}, msg={register_err['msg']!r}")
            except Exception as e:
                register_err = {"introspect_fail": f"{type(e).__name__}: {e}"}
                print(f"  err 정보 조회 실패: {register_err}")

        # N초 캡처 (등록 실패해도 어차피 콜백 0건이라 짧게 끝남)
        print(f"[INFO] {CAPTURE_SECONDS}초 캡처 시작...")
        loop = QEventLoop()
        QTimer.singleShot(CAPTURE_SECONDS * 1000, loop.quit)
        loop.exec_()
        print(f"[INFO] 캡처 종료: {len(captures)}건")

        # 해제
        try:
            unreg_ok = bool(ocx.UnRequestRTReg("AG", "*"))
            print(f"[INFO] UnRequestRTReg('AG', '*') → {unreg_ok}")
        except Exception as e:
            print(f"[WARN] UnRequestRTReg 실패: {type(e).__name__}: {e}")
        try:
            ocx.ReceiveRTData.disconnect(on_rt)
        except (TypeError, RuntimeError):
            pass

    snapshot = {
        "as_of": datetime.now(KST).isoformat(timespec="seconds"),
        "mode": "cert" if creds.cert_pw else "quote_only",
        "register_ok": register_ok,
        "register_err": register_err,
        "capture_seconds": CAPTURE_SECONDS,
        "dump_indices": DUMP_INDICES,
        "captures": captures,
    }
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    print(f"[DONE] {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
