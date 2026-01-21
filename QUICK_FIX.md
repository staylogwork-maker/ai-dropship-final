# ⚡ 빠른 해결 가이드

## 🎯 현재 문제
최신 커밋(d6ba0b1 → 8babf3d) 배포했으나 로그에 DB 검증 마커가 안 보임

---

## 🚨 즉시 실행 (서버에서)

### 1분 해결책:

```bash
# 1. 디렉토리 이동
cd ~/ai-dropship-final

# 2. 최신 코드 가져오기
git fetch origin && git reset --hard origin/main

# 3. 커밋 확인 (8babf3d 여야 함)
git log -1 --oneline

# 4. 빠른 재시작
bash restart.sh
```

---

## ✅ 성공 확인

로그에서 다음을 확인:

```bash
tail -f logs/server.log
```

**찾아야 할 마커**:
```
[CRITICAL] Starting database initialization...
[DB-VERIFY] ✅ All 8 required tables exist
!!! DATABASE INITIALIZATION COMPLETE !!!
```

---

## 🔧 여전히 안 되면

### 옵션 A: 서비스 재배포

```bash
cd ~/ai-dropship-final
sudo bash deploy_service.sh
```

### 옵션 B: 진단 실행

```bash
cd ~/ai-dropship-final
bash diagnose_service.sh
```

---

## 📞 서비스 경로 확인법

```bash
# 방법 1: 서비스 파일 확인
sudo cat /etc/systemd/system/webapp.service | grep -E "(WorkingDirectory|ExecStart)"

# 방법 2: 실행 중인 프로세스 확인
ps aux | grep "python.*app.py"

# 방법 3: 로그에서 DB 경로 확인
grep "Database path:" logs/server.log | tail -1
```

**올바른 경로**: `/home/user/ai-dropship-final`

---

## 💡 최종 검증

```bash
# 모든 것이 정상인지 한 번에 확인
cd ~/ai-dropship-final && \
echo "=== Git Commit ===" && git log -1 --oneline && \
echo -e "\n=== Service Status ===" && sudo systemctl status webapp | head -5 && \
echo -e "\n=== DB Path ===" && grep "Database path:" logs/server.log | tail -1 && \
echo -e "\n=== Init Complete ===" && grep "INITIALIZATION COMPLETE" logs/server.log | tail -1
```

---

## 📋 체크리스트

- [ ] 커밋: `8babf3d`
- [ ] 서비스 경로: `/home/user/ai-dropship-final`
- [ ] 로그 마커: "DATABASE INITIALIZATION COMPLETE"
- [ ] 웹 접속: 정상

---

**커밋**: 8babf3d  
**Repository**: https://github.com/staylogwork-maker/ai-dropship-final
