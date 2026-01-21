# 🚀 서비스 경로 설정 확인 및 배포 가이드

## 📌 최신 커밋: 8babf3d

---

## ✅ 1단계: 현재 상태 진단

서버에서 다음 명령어를 실행하여 현재 상태를 확인하세요:

```bash
cd ~/ai-dropship-final
bash diagnose_service.sh
```

### 진단 스크립트가 확인하는 항목:

1. **현재 작업 디렉토리**: 스크립트 실행 위치
2. **Systemd 서비스 파일**: `/etc/systemd/system/webapp.service` 존재 여부 및 설정
3. **실행 중인 Flask 프로세스**: PID, 작업 디렉토리, 실행 명령어
4. **Git 상태**: 현재 브랜치, 최신 커밋, 추적되지 않은 변경사항
5. **app.py 버전**: DB 검증 마커 존재 여부
6. **로그 파일 위치**: logs/server.log, /var/log/server.log
7. **데이터베이스 상태**: dropship.db 존재 여부 및 테이블 목록

### 예상 출력:

```
========================================
SYSTEM DIAGNOSIS REPORT
========================================

[✓] Current working directory: /home/user/ai-dropship-final
[✓] Systemd service file: /etc/systemd/system/webapp.service
[✓] Flask process running: PID 12345
[✓] Git commit: 8babf3d (feat: Add service deployment and diagnostic tools)
[✓] app.py contains DB verification markers
[✓] Database exists: /home/user/ai-dropship-final/dropship.db
[✓] All 8 required tables present
```

---

## ⚙️ 2단계: 서비스 경로 수정

### 옵션 A: 자동 배포 스크립트 사용 (권장)

```bash
cd ~/ai-dropship-final
sudo bash deploy_service.sh
```

이 스크립트는 자동으로:
- 기존 서비스 파일을 백업
- 올바른 경로로 새 서비스 파일 생성
- Systemd 데몬 리로드
- 서비스 활성화 및 시작

### 옵션 B: 수동 수정

1. **서비스 파일 확인**:
   ```bash
   sudo cat /etc/systemd/system/webapp.service
   ```

2. **올바른 경로인지 확인**:
   - `WorkingDirectory=/home/user/ai-dropship-final` (또는 `~/ai-dropship-final`)
   - `ExecStart=/usr/bin/python3 /home/user/ai-dropship-final/app.py`

3. **경로가 틀리면 수정**:
   ```bash
   sudo nano /etc/systemd/system/webapp.service
   ```

4. **변경사항 적용**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart webapp
   ```

---

## 🔄 3단계: 최신 코드 배포 및 재시작

### 빠른 재시작 (자동화 스크립트)

```bash
cd ~/ai-dropship-final
bash restart.sh
```

이 스크립트는 자동으로:
1. 최신 코드 Pull (`git reset --hard origin/main`)
2. 현재 커밋 확인
3. DB 검증 마커 존재 확인
4. 기존 Flask 프로세스 종료
5. 서비스 재시작 (systemd 또는 수동)
6. 초기 로그 출력

### 수동 재시작

```bash
# 1. 최신 코드 가져오기
cd ~/ai-dropship-final
git fetch origin
git reset --hard origin/main

# 2. 커밋 확인
git log -1

# 3. 기존 프로세스 종료
sudo pkill -9 -f "python.*app.py"

# 4. 서비스 재시작
sudo systemctl restart webapp

# 또는 수동 실행
python3 app.py
```

---

## 📋 4단계: 배포 검증

### 로그 확인

```bash
# 옵션 1: Flask 앱 로그
tail -f ~/ai-dropship-final/logs/server.log

# 옵션 2: Systemd 로그
sudo journalctl -u webapp -f

# 옵션 3: /var/log (서비스 설정에 따라)
tail -f /var/log/server.log
```

### ✅ 성공 시 보이는 마커들:

```
[INIT] Database path: /home/user/ai-dropship-final/dropship.db
[INIT] Base directory: /home/user/ai-dropship-final
[CRITICAL] Starting database initialization...
[DB-VERIFY] ✅ All 8 required tables exist: ['users', 'config', ...]
============================================================
!!! DATABASE INITIALIZATION COMPLETE !!!
============================================================
 * Serving Flask app 'app'
 * Debug mode: off
```

### ❌ 문제 발생 시:

1. **"no such table: users" 에러**:
   - DB 초기화가 실행되지 않음
   - 로그에 "DATABASE INITIALIZATION COMPLETE" 마커가 없음
   - 해결: `rm dropship.db && python3 app.py`

2. **이전 버전 코드 실행**:
   - `git log -1`로 커밋 확인 → `8babf3d`가 아니면 재배포
   - 서비스 파일 경로 확인 → 올바른 디렉토리를 가리키는지 검증

3. **로그 파일이 보이지 않음**:
   - `logs` 디렉토리 생성: `mkdir -p ~/ai-dropship-final/logs`
   - 권한 확인: `chmod 755 ~/ai-dropship-final/logs`

---

## 🔍 5단계: 서비스 경로 설정 확인법

### 방법 1: Systemd 서비스 파일 직접 확인

```bash
sudo cat /etc/systemd/system/webapp.service
```

**확인 포인트**:
```ini
[Service]
WorkingDirectory=/home/user/ai-dropship-final
ExecStart=/usr/bin/python3 /home/user/ai-dropship-final/app.py
```

### 방법 2: 실행 중인 프로세스 확인

```bash
# Flask 프로세스 찾기
ps aux | grep "python.*app.py"

# 프로세스의 작업 디렉토리 확인
PID=$(ps aux | grep "python.*app.py" | grep -v grep | awk '{print $2}' | head -1)
sudo ls -l /proc/$PID/cwd
```

**예상 출력**:
```
lrwxrwxrwx 1 user user 0 Jan 21 10:30 /proc/12345/cwd -> /home/user/ai-dropship-final
```

### 방법 3: Flask 로그에서 경로 확인

```bash
grep "Database path:" ~/ai-dropship-final/logs/server.log | tail -1
```

**예상 출력**:
```
2026-01-21 10:30:15 [INIT] Database path: /home/user/ai-dropship-final/dropship.db
```

### 방법 4: 진단 스크립트 사용

```bash
cd ~/ai-dropship-final
bash diagnose_service.sh | grep -E "(WorkingDirectory|ExecStart|cwd)"
```

---

## 📊 체크리스트

배포가 완료되면 다음 항목을 모두 확인하세요:

- [ ] `git log -1` → 커밋 `8babf3d` 확인
- [ ] `sudo cat /etc/systemd/system/webapp.service` → 경로 확인
- [ ] `ps aux | grep "python.*app.py"` → 프로세스 실행 확인
- [ ] `tail -f logs/server.log` → "DATABASE INITIALIZATION COMPLETE" 마커 확인
- [ ] `ls -l /proc/$(pidof python3)/cwd` → 작업 디렉토리 `/home/user/ai-dropship-final` 확인
- [ ] 웹 브라우저에서 대시보드 접속 → 로그인 성공 확인
- [ ] 소싱 기능 테스트 → "Blue Ocean Analysis" 정상 작동 확인

---

## 🛠 문제 해결 가이드

### 문제 1: 서비스 파일이 없음

```bash
cd ~/ai-dropship-final
sudo bash deploy_service.sh
```

### 문제 2: 권한 에러

```bash
sudo chown -R $USER:$USER ~/ai-dropship-final
chmod +x ~/ai-dropship-final/*.sh
```

### 문제 3: Git 충돌

```bash
cd ~/ai-dropship-final
git fetch origin
git reset --hard origin/main
git clean -fd
```

### 문제 4: 포트 이미 사용 중

```bash
sudo lsof -ti:5000 | xargs sudo kill -9
sudo systemctl restart webapp
```

### 문제 5: 가상환경 문제

```bash
cd ~/ai-dropship-final
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 📞 추가 지원

진단 스크립트를 실행한 후 출력 결과를 공유하시면 더 정확한 해결책을 제공할 수 있습니다:

```bash
cd ~/ai-dropship-final
bash diagnose_service.sh > diagnosis_report.txt 2>&1
cat diagnosis_report.txt
```

---

## 📝 요약

1. **진단**: `bash diagnose_service.sh`
2. **배포**: `sudo bash deploy_service.sh`
3. **재시작**: `bash restart.sh`
4. **검증**: 로그에서 "DATABASE INITIALIZATION COMPLETE" 확인
5. **확인**: 서비스 경로가 `~/ai-dropship-final`을 가리키는지 확인

**최신 커밋**: `8babf3d` - feat: Add service deployment and diagnostic tools

**Repository**: https://github.com/staylogwork-maker/ai-dropship-final

---

✅ **배포 완료 조건**:
- 커밋 `8babf3d` 실행 중
- 로그에 "DATABASE INITIALIZATION COMPLETE" 마커 표시
- 서비스가 `/home/user/ai-dropship-final` 디렉토리에서 실행
- 웹 대시보드 정상 접속
