"""OCX dispatch만 검증 (로그인 X). 32bit emulation에서 INDI OCX가 살아있는지 확인."""
import struct
import sys

print(f"python   : {sys.executable}")
print(f"bits     : {struct.calcsize('P') * 8}")
assert struct.calcsize("P") * 8 == 32, "32bit Python 아님"

from PyQt5.QtWidgets import QApplication  # noqa: E402
from PyQt5.QAxContainer import QAxWidget  # noqa: E402

app = QApplication(sys.argv)
progid = "GIEXPERTCONTROL.GiExpertControlCtrl.1"
ocx = QAxWidget(progid)
print(f"progid   : {progid}")
print(f"axobject : {ocx.control()!r}")

# GetCommState는 로그인 전에도 안전하게 호출됨 (보통 0)
state = ocx.dynamicCall("GetCommState()")
print(f"CommState: {state}  (0=before login)")

print("\n[OK] OCX dispatch passed. Next: fill .env and run dump_portfolio.py --dry-run")
