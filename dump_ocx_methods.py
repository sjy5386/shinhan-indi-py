"""OCX가 노출하는 모든 메서드/속성 목록 출력 (디버그용)."""
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget

app = QApplication(sys.argv)
ocx = QAxWidget("GIEXPERTCONTROL.GiExpertControlCtrl.1")

mo = ocx.metaObject()
print("=== Methods ===")
for i in range(mo.methodCount()):
    m = mo.method(i)
    sig = bytes(m.methodSignature()).decode("utf-8", errors="replace")
    typ = ["signal", "slot", "method", "constructor"][m.methodType()]
    if "QObject::" in sig or "QWidget::" in sig:
        continue
    print(f"  [{typ}] {sig}")

print("\n=== Properties ===")
for i in range(mo.propertyCount()):
    prop = mo.property(i)
    print(f"  {prop.name()} : {prop.typeName()}")
