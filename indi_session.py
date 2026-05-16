"""INDI OCX 세션 관리 — 로그인/로그아웃 + QApplication wiring.

OCX는 GUI 메시지 루프를 요구하므로 PyQt5 QApplication 위에서 동작.
"""
from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass

from PyQt5.QtCore import QEventLoop, QTimer
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget


@dataclass
class IndiCreds:
    user_id: str
    user_pw: str
    cert_pw: str  # 빈 문자열이면 인증서 없이 시세조회 모드 로그인
    starter_path: str
    progid: str


def load_creds() -> IndiCreds:
    from dotenv import load_dotenv
    load_dotenv()
    # CERT_PW는 선택 (없으면 시세조회 모드)
    missing = [k for k in ("INDI_ID", "INDI_PW", "INDI_STARTER_PATH", "INDI_PROGID")
               if not os.getenv(k)]
    if missing:
        raise SystemExit(f".env 누락: {', '.join(missing)}")
    return IndiCreds(
        user_id=os.environ["INDI_ID"],
        user_pw=os.environ["INDI_PW"],
        cert_pw=os.environ.get("INDI_CERT_PW", ""),
        starter_path=os.environ["INDI_STARTER_PATH"],
        progid=os.environ["INDI_PROGID"],
    )


class IndiSession:
    """OCX 인스턴스 + 로그인 상태를 들고 있는 세션.

    - `tr`: 조회성 데이터용 OCX
    - `real`: 실시간 데이터용 OCX (별도 인스턴스 권장 — 예제 패턴)
    """

    def __init__(self, creds: IndiCreds, app: QApplication | None = None,
                 use_existing: bool = False):
        self.creds = creds
        self.use_existing = use_existing
        self.app = app or QApplication.instance() or QApplication(sys.argv)
        self.tr = QAxWidget(creds.progid)
        self.real = QAxWidget(creds.progid)
        self._logged_in = False

    def login(self, timeout_sec: int = 60, use_existing: bool = False) -> None:
        """StartIndi 호출 후 GetCommState()==0(정상)이 될 때까지 대기.

        주의: 사양서상 GetCommState() 반환값은
            0 = 통신 상태 정상 (로그인 완료)
            1 = 통신 상태 비정상
        """
        print(f"  StartIndi(id={self.creds.user_id!r}, "
              f"pw=*({len(self.creds.user_pw)}), "
              f"cert=*({len(self.creds.cert_pw)}) [공백=조회모드], "
              f"path={self.creds.starter_path!r})")

        def _call_start():
            try:
                return self.tr.StartIndi(
                    self.creds.user_id, self.creds.user_pw,
                    self.creds.cert_pw, self.creds.starter_path,
                )
            except AttributeError:
                return self.tr.dynamicCall(
                    "StartIndi(QString, QString, QString, QString)",
                    self.creds.user_id, self.creds.user_pw,
                    self.creds.cert_pw, self.creds.starter_path,
                )

        # 위키독스 패턴: starter exe가 백그라운드에서 떠올라오는 동안
        # 첫 호출들은 False일 수 있음. timeout까지 재시도.
        deadline = time.monotonic() + timeout_sec
        ok = False
        attempts = 0
        while time.monotonic() < deadline:
            attempts += 1
            ok = _call_start()
            if ok:
                print(f"  StartIndi True (attempt {attempts})")
                break
            if attempts == 1 or attempts % 10 == 0:
                print(f"  StartIndi False (attempt {attempts}, retrying...)")
            self._pump(500)

        if not ok:
            try:
                err_code = self.tr.GetErrorCode()
                err_msg = self.tr.GetErrorMessage()
                err_state = self.tr.GetErrorState()
            except AttributeError:
                err_code = self.tr.dynamicCall("GetErrorCode()")
                err_msg = self.tr.dynamicCall("GetErrorMessage()")
                err_state = self.tr.dynamicCall("GetErrorState()")
            hint = (
                "\n  힌트: timeout 동안 계속 False 반환. 가능한 원인:\n"
                "    1) PowerShell이 관리자 권한 아님 — 관리자 PowerShell에서 재시도\n"
                "    2) INDI HTS GUI에서 시세조회전용 모드 사전 설정 누락\n"
                "    3) ID/PW 불일치\n"
                "    4) 다른 INDI/giexpertstarter 프로세스 충돌\n"
            )
            raise RuntimeError(
                f"StartIndi 실패 ({attempts}회 시도). "
                f"code={err_code!r} state={err_state!r} msg={err_msg!r}{hint}"
            )

        # StartIndi True 받았으면 CommState=0(정상) 폴링 (보통 즉시 0)
        state = -1
        while time.monotonic() < deadline:
            try:
                state = self.tr.GetCommState()
            except AttributeError:
                state = self.tr.dynamicCall("GetCommState()")
            if state == 0:
                self._logged_in = True
                print(f"  로그인 완료 (CommState=0 정상)")
                return
            self._pump(500)
        raise TimeoutError(
            f"StartIndi True 후 CommState=0 미도달 (마지막={state}; 1=비정상)"
        )

    def logout(self) -> None:
        if self._logged_in:
            self.tr.dynamicCall("CloseIndi()")
            self._logged_in = False

    def _pump(self, ms: int) -> None:
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec_()

    def __enter__(self) -> "IndiSession":
        self.login(use_existing=self.use_existing)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        # 기존 세션 재활용한 경우 우리가 만든 게 아니므로 닫지 않음
        if not self.use_existing:
            self.logout()
