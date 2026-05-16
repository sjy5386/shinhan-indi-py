# shinhan-indi-py

신한투자증권 INDI OCX를 Python에서 호출하는 비공식 도구. v0은 **국내 현물** 잔고
스냅샷을 JSON으로 덤프해 AI 분석에 넘기는 단발성 파이프라인.

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
| `Special_Interface.md` | Special_Interface.doc 전체 사양서 (TR/이벤트/메소드 상세) |
| `indi_session.py` | OCX 인스턴스 + 로그인/로그아웃 |
| `indi_tr.py` | RequestData→ReceiveData를 동기 함수로 감싼 헬퍼 |
| `indi_portfolio.py` | SABA200QB / SABA610Q1 / SABA655Q1 / SABZ622Q2 / SAAA612QB / CustomerNum / SC 호출 함수 |
| `dump_portfolio.py` | entry point (CLI) |
| `register_ocx.bat` | 64bit OCX regsvr32 등록 도우미 |

## 한계 / 다음 단계

- **v0.5 추가 분해:** `SABZ622Q2`(종합계좌기간별자산평가)로 연금저축/신탁퇴직연금/
  해외주식이 별도 필드로 분해됨. `CustomerNum` TR로 받은 10자 고객번호가 INPUT에
  필요. 사양서가 OUTPUT을 `[Single]`로 표기했지만 실측은 Multi — 함정 주의
  (notes.md 참조).
- **v0.6 해외주식 종목별 분해 — 시세조회 모드 불가 (인증서 발급 대기):**
  `SAAA612QB`(특정일잔고확인서) 단발 TR로 종목별 잔량/평가금액 Multi 호출 추가.
  JSON의 각 계좌에 `saaa612qb` 키로 dump. **시세조회 모드 실측에서 8계좌 모두
  rows=0** (TR 응답 정상, 빈 데이터). 권한 차등 추정. 인증서 발급 후
  `.env`에 `INDI_CERT_PW` 채우고 재실행하면 즉시 결판. 코드는 보존됨.
  (notes.md SAAA612QB 섹션 참조)
- **로그 자동 저장:** `dump_portfolio.py` 실행 시 `portfolio_*.json` 옆에
  같은 prefix의 `.log` 자동 생성 (stdout/stderr Tee). 디버그/AI 분석에 활용.
- **v0.7 후보 — AG 실시간 잔고:** 인증서 모드에서도 SAAA612QB가 해외 미지원으로
  판명 시 `AG` 실시간 메시지 등록/해제 패턴으로 전환. 단, Special_Interface.md
  변경이력 L115에만 등재되고 본 사양 누락 → 필드 역공학 필요.
- **장중 호출 권장.** 잔고 자체는 장후에도 가능하지만 `SC`(현재가)는 장중·종가 모두
  가능. 장 마감 직후가 가장 의미 있는 시점.
- **TR 호출 빈도 제한**이 INDI에 있으므로 종목 수 많으면 throttle 추가 필요.
- 안정화 후 동일 함수를 MCP 서버로 노출하면 대화 중 직접 호출 가능 (v2).
