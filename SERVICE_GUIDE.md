# 서비스 배포 및 관리 가이드

## 🚨 **현재 문제 진단**

최신 코드를 Pull 했는데도 이전 버전이 실행되는 경우, 다음 원인이 있을 수 있습니다:

1. **다른 디렉토리에서 실행 중**: 서비스가 `/home/user/webapp` 대신 다른 경로에서 실행
2. **Systemd 서비스 설정 오류**: `WorkingDirectory`가 잘못 설정됨
3. **프로세스가 재시작되지 않음**: 기존 프로세스가 여전히 실행 중

---

## 📋 **진단 스크립트 실행**

### **1단계: 현재 상태 진단**

```bash
cd /home/user/webapp  # 또는 ~/ai-dropship-final
bash diagnose_service.sh
```

**이 스크립트가 확인하는 것:**
- ✅ 현재 작업 디렉토리
- ✅ Systemd 서비스 파일 존재 여부 및 내용
- ✅ 실행 중인 Flask 프로세스 및 그 위치
- ✅ Git 저장소 상태 및 커밋
- ✅ app.py 파일 및 최신 버전 확인
- ✅ 로그 파일 내용
- ✅ 데이터베이스 파일

**출력 예시:**
```
[1] Current Working Directory:
/home/user/webapp

[2] Checking for systemd service file...
✓ Found: /etc/systemd/system/webapp.service

[3] Checking for running Flask process...
✓ Flask process found (PID: 12345)
Working directory of process: /home/user/old-location  ← 문제 발견!

[5] Checking app.py...
✓ app.py exists in current directory
✓ DB initialization marker FOUND in app.py

[6] Checking log files...
⚠ Marker NOT FOUND in logs (old version running?)  ← 문제 확인!
```

---

## 🔧 **해결 방법**

### **방법 1: 빠른 재시작 (권장)**

```bash
cd /home/user/webapp  # 정확한 경로로 이동
bash restart.sh
```

**이 스크립트가 수행하는 작업:**
1. 최신 코드를 GitHub에서 Pull (`git reset --hard origin/main`)
2. 최신 버전인지 확인 (`DATABASE INITIALIZATION COMPLETE` 확인)
3. 기존 Flask 프로세스 종료
4. Systemd 서비스가 있으면 재시작, 없으면 수동 시작
5. 초기 로그 출력

---

### **방법 2: Systemd 서비스 재배포 (영구 수정)**

**Systemd 서비스를 사용하는 경우:**

```bash
cd /home/user/webapp  # 정확한 경로로 이동
sudo bash deploy_service.sh
```

**이 스크립트가 수행하는 작업:**
1. 기존 서비스 파일 백업
2. 올바른 `WorkingDirectory`로 새 서비스 파일 생성
3. 로그 디렉토리 생성
4. Virtual environment 확인
5. Systemd 데몬 리로드
6. 서비스 활성화

**생성되는 서비스 파일 예시:**
```ini
[Unit]
Description=AI Dropshipping ERP System
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/home/user/webapp  ← 자동으로 현재 디렉토리로 설정
Environment="PATH=/home/user/webapp/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/user/webapp/venv/bin/python3 /home/user/webapp/app.py
Restart=always
RestartSec=10
StandardOutput=append:/home/user/webapp/logs/server.log
StandardError=append:/home/user/webapp/logs/server.log

[Install]
WantedBy=multi-user.target
```

---

## 📊 **서비스 관리 명령어**

### **Systemd 서비스 사용 시:**

```bash
# 서비스 시작
sudo systemctl start webapp

# 서비스 중지
sudo systemctl stop webapp

# 서비스 재시작
sudo systemctl restart webapp

# 서비스 상태 확인
sudo systemctl status webapp

# 실시간 로그 보기
sudo journalctl -u webapp -f

# 또는 직접 로그 파일 확인
tail -f /home/user/webapp/logs/server.log
```

### **수동 실행 시:**

```bash
cd /home/user/webapp

# 기존 프로세스 종료
pkill -9 -f "python.*app.py"

# 백그라운드 실행
python3 app.py > logs/server.log 2>&1 &

# 또는 가상환경 사용
source venv/bin/activate
python3 app.py > logs/server.log 2>&1 &

# 로그 확인
tail -f logs/server.log

# 프로세스 확인
ps aux | grep "python.*app.py"
```

---

## ✅ **최신 버전 확인 방법**

### **1. 로그에서 확인**

```bash
tail -50 logs/server.log | grep -E "(CRITICAL|DATABASE INITIALIZATION COMPLETE)"
```

**기대되는 출력:**
```
[CRITICAL] Starting database initialization...
[DB-VERIFY] ✅ All 8 required tables exist!
======================================================================
!!! DATABASE INITIALIZATION COMPLETE !!!
======================================================================
[CRITICAL] Database initialization finished. Proceeding with Flask setup...
```

### **2. 코드에서 확인**

```bash
grep -n "DATABASE INITIALIZATION COMPLETE" app.py
```

**기대되는 출력:**
```
283:    print('!!! DATABASE INITIALIZATION COMPLETE !!!')
```

### **3. Git 커밋 확인**

```bash
git log --oneline -1
```

**기대되는 출력:**
```
d6ba0b1 fix: Add comprehensive DB verification and completion markers
```

---

## 🎯 **문제별 해결 가이드**

### **문제 1: "로그에 마커가 없어요"**

**원인:** 이전 버전이 실행 중

**해결:**
```bash
cd /home/user/webapp
bash restart.sh
```

---

### **문제 2: "다른 디렉토리에서 실행되고 있어요"**

**원인:** Systemd 서비스의 `WorkingDirectory`가 잘못됨

**해결:**
```bash
cd /home/user/webapp  # 올바른 디렉토리로 이동
sudo bash deploy_service.sh  # 서비스 재설정
```

---

### **문제 3: "코드를 Pull 했는데도 변경이 없어요"**

**원인:** Git이 다른 디렉토리를 보고 있거나, 프로세스가 재시작 안 됨

**해결:**
```bash
# 1. 올바른 디렉토리인지 확인
pwd
ls -la app.py

# 2. Git 상태 확인
git status
git log --oneline -1

# 3. 강제로 최신 버전 가져오기
git fetch origin
git reset --hard origin/main

# 4. 프로세스 재시작
bash restart.sh
```

---

### **문제 4: "여전히 'no such table: users' 에러가 나요"**

**원인:** DB 파일이 손상되었거나 초기화가 실패함

**해결:**
```bash
cd /home/user/webapp

# 1. 기존 DB 삭제
rm dropship.db

# 2. 앱 재시작 (자동으로 DB 생성됨)
bash restart.sh

# 3. 로그 확인
tail -f logs/server.log
# "!!! DATABASE INITIALIZATION COMPLETE !!!" 확인
```

---

## 📝 **체크리스트**

배포 전 확인 사항:

- [ ] 올바른 디렉토리에 있는가? (`pwd` 확인)
- [ ] 최신 코드를 Pull 했는가? (`git log -1` 확인)
- [ ] app.py에 마커가 있는가? (`grep "DATABASE INITIALIZATION COMPLETE" app.py`)
- [ ] 기존 프로세스를 종료했는가? (`pkill -9 -f "python.*app.py"`)
- [ ] 로그에 마커가 나타나는가? (`tail -f logs/server.log`)

---

## 🚀 **권장 배포 프로세스**

```bash
# 1. 올바른 디렉토리로 이동
cd /home/user/webapp  # 또는 ~/ai-dropship-final

# 2. 진단 실행
bash diagnose_service.sh

# 3. 문제가 발견되면 restart 스크립트 실행
bash restart.sh

# 4. 로그 확인
tail -f logs/server.log

# 5. 브라우저에서 확인
# http://your-server-ip:5000
```

---

## 📞 **추가 도움말**

각 스크립트는 상세한 출력을 제공합니다. 문제가 계속되면:

1. `diagnose_service.sh` 출력 전체를 캡처
2. `logs/server.log` 마지막 100줄을 확인
3. `systemctl status webapp` 출력 확인

이 정보로 정확한 문제를 파악할 수 있습니다.
