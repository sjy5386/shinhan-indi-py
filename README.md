# INDI 포트폴리오 → AI 분석 파이프라인 (v0)

신한투자증권 INDI OCX를 PyQt5로 호출해 **국내 현물** 포트폴리오 스냅샷을 JSON으로
덤프합니다. 그 JSON을 Claude(또는 다른 AI)에게 던지면 분석 받음.

## 환경

이 프로젝트는 **Windows ARM64 / x64 모두 32bit (x86) 트랙**을 기본으로 잡았습니다.

| 플랫폼 | 권장 트랙 | 이유 |
|--------|----------|------|
| **Windows ARM64 (Surface Pro X 등)** | 32bit (x86) | x64 OCX의 `DllRegisterServer`가 ARM64 emulation 경계를 못 넘음. x86 OCX는 SysWOW64에서 정상. |
| **Windows x64** | 32bit (x86) 또는 64bit | 둘 다 가능. 32bit이 가장 빠른 길 (이미 등록됨). |

## 사전 준비 — 한 번만

### 1. OCX 등록 확인 (대부분 추가 작업 불필요)

INDI HTS 설치 시점에 32bit OCX `GIEXPERTCONTROL.GiExpertControlCtrl.1`이 이미
등록되어 있습니다. 확인:
```powershell
cd <project_root>   # 이 폴더 경로
powershell -ExecutionPolicy Bypass -File verify_ocx.ps1
```
"32bit hive: REGISTERED -> ..." 가 나오면 OK.

> x64 Windows에서 64bit으로 가고 싶으면 `register_ocx.bat`을 관리자 권한으로
> 실행 (ARM64에서는 보통 ExitCode 3으로 실패하므로 32bit 권장).

### 2. 32bit Python 설치 (ARM64에서도 이걸 받으세요)

[python.org/downloads/windows](https://www.python.org/downloads/windows/) 에서 Python 3.11
또는 3.12의 **"Windows installer (32-bit)"** 받기.

> ARM64에서도 32bit (x86) Python이 emulation으로 잘 돕니다. INDI 32bit OCX와
> 같은 비트 프로세스여야 하므로 64bit/ARM64 Python이 아닌 **32bit**를 받으세요.

설치 시 "Add python.exe to PATH" 체크.

확인:
```powershell
python -c "import struct; print('bits:', struct.calcsize('P')*8)"
# bits: 32  여야 함
```

### 3. 가상환경 + 의존성

프로젝트 폴더에서:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

PowerShell 스크립트 실행이 막혀있으면:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 4. 자격 증명

`.env`에 다음 채우기 (필수):

```
INDI_ID=신한_ID
INDI_PW=로그인_PW
INDI_ACCOUNT_PW=계좌_비밀번호
```

선택:
- `INDI_CERT_PW`는 **비워두면 시세조회 전용 모드** — 인증서 없이 로그인. 잔고 조회는 보통 가능, 주문은 불가.
- `INDI_ACCOUNT_NO`는 **비워두면 전체 계좌 자동 enumerate** (`AccountList` TR). 특정 계좌만 보려면 채우기.

## 실행

```powershell
# 로그인까지만 검증
python dump_portfolio.py --dry-run

# 풀 덤프 → portfolio_YYYYMMDD_HHMM.json
python dump_portfolio.py

# 시세 보강 생략(빠름)
python dump_portfolio.py --no-quote
```

생성된 JSON을 INDI HTS 화면 잔고와 한 번 대조해 보세요.

## AI 분석 받기

생성된 `portfolio_YYYYMMDD_HHMM.json`을 Claude에게 첨부해 분석 요청:

> "이 JSON으로 자산 배분, 손익 기여도, 집중도 리스크, 시나리오 분석 해줘"

## 파일 구성

| 파일 | 역할 |
|------|------|
| `notes.md` | TR 사양서 발췌 (필드 인덱스 정리) |
| `indi_session.py` | OCX 인스턴스 + 로그인/로그아웃 |
| `indi_tr.py` | RequestData→ReceiveData를 동기 함수로 감싼 헬퍼 |
| `indi_portfolio.py` | SABA200QB / SABA610Q1 / SABA655Q1 / SC 호출 함수 |
| `dump_portfolio.py` | entry point (CLI) |
| `register_ocx.bat` | 64bit OCX regsvr32 등록 도우미 |

## 한계 / 다음 단계

- **v0는 국내 현물 전용.** 해외주식 종목별 보유는 `SABA655Q1`의 "외화자산 평가금액"
  합계로만 잡힘 — 종목별은 `AG` 실시간 메시지 등록/해제 패턴이 필요(v0.5).
- **장중 호출 권장.** 잔고 자체는 장후에도 가능하지만 `SC`(현재가)는 장중·종가 모두
  가능. 장 마감 직후가 가장 의미 있는 시점.
- **TR 호출 빈도 제한**이 INDI에 있으므로 종목 수 많으면 throttle 추가 필요.
- 안정화 후 동일 함수를 MCP 서버로 노출하면 대화 중 직접 호출 가능 (v2).
