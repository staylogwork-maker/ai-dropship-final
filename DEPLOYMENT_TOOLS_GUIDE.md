# 🚀 배포 도구 사용 가이드

## 📌 최신 커밋 확인

```bash
cd ~/ai-dropship-final
git log -1 --oneline
```

**최신 커밋**: `22a7493` (또는 그 이상)

---

## 🆘 긴급 상황: DB 검증 마커가 안 보임

**증상**: 서버를 재시작했지만 로그에 "DATABASE INITIALIZATION COMPLETE" 마커가 보이지 않음

**즉시 해결**:

```bash
cd ~/ai-dropship-final
sudo bash fix_deployment.sh
```

이 스크립트는 **12단계**에 걸쳐 모든 것을 자동으로 수정합니다:

1. ✅ 작업 디렉토리 확인
2. ✅ GitHub에서 최신 코드 가져오기
3. ✅ DB 검증 마커 존재 확인
4. ✅ Systemd 서비스 파일 확인 및 수정
5. ✅ 로그 디렉토리 생성 및 권한 설정
6. ✅ 데이터베이스 확인
7. ✅ Systemd 데몬 리로드
8. ✅ 기존 프로세스 종료
9. ✅ 서비스 재시작
10. ✅ 서비스 상태 확인
11. ✅ 로그 확인 (최근 20줄)
12. ✅ DB 검증 마커 확인

---

## 🛠 배포 도구 목록

### 1. `fix_deployment.sh` ⭐ **가장 강력**

**용도**: 모든 문제를 한 번에 해결

```bash
sudo bash fix_deployment.sh
```

**특징**:
- 서비스 경로 자동 수정
- 로그 위치 자동 설정
- 최신 코드 동기화
- 서비스 재시작
- 전체 검증

**실행 시간**: 약 30초

---

### 2. `restart.sh` ⚡ **가장 빠름**

**용도**: 빠른 재시작 및 검증

```bash
bash restart.sh
```

**특징**:
- Git pull
- 프로세스 종료
- 재시작
- 초기 로그 표시

**실행 시간**: 약 10초

---

### 3. `deploy_service.sh` 🔧 **서비스 설치**

**용도**: Systemd 서비스 최초 설치 또는 재배포

```bash
sudo bash deploy_service.sh
```

**특징**:
- 서비스 파일 생성
- 올바른 경로 설정
- 자동 시작 활성화

**실행 시간**: 약 20초

---

### 4. `diagnose_service.sh` 🔍 **진단 전용**

**용도**: 현재 상태 전체 진단 (수정하지 않음)

```bash
bash diagnose_service.sh
```

**특징**:
- 시스템 상태 보고서 생성
- 문제 식별
- 해결 방법 제안

**실행 시간**: 약 5초

---

## 📋 상황별 사용 가이드

### 상황 1: 처음 배포하는 경우

```bash
cd ~/ai-dropship-final
git clone https://github.com/staylogwork-maker/ai-dropship-final.git
cd ai-dropship-final
sudo bash deploy_service.sh
```

---

### 상황 2: 코드를 업데이트했고 빠르게 반영하고 싶은 경우

```bash
cd ~/ai-dropship-final
bash restart.sh
```

---

### 상황 3: 서비스가 이상하게 작동하는 경우

```bash
cd ~/ai-dropship-final
sudo bash fix_deployment.sh
```

---

### 상황 4: 문제 원인을 파악하고 싶은 경우

```bash
cd ~/ai-dropship-final
bash diagnose_service.sh > report.txt
cat report.txt
```

---

## 🔍 서비스 경로 설정 확인법

### 방법 1: 서비스 파일 직접 확인 ⭐

```bash
sudo cat /etc/systemd/system/webapp.service
```

**확인 포인트**:
```ini
WorkingDirectory=/home/user/ai-dropship-final
ExecStart=/usr/bin/python3 /home/user/ai-dropship-final/app.py
StandardOutput=append:/home/user/ai-dropship-final/logs/server.log
StandardError=append:/home/user/ai-dropship-final/logs/server.log
```

---

### 방법 2: 실행 중인 프로세스 확인

```bash
ps aux | grep "python.*app.py"
```

**예상 출력**:
```
user  12345  0.5  2.1  ... python3 /home/user/ai-dropship-final/app.py
```

**프로세스 작업 디렉토리 확인**:
```bash
PID=$(pgrep -f "python.*app.py" | head -1)
sudo ls -l /proc/$PID/cwd
```

**예상 출력**:
```
lrwxrwxrwx 1 user user 0 Jan 21 10:30 /proc/12345/cwd -> /home/user/ai-dropship-final
```

---

### 방법 3: 로그에서 확인

```bash
grep "Database path:" ~/ai-dropship-final/logs/server.log | tail -1
```

**예상 출력**:
```
[INIT] Database path: /home/user/ai-dropship-final/dropship.db
```

---

### 방법 4: 진단 스크립트로 한 번에 확인 ⭐

```bash
cd ~/ai-dropship-final
bash diagnose_service.sh | grep -A2 "SERVICE CONFIGURATION"
```

---

## ✅ 배포 성공 검증

다음 명령어로 모든 것이 정상인지 확인:

```bash
cd ~/ai-dropship-final && \
echo "=== Git Commit ===" && \
git log -1 --oneline && \
echo -e "\n=== Service Status ===" && \
sudo systemctl is-active webapp && \
echo -e "\n=== Working Directory ===" && \
PID=$(pgrep -f "python.*app.py" | head -1) && \
sudo readlink /proc/$PID/cwd && \
echo -e "\n=== DB Init Marker ===" && \
grep "DATABASE INITIALIZATION COMPLETE" logs/server.log | tail -1 && \
echo -e "\n✅✅✅ ALL CHECKS PASSED! ✅✅✅"
```

---

## 🐛 문제 해결

### 문제 1: "Permission denied" 에러

**해결**:
```bash
chmod +x ~/ai-dropship-final/*.sh
```

---

### 문제 2: 로그에 여전히 구버전 코드의 흔적

**해결**:
```bash
cd ~/ai-dropship-final
rm logs/server.log
sudo bash fix_deployment.sh
```

---

### 문제 3: 서비스가 시작되지 않음

**진단**:
```bash
sudo systemctl status webapp
sudo journalctl -u webapp -n 50
```

**해결**:
```bash
cd ~/ai-dropship-final
sudo bash fix_deployment.sh
```

---

### 문제 4: DB 테이블이 없다는 에러

**해결**:
```bash
cd ~/ai-dropship-final
rm dropship.db
sudo systemctl restart webapp
tail -f logs/server.log
```

---

## 📊 체크리스트

배포 후 다음을 확인하세요:

- [ ] `git log -1` 커밋이 `22a7493` 이상
- [ ] `sudo systemctl is-active webapp` → `active`
- [ ] 프로세스 작업 디렉토리가 `/home/user/ai-dropship-final`
- [ ] 로그에 "DATABASE INITIALIZATION COMPLETE" 마커 존재
- [ ] 웹 브라우저에서 대시보드 접속 가능
- [ ] AI 소싱 기능 정상 작동

---

## 🚀 빠른 참조

| 명령어 | 용도 | 실행 시간 |
|--------|------|-----------|
| `sudo bash fix_deployment.sh` | 모든 문제 해결 | ~30초 |
| `bash restart.sh` | 빠른 재시작 | ~10초 |
| `sudo bash deploy_service.sh` | 서비스 설치 | ~20초 |
| `bash diagnose_service.sh` | 진단만 | ~5초 |

---

## 📞 추가 지원

문제가 지속되면 진단 보고서를 생성하세요:

```bash
cd ~/ai-dropship-final
bash diagnose_service.sh > diagnosis.txt 2>&1
cat diagnosis.txt
```

---

## 📝 요약

**가장 확실한 해결책**:
```bash
cd ~/ai-dropship-final
sudo bash fix_deployment.sh
tail -f logs/server.log
```

로그에서 **"DATABASE INITIALIZATION COMPLETE"** 마커를 확인하세요!

**Repository**: https://github.com/staylogwork-maker/ai-dropship-final
