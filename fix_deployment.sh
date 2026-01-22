#!/bin/bash

################################################################################
# 🚨 긴급 배포 수정 스크립트
# 용도: 서비스 경로, 로그 위치, 환경 동기화 문제를 한 번에 해결
# 사용법: sudo bash fix_deployment.sh
################################################################################

set -e  # 에러 발생 시 즉시 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 배너 출력
echo "============================================================"
echo "🚨 긴급 배포 수정 스크립트"
echo "============================================================"
echo ""

# Step 1: 작업 디렉토리 확인
log_info "Step 1: 작업 디렉토리 확인 중..."
TARGET_DIR="$HOME/ai-dropship-final"

if [ ! -d "$TARGET_DIR" ]; then
    log_error "디렉토리를 찾을 수 없습니다: $TARGET_DIR"
    exit 1
fi

cd "$TARGET_DIR"
log_success "작업 디렉토리: $(pwd)"
echo ""

# Step 2: 최신 코드 동기화
log_info "Step 2: GitHub에서 최신 코드 가져오기..."
git fetch origin
BEFORE_COMMIT=$(git rev-parse --short HEAD)
log_info "현재 커밋: $BEFORE_COMMIT"

git reset --hard origin/main
AFTER_COMMIT=$(git rev-parse --short HEAD)
log_success "최신 커밋: $AFTER_COMMIT"

if [ "$BEFORE_COMMIT" != "$AFTER_COMMIT" ]; then
    log_warning "코드가 업데이트되었습니다: $BEFORE_COMMIT → $AFTER_COMMIT"
else
    log_info "이미 최신 코드입니다."
fi
echo ""

# Step 3: DB 검증 마커 확인
log_info "Step 3: DB 검증 마커 존재 확인..."
if grep -q "DATABASE INITIALIZATION COMPLETE" app.py; then
    log_success "✅ DB 검증 마커 발견: app.py에 최신 코드 포함"
else
    log_error "❌ DB 검증 마커 없음: app.py가 구버전일 수 있음"
    log_warning "git pull을 다시 시도하거나 app.py를 확인하세요."
fi
echo ""

# Step 4: 서비스 파일 확인 및 수정
log_info "Step 4: Systemd 서비스 파일 확인 및 수정..."
SERVICE_FILE="/etc/systemd/system/webapp.service"

if [ ! -f "$SERVICE_FILE" ]; then
    log_warning "서비스 파일이 없습니다. 새로 생성합니다..."
    
    # 서비스 파일 생성
    cat > /tmp/webapp.service <<EOF
[Unit]
Description=AI Dropshipping ERP System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$TARGET_DIR
ExecStart=/usr/bin/python3 $TARGET_DIR/app.py
Restart=always
RestartSec=3
StandardOutput=append:$TARGET_DIR/logs/server.log
StandardError=append:$TARGET_DIR/logs/server.log
Environment=FLASK_SECRET_KEY=production-secret-key-change-me

[Install]
WantedBy=multi-user.target
EOF
    
    sudo mv /tmp/webapp.service "$SERVICE_FILE"
    sudo chmod 644 "$SERVICE_FILE"
    log_success "새 서비스 파일 생성: $SERVICE_FILE"
else
    log_info "기존 서비스 파일 발견. 경로 확인 중..."
    
    # 현재 설정 확인
    CURRENT_WORKING_DIR=$(grep "^WorkingDirectory=" "$SERVICE_FILE" | cut -d= -f2)
    CURRENT_EXEC_START=$(grep "^ExecStart=" "$SERVICE_FILE" | cut -d= -f2-)
    
    log_info "현재 WorkingDirectory: $CURRENT_WORKING_DIR"
    log_info "현재 ExecStart: $CURRENT_EXEC_START"
    
    # 경로가 틀리면 수정
    if [[ "$CURRENT_WORKING_DIR" != "$TARGET_DIR" ]] || [[ ! "$CURRENT_EXEC_START" =~ "$TARGET_DIR/app.py" ]]; then
        log_warning "서비스 파일 경로가 올바르지 않습니다. 수정합니다..."
        
        # 백업
        sudo cp "$SERVICE_FILE" "${SERVICE_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        
        # 새 서비스 파일 생성
        cat > /tmp/webapp.service <<EOF
[Unit]
Description=AI Dropshipping ERP System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$TARGET_DIR
ExecStart=/usr/bin/python3 $TARGET_DIR/app.py
Restart=always
RestartSec=3
StandardOutput=append:$TARGET_DIR/logs/server.log
StandardError=append:$TARGET_DIR/logs/server.log
Environment=FLASK_SECRET_KEY=production-secret-key-change-me

[Install]
WantedBy=multi-user.target
EOF
        
        sudo mv /tmp/webapp.service "$SERVICE_FILE"
        sudo chmod 644 "$SERVICE_FILE"
        log_success "서비스 파일 경로 수정 완료"
    else
        log_success "✅ 서비스 파일 경로가 올바릅니다."
    fi
fi
echo ""

# Step 5: 로그 디렉토리 확인
log_info "Step 5: 로그 디렉토리 확인..."
LOG_DIR="$TARGET_DIR/logs"

if [ ! -d "$LOG_DIR" ]; then
    log_warning "로그 디렉토리가 없습니다. 생성합니다..."
    mkdir -p "$LOG_DIR"
    chmod 755 "$LOG_DIR"
    log_success "로그 디렉토리 생성: $LOG_DIR"
else
    log_success "✅ 로그 디렉토리 존재: $LOG_DIR"
fi

# 로그 파일 권한 확인
if [ -f "$LOG_DIR/server.log" ]; then
    chmod 644 "$LOG_DIR/server.log"
    log_info "로그 파일 권한 설정 완료"
fi
echo ""

# Step 6: 데이터베이스 확인
log_info "Step 6: 데이터베이스 확인..."
DB_FILE="$TARGET_DIR/dropship.db"

if [ -f "$DB_FILE" ]; then
    log_success "✅ 데이터베이스 파일 존재: $DB_FILE"
    
    # 테이블 확인
    TABLE_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';" 2>/dev/null || echo "0")
    log_info "테이블 수: $TABLE_COUNT"
    
    if [ "$TABLE_COUNT" -lt 8 ]; then
        log_warning "필수 테이블이 부족합니다. 앱 시작 시 자동 생성됩니다."
    fi
else
    log_warning "데이터베이스 파일이 없습니다. 앱 시작 시 자동 생성됩니다."
fi
echo ""

# Step 7: Systemd 데몬 리로드
log_info "Step 7: Systemd 데몬 리로드..."
sudo systemctl daemon-reload
log_success "데몬 리로드 완료"
echo ""

# Step 8: 기존 프로세스 종료
log_info "Step 8: 기존 Flask 프로세스 종료..."
FLASK_PIDS=$(pgrep -f "python.*app.py" || true)

if [ -n "$FLASK_PIDS" ]; then
    log_info "종료할 프로세스: $FLASK_PIDS"
    sudo pkill -9 -f "python.*app.py" || true
    sleep 2
    log_success "기존 프로세스 종료 완료"
else
    log_info "실행 중인 Flask 프로세스 없음"
fi
echo ""

# Step 9: 서비스 재시작
log_info "Step 9: 서비스 재시작..."
sudo systemctl enable webapp
sudo systemctl restart webapp
sleep 3
log_success "서비스 재시작 완료"
echo ""

# Step 10: 상태 확인
log_info "Step 10: 서비스 상태 확인..."
if sudo systemctl is-active --quiet webapp; then
    log_success "✅ 서비스가 정상적으로 실행 중입니다!"
    
    # PID 확인
    FLASK_PID=$(pgrep -f "python.*app.py" | head -1)
    if [ -n "$FLASK_PID" ]; then
        log_info "Flask PID: $FLASK_PID"
        
        # 작업 디렉토리 확인
        PROC_CWD=$(sudo readlink /proc/$FLASK_PID/cwd 2>/dev/null || echo "unknown")
        log_info "프로세스 작업 디렉토리: $PROC_CWD"
        
        if [ "$PROC_CWD" = "$TARGET_DIR" ]; then
            log_success "✅ 프로세스가 올바른 디렉토리에서 실행 중입니다!"
        else
            log_warning "⚠️  프로세스가 다른 디렉토리에서 실행 중입니다: $PROC_CWD"
        fi
    fi
else
    log_error "❌ 서비스 시작 실패!"
    log_info "상태 확인: sudo systemctl status webapp"
fi
echo ""

# Step 11: 로그 확인
log_info "Step 11: 로그 확인 (최근 20줄)..."
echo "============================================================"
if [ -f "$LOG_DIR/server.log" ]; then
    tail -20 "$LOG_DIR/server.log"
else
    log_warning "로그 파일을 찾을 수 없습니다: $LOG_DIR/server.log"
    log_info "Systemd 로그 확인: sudo journalctl -u webapp -n 20"
fi
echo "============================================================"
echo ""

# Step 12: 검증 마커 확인
log_info "Step 12: DB 검증 마커 확인..."
if [ -f "$LOG_DIR/server.log" ]; then
    if grep -q "DATABASE INITIALIZATION COMPLETE" "$LOG_DIR/server.log"; then
        log_success "✅✅✅ DB 검증 마커 발견! 최신 코드가 정상 실행되었습니다!"
    else
        log_warning "⚠️  DB 검증 마커가 로그에 없습니다."
        log_info "다음 명령어로 실시간 로그 확인: tail -f $LOG_DIR/server.log"
    fi
else
    log_warning "로그 파일이 아직 생성되지 않았습니다. 잠시 후 다시 확인하세요."
fi
echo ""

# 최종 요약
echo "============================================================"
echo "✅ 배포 수정 완료!"
echo "============================================================"
echo ""
log_success "최신 커밋: $AFTER_COMMIT"
log_success "작업 디렉토리: $TARGET_DIR"
log_success "로그 파일: $LOG_DIR/server.log"
echo ""
echo "📋 다음 명령어로 실시간 로그 확인:"
echo "   tail -f $LOG_DIR/server.log"
echo ""
echo "📋 서비스 상태 확인:"
echo "   sudo systemctl status webapp"
echo ""
echo "📋 진단 스크립트 실행:"
echo "   cd $TARGET_DIR && bash diagnose_service.sh"
echo ""
echo "============================================================"
