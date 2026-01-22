#!/bin/bash

################################################################################
# 🚨 긴급 배포 수정 스크립트 v2.0
# 용도: 서비스 경로, 로그 위치, 환경 동기화 문제를 한 번에 해결
# 사용법: sudo bash fix_deployment.sh
# 또는:   bash fix_deployment.sh (자동으로 sudo 권한 확인)
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
echo "🚨 긴급 배포 수정 스크립트 v2.0"
echo "============================================================"
echo ""

# ============================================================================
# Step 0: 경로 및 사용자 정보 동적 감지
# ============================================================================
log_info "Step 0: 환경 정보 감지 중..."

# 스크립트가 실행된 실제 디렉토리 감지
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
log_info "스크립트 위치: $SCRIPT_DIR"

# 실제 사용자 감지 (sudo로 실행되어도 원래 사용자 파악)
if [ -n "$SUDO_USER" ]; then
    REAL_USER="$SUDO_USER"
    REAL_HOME=$(eval echo ~$SUDO_USER)
else
    REAL_USER="$USER"
    REAL_HOME="$HOME"
fi

log_info "실행 사용자: $REAL_USER"
log_info "사용자 홈: $REAL_HOME"

# 작업 디렉토리 결정 (우선순위: 1. 스크립트 위치, 2. 현재 위치, 3. 홈 디렉토리)
if [ -f "$SCRIPT_DIR/app.py" ]; then
    TARGET_DIR="$SCRIPT_DIR"
    log_success "✅ 작업 디렉토리: $TARGET_DIR (스크립트 위치)"
elif [ -f "$(pwd)/app.py" ]; then
    TARGET_DIR="$(pwd)"
    log_success "✅ 작업 디렉토리: $TARGET_DIR (현재 위치)"
elif [ -d "$REAL_HOME/ai-dropship-final" ]; then
    TARGET_DIR="$REAL_HOME/ai-dropship-final"
    log_warning "⚠️  작업 디렉토리: $TARGET_DIR (사용자 홈)"
else
    log_error "❌ ai-dropship-final 디렉토리를 찾을 수 없습니다!"
    log_error "다음 위치를 확인했습니다:"
    log_error "  - 스크립트 위치: $SCRIPT_DIR"
    log_error "  - 현재 위치: $(pwd)"
    log_error "  - 사용자 홈: $REAL_HOME/ai-dropship-final"
    echo ""
    log_info "💡 해결 방법: ai-dropship-final 디렉토리로 이동한 후 실행하세요"
    log_info "   cd ~/ai-dropship-final && sudo bash fix_deployment.sh"
    exit 1
fi

cd "$TARGET_DIR"
log_success "작업 디렉토리 변경 완료: $(pwd)"
echo ""

# ============================================================================
# Step 1: app.py 존재 확인 (git pull 전 초기 검증)
# ============================================================================
log_info "Step 1: app.py 파일 존재 확인..."

if [ ! -f "$TARGET_DIR/app.py" ]; then
    log_error "❌ app.py 파일을 찾을 수 없습니다: $TARGET_DIR/app.py"
    log_error "현재 디렉토리가 올바른 프로젝트 디렉토리인지 확인하세요."
    exit 1
fi

log_success "✅ app.py 파일 발견: $TARGET_DIR/app.py"
echo ""

# ============================================================================
# Step 2: 최신 코드 동기화
# ============================================================================
log_info "Step 2: GitHub에서 최신 코드 가져오기..."

# Git 사용자 확인 (sudo 실행 시에도 원래 사용자 권한으로 git 실행)
if [ -n "$SUDO_USER" ]; then
    log_info "Git 명령을 $REAL_USER 권한으로 실행합니다..."
    GIT_CMD="sudo -u $REAL_USER git"
else
    GIT_CMD="git"
fi

$GIT_CMD fetch origin
BEFORE_COMMIT=$($GIT_CMD rev-parse --short HEAD)
log_info "현재 커밋: $BEFORE_COMMIT"

$GIT_CMD reset --hard origin/main
AFTER_COMMIT=$($GIT_CMD rev-parse --short HEAD)
log_success "최신 커밋: $AFTER_COMMIT"

if [ "$BEFORE_COMMIT" != "$AFTER_COMMIT" ]; then
    log_warning "코드가 업데이트되었습니다: $BEFORE_COMMIT → $AFTER_COMMIT"
else
    log_info "이미 최신 코드입니다."
fi
echo ""

# ============================================================================
# Step 3: app.py 존재 재확인 (git pull 후 최종 검증)
# ============================================================================
log_info "Step 3: 코드 업데이트 후 app.py 재확인..."

if [ ! -f "$TARGET_DIR/app.py" ]; then
    log_error "❌ git pull 후에도 app.py 파일이 없습니다!"
    log_error "GitHub 리포지토리 상태를 확인하세요."
    exit 1
fi

log_success "✅ app.py 파일 확인 완료: $TARGET_DIR/app.py"

# 파일 크기도 확인
APP_PY_SIZE=$(stat -f%z "$TARGET_DIR/app.py" 2>/dev/null || stat -c%s "$TARGET_DIR/app.py" 2>/dev/null || echo "unknown")
log_info "app.py 파일 크기: $APP_PY_SIZE bytes"
echo ""

# ============================================================================
# Step 4: DB 검증 마커 확인
# ============================================================================
log_info "Step 4: DB 검증 마커 존재 확인..."

if grep -q "DATABASE INITIALIZATION COMPLETE" "$TARGET_DIR/app.py"; then
    log_success "✅ DB 검증 마커 발견: app.py에 최신 코드 포함"
else
    log_error "❌ DB 검증 마커 없음: app.py가 구버전일 수 있음"
    log_warning "git pull을 다시 시도하거나 app.py를 확인하세요."
fi
echo ""

# ============================================================================
# Step 5: 서비스 파일 확인 및 수정
# ============================================================================
log_info "Step 5: Systemd 서비스 파일 확인 및 수정..."
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
User=$REAL_USER
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
    CURRENT_USER=$(grep "^User=" "$SERVICE_FILE" | cut -d= -f2)
    
    log_info "현재 User: $CURRENT_USER"
    log_info "현재 WorkingDirectory: $CURRENT_WORKING_DIR"
    log_info "현재 ExecStart: $CURRENT_EXEC_START"
    
    # 경로나 사용자가 틀리면 수정
    NEEDS_UPDATE=0
    if [[ "$CURRENT_USER" != "$REAL_USER" ]]; then
        log_warning "⚠️  User가 올바르지 않습니다: $CURRENT_USER → $REAL_USER"
        NEEDS_UPDATE=1
    fi
    if [[ "$CURRENT_WORKING_DIR" != "$TARGET_DIR" ]]; then
        log_warning "⚠️  WorkingDirectory가 올바르지 않습니다"
        NEEDS_UPDATE=1
    fi
    if [[ ! "$CURRENT_EXEC_START" =~ "$TARGET_DIR/app.py" ]]; then
        log_warning "⚠️  ExecStart가 올바르지 않습니다"
        NEEDS_UPDATE=1
    fi
    
    if [ $NEEDS_UPDATE -eq 1 ]; then
        log_warning "서비스 파일을 수정합니다..."
        
        # 백업
        sudo cp "$SERVICE_FILE" "${SERVICE_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        log_info "백업 생성: ${SERVICE_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        
        # 새 서비스 파일 생성
        cat > /tmp/webapp.service <<EOF
[Unit]
Description=AI Dropshipping ERP System
After=network.target

[Service]
Type=simple
User=$REAL_USER
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
        log_success "✅ 서비스 파일 수정 완료"
    else
        log_success "✅ 서비스 파일이 이미 올바릅니다."
    fi
fi
echo ""

# ============================================================================
# Step 6: 로그 디렉토리 확인
# ============================================================================
log_info "Step 6: 로그 디렉토리 확인..."
LOG_DIR="$TARGET_DIR/logs"

if [ ! -d "$LOG_DIR" ]; then
    log_warning "로그 디렉토리가 없습니다. 생성합니다..."
    mkdir -p "$LOG_DIR"
    
    # sudo로 실행된 경우 원래 사용자 소유로 변경
    if [ -n "$SUDO_USER" ]; then
        chown -R "$REAL_USER:$REAL_USER" "$LOG_DIR"
    fi
    
    chmod 755 "$LOG_DIR"
    log_success "로그 디렉토리 생성: $LOG_DIR"
else
    log_success "✅ 로그 디렉토리 존재: $LOG_DIR"
fi

# 로그 파일 권한 확인
if [ -f "$LOG_DIR/server.log" ]; then
    # sudo로 실행된 경우 원래 사용자 소유로 변경
    if [ -n "$SUDO_USER" ]; then
        chown "$REAL_USER:$REAL_USER" "$LOG_DIR/server.log"
    fi
    chmod 644 "$LOG_DIR/server.log"
    log_info "로그 파일 권한 설정 완료"
fi
echo ""

# ============================================================================
# Step 7: 데이터베이스 확인
# ============================================================================
log_info "Step 7: 데이터베이스 확인..."
DB_FILE="$TARGET_DIR/dropship.db"

if [ -f "$DB_FILE" ]; then
    log_success "✅ 데이터베이스 파일 존재: $DB_FILE"
    
    # 테이블 확인 (sqlite3가 설치된 경우만)
    if command -v sqlite3 &> /dev/null; then
        TABLE_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';" 2>/dev/null || echo "0")
        log_info "테이블 수: $TABLE_COUNT"
        
        if [ "$TABLE_COUNT" -lt 8 ]; then
            log_warning "필수 테이블이 부족합니다. 앱 시작 시 자동 생성됩니다."
        fi
    else
        log_warning "sqlite3가 설치되지 않아 테이블 확인을 건너뜁니다."
    fi
else
    log_warning "데이터베이스 파일이 없습니다. 앱 시작 시 자동 생성됩니다."
fi
echo ""

# ============================================================================
# Step 8: Systemd 데몬 리로드
# ============================================================================
log_info "Step 8: Systemd 데몬 리로드..."
sudo systemctl daemon-reload
log_success "데몬 리로드 완료"
echo ""

# ============================================================================
# Step 9: 기존 프로세스 종료
# ============================================================================
log_info "Step 9: 기존 Flask 프로세스 종료..."
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

# ============================================================================
# Step 10: 서비스 재시작
# ============================================================================
log_info "Step 10: 서비스 재시작..."
sudo systemctl enable webapp
sudo systemctl restart webapp
sleep 3
log_success "서비스 재시작 완료"
echo ""

# ============================================================================
# Step 11: 상태 확인
# ============================================================================
log_info "Step 11: 서비스 상태 확인..."
if sudo systemctl is-active --quiet webapp; then
    log_success "✅ 서비스가 정상적으로 실행 중입니다!"
    
    # PID 확인
    FLASK_PID=$(pgrep -f "python.*app.py" | head -1)
    if [ -n "$FLASK_PID" ]; then
        log_info "Flask PID: $FLASK_PID"
        
        # 작업 디렉토리 확인
        if [ -e "/proc/$FLASK_PID/cwd" ]; then
            PROC_CWD=$(sudo readlink /proc/$FLASK_PID/cwd 2>/dev/null || echo "unknown")
            log_info "프로세스 작업 디렉토리: $PROC_CWD"
            
            if [ "$PROC_CWD" = "$TARGET_DIR" ]; then
                log_success "✅ 프로세스가 올바른 디렉토리에서 실행 중입니다!"
            else
                log_warning "⚠️  프로세스가 다른 디렉토리에서 실행 중입니다: $PROC_CWD"
            fi
        else
            log_warning "프로세스 정보를 읽을 수 없습니다."
        fi
    fi
else
    log_error "❌ 서비스 시작 실패!"
    log_info "상태 확인: sudo systemctl status webapp"
    log_info "로그 확인: sudo journalctl -u webapp -n 50"
fi
echo ""

# ============================================================================
# Step 12: 로그 확인
# ============================================================================
log_info "Step 12: 로그 확인 (최근 20줄)..."
echo "============================================================"
if [ -f "$LOG_DIR/server.log" ]; then
    tail -20 "$LOG_DIR/server.log"
else
    log_warning "로그 파일을 찾을 수 없습니다: $LOG_DIR/server.log"
    log_info "Systemd 로그 확인: sudo journalctl -u webapp -n 20"
fi
echo "============================================================"
echo ""

# ============================================================================
# Step 13: 검증 마커 확인
# ============================================================================
log_info "Step 13: DB 검증 마커 확인..."
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

# ============================================================================
# 최종 요약
# ============================================================================
echo "============================================================"
echo "✅ 배포 수정 완료!"
echo "============================================================"
echo ""
log_success "실행 사용자: $REAL_USER"
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
