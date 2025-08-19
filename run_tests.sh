#!/bin/bash

# Test Runner Script
# This script runs all tests for the polarization interface

echo "Running Polarization Interface Test Suite..."

# Function to print section headers
print_header() {
    echo ""
    echo "========================================"
    echo "$1"
    echo "========================================"
}

# Initialize test results
BACKEND_TESTS_PASSED=false
FRONTEND_TESTS_PASSED=false

# Activate virtual environment for backend tests
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Warning: Virtual environment not found. Some tests may fail."
fi

# Run backend tests
print_header "BACKEND TESTS"
cd src/backend

echo "Running ZMQ Client Tests..."
python -m pytest test_zmq_client.py -v
ZMQCLIENT_EXIT_CODE=$?

echo "Running API Tests..."
python -m pytest test_api.py -v
API_EXIT_CODE=$?

echo "Running Integration Tests..."
python -m pytest integration_tests.py -v
INTEGRATION_EXIT_CODE=$?

cd ../..

if [ $ZMQCLIENT_EXIT_CODE -eq 0 ] && [ $API_EXIT_CODE -eq 0 ] && [ $INTEGRATION_EXIT_CODE -eq 0 ]; then
    BACKEND_TESTS_PASSED=true
    echo "✅ All backend tests passed!"
else
    echo "❌ Some backend tests failed!"
fi

# Run frontend tests
print_header "FRONTEND TESTS"
cd src/frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Security audit check
print_header "FRONTEND SECURITY AUDIT"
echo "Running npm security audit..."
npm audit --audit-level=moderate
AUDIT_EXIT_CODE=$?
if [ $AUDIT_EXIT_CODE -eq 0 ]; then
    echo "✅ No moderate or high security vulnerabilities found!"
else
    echo "⚠️  Security vulnerabilities detected. Run 'npm audit' for details."
fi

echo "Running React Component Tests..."
npm test -- --watchAll=false --coverage
FRONTEND_EXIT_CODE=$?

cd ../..

if [ $FRONTEND_EXIT_CODE -eq 0 ]; then
    FRONTEND_TESTS_PASSED=true
    echo "✅ All frontend tests passed!"
else
    echo "❌ Some frontend tests failed!"
fi

# Summary
print_header "TEST SUMMARY"
echo "Backend Tests: $([ $BACKEND_TESTS_PASSED = true ] && echo "✅ PASSED" || echo "❌ FAILED")"
echo "Frontend Tests: $([ $FRONTEND_TESTS_PASSED = true ] && echo "✅ PASSED" || echo "❌ FAILED")"

if [ $BACKEND_TESTS_PASSED = true ] && [ $FRONTEND_TESTS_PASSED = true ]; then
    echo ""
    echo "🎉 All tests passed! The system is ready for deployment."
    exit 0
else
    echo ""
    echo "⚠️  Some tests failed. Please review the output above."
    exit 1
fi