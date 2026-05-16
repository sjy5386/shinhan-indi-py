# INDI TR 사양 메모 — 포트폴리오 분석용

`Special_Interface.doc`에서 추출. v0(국내 현물)에서 사용할 4개 TR.

## 환경

| 항목 | 값 |
|-----|----|
| 32bit ProgID | `GIEXPERTCONTROL.GiExpertControlCtrl.1` (이미 등록) |
| 32bit OCX | `C:\SHINHAN-i\indi\giexpertcontrol.ocx` |
| 64bit ProgID | `GIEXPERTCONTROL6.GIExpertControl6Ctrl.1` (regsvr32 등록 필요) |
| 64bit OCX | `C:\SHINHAN-i\indi\giexpertcontrol64.ocx` |
| Starter | `C:\SHINHAN-i\indi\giexpertstarter.exe` |

## 로그인 (Comm_Indi 메서드)

- `StartIndi(ID, PW, CERT_PW, STARTER_PATH)` → bool
- `CloseIndi()` → bool

비동기로 진행되므로 호출 후 `GetCommState()` 폴링 또는 `ReceiveSysMsg` 이벤트 대기.

## TR 호출 패턴

```
SetQueryName("TR_CODE")
SetSingleData(idx, value)         # 입력 Single
SetMultiData(row, col, value)     # 입력 Multi (필요 시)
rqid = RequestData()              # 호출
# → ReceiveData(rqid) 이벤트로 결과 수신
GetSingleData(idx)                # 출력 Single
GetMultiRowCount()                # 출력 Multi 행 수
GetMultiData(row, col)            # 출력 Multi 셀
```

---

## SABA200QB — 잔고 및 주문 체결 조회 (종목별 보유)

**INPUT (Single)**

| # | 항목 | Size | 비고 |
|---|------|------|------|
| 0 | 계좌번호 | 11 | |
| 1 | 상품구분 | 2 | 항상 "01" |
| 2 | 비밀번호 | 9 | 계좌 비밀번호 |

**OUTPUT (Multi — 종목별 1행)**

| # | 항목 | Size | 비고 |
|---|------|------|------|
| 0 | 종목코드 | 12 | 표준코드 (`A` + 단축코드 6자리) |
| 1 | 종목명 | 50 | |
| 2 | 결제일 잔고 수량 | 18 | |
| 3 | 매도 미체결 수량 | 18 | |
| 4 | 매수 미체결 수량 | 18 | |
| 5 | 현재가 | 20 | |
| 6 | 평균단가 | 20 | 일반 평균 단가 |
| 7 | 신용잔고수량 | 10 | |
| 8 | 코스피대용수량 | 18 | |

> 잔고 없는 매수 미체결만 있는 종목은 평균단가가 0.

---

## SABA610Q1 — 계좌잔고 조회금액 (현금/총평가)

**INPUT (Single)**

| # | 항목 | Size | 비고 |
|---|------|------|------|
| 0 | 계좌번호 | 11 | |
| 1 | 상품구분 | 2 | 항상 "01" |
| 2 | 비밀번호 | 9 | |
| 3 | 구분1 | 1 | 1:매매기준 / 2:결제기준 / 3:신용잔고 |
| 4 | 단가구분 | 1 | 1:평균 / 2:제비용 / 3:매수비용 / 4:매도비용 |
| 5 | 종목구분코드 | 1 | 0:전체 / 1:ELW제외 / 2:ELW만 |
| 6 | 작업구분 | 1 | 0:전체Output / 1:Multi제외 / 2:Multi만 |
| 7 | 조회시세구분 | 1 | 0:통합시세 / 1:KRX (NULL=KRX) |

**OUTPUT (Single — 핵심 발췌)**

| # | 항목 |
|---|------|
| 2 | 예수금 |
| 9 | 인출가능금액 |
| 12 | 주문가능현금 |
| 15 | 주식매수금액 |
| 16 | 실현손익금액 |
| 17 | 채권평가금액 |
| 18 | 주식평가금액 |
| 19 | 미실현손익금액 |
| 21 | 위탁순자산평가금액 |
| 22 | 미실현손익율 |
| 28 | 상품순자산평가금액 |

---

## SABA655Q1 — 총자산 계좌잔고 조회 (전체 자산군 합계)

**INPUT (Single)**

| # | 항목 | Size | 비고 |
|---|------|------|------|
| 0 | 계좌번호 | 11 | |
| 1 | 상품구분 | 2 | 01:종합계좌 / 10:KOSPI선옵 / 11:KOSDAQ선옵 / 21:증권저축 |
| 2 | 비밀번호 | 9 | |

**OUTPUT (Single — 핵심 발췌)**

| # | 항목 |
|---|------|
| 0 | 순자산 평가금액 |
| 1 | 총자산 평가금액 |
| 2 | 대출/미납금 합계 |
| 3 | 주식 평가금액 |
| 4 | KOSPI선물옵션평가금액 |
| 5 | 채권 평가금액 |
| 6 | RP 평가금액 |
| 7 | 수익증권 평가금액 |
| 9 | 국내뮤츄얼 평가금액 |
| 10 | 해외뮤추얼 평가금액 |
| 13 | 외화자산 평가금액 |
| 17 | 예수금합계 |
| 19 | 인출가능금액합계 |
| 32 | ELS평가금액 |
| 33 | WARRANT평가금액 |
| 38 | CMA평가금액 |

> 해외주식 종목별은 별도 TR(AG 실시간) 필요. 합계는 "외화자산 평가금액"에 포함됨(국내 현물주식은 "주식 평가금액").

---

## SC — 현물 현재가

**INPUT (Single)**

| # | 항목 | Size |
|---|------|------|
| 0 | 단축코드 | 6 |

**OUTPUT (Single — 핵심 발췌)**

| # | 항목 |
|---|------|
| 1 | 단축코드 |
| 2 | 체결시간 |
| 3 | 현재가 |
| 4 | 전일대비구분 (1:상한 2:상승 3:보합 4:하한 5:하락) |
| 5 | 전일대비 |
| 6 | 전일대비율 |
| 7 | 누적거래량 |
| 10 | 시가 |
| 11 | 고가 |
| 12 | 저가 |
| 20 | 매도1호가 |
| 21 | 매수1호가 |
