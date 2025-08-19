#!/bin/bash

# Polarization Interface Auto-Start Script
# Automatically detects IP address and starts the application with network accessibility

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to detect the primary IP address
detect_ip() {
    local detected_ip=""
    
    # Method 1: Use ip route (most reliable on Linux)
    if command -v ip >/dev/null 2>&1; then
        detected_ip=$(ip route get 8.8.8.8 2>/dev/null | awk '{print $7; exit}' 2>/dev/null || echo "")
    fi
    
    # Method 2: Use hostname -I (fallback)
    if [ -z "$detected_ip" ] && command -v hostname >/dev/null 2>&1; then
        detected_ip=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "")
    fi
    
    # Method 3: Use ifconfig (macOS/older systems)
    if [ -z "$detected_ip" ] && command -v ifconfig >/dev/null 2>&1; then
        detected_ip=$(ifconfig | grep -E 'inet.*192\.168\.|inet.*10\.|inet.*172\.' | head -1 | awk '{print $2}' | sed 's/addr://' || echo "")
    fi
    
    # Validate IP format
    if [[ $detected_ip =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        echo "$detected_ip"
    else
        echo ""
    fi
}

# Function to show usage
show_usage() {
    echo "Polarization Interface Startup Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --host IP_ADDRESS    Use specific IP address (e.g., --host 192.168.1.100)"
    echo "  --localhost          Force localhost mode (development only)"
    echo "  --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                           # Auto-detect IP and start"
    echo "  $0 --host 192.168.1.100     # Use specific IP address"
    echo "  $0 --localhost              # Development mode (localhost only)"
    echo ""
}

# Parse command line arguments
BACKEND_HOST=""
FORCE_LOCALHOST=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            BACKEND_HOST="$2"
            shift 2
            ;;
        --localhost)
            FORCE_LOCALHOST=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

echo "🚀 Polarization Interface Startup"
echo "=================================="

# Determine backend host
if [ "$FORCE_LOCALHOST" = true ]; then
    BACKEND_HOST="localhost"
    print_info "Using localhost mode (development only)"
elif [ -n "$BACKEND_HOST" ]; then
    print_info "Using manually specified host: $BACKEND_HOST"
else
    print_info "Auto-detecting network configuration..."
    
    DETECTED_IP=$(detect_ip)
    
    if [ -n "$DETECTED_IP" ]; then
        BACKEND_HOST="$DETECTED_IP"
        print_success "Detected IP address: $BACKEND_HOST"
    else
        print_warning "Could not detect IP address, falling back to localhost"
        BACKEND_HOST="localhost"
    fi
fi

# Validate Docker and Docker Compose
if ! command -v docker >/dev/null 2>&1; then
    print_error "Docker is not installed or not in PATH"
    exit 1
fi

if ! command -v docker-compose >/dev/null 2>&1; then
    print_error "Docker Compose is not installed or not in PATH"
    exit 1
fi

# Set environment variables and start
export BACKEND_HOST

# Set CORS origins to include the frontend URL
export CORS_ALLOW_ORIGINS="http://$BACKEND_HOST:8085"

print_info "Backend host: $BACKEND_HOST"
print_info "Frontend will be accessible at: http://$BACKEND_HOST:8085"
print_info "Backend API will be accessible at: http://$BACKEND_HOST:8000"
print_info "CORS configured for: $CORS_ALLOW_ORIGINS"

echo ""
print_info "Starting containers..."

# Run docker-compose
docker-compose down
if docker-compose up --build -d; then
    print_success "Application started successfully!"
else
    print_error "Failed to start application"
    exit 1
fi
