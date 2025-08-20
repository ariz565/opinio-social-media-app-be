#!/usr/bin/env python3
"""
Test runner script for Gulf Return Social Media Backend
"""

import subprocess
import sys
import os
from pathlib import Path

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def run_command(command):
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            shell=True,
            cwd=Path(__file__).parent
        )
        return result
    except Exception as e:
        print(f"{RED}Error running command: {command}{RESET}")
        print(f"{RED}Error: {e}{RESET}")
        return None

def print_header(text):
    """Print a formatted header"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_section(text):
    """Print a formatted section header"""
    print(f"\n{YELLOW}{'-'*40}{RESET}")
    print(f"{YELLOW}{text}{RESET}")
    print(f"{YELLOW}{'-'*40}{RESET}")

def run_tests(test_type="all"):
    """Run the test suite"""
    
    print_header("Gulf Return Social Media Backend - Test Suite")
    
    # Test commands
    commands = {
        "all": "python -m pytest app/tests/test_auth.py -v",
        "registration": "python -m pytest app/tests/test_auth.py::TestUserRegistration -v",
        "login": "python -m pytest app/tests/test_auth.py::TestUserLogin -v", 
        "password_reset": "python -m pytest app/tests/test_auth.py::TestPasswordReset -v",
        "token_refresh": "python -m pytest app/tests/test_auth.py::TestTokenRefresh -v",
        "email_verification": "python -m pytest app/tests/test_auth.py::TestEmailVerification -v",
        "integration": "python -m pytest app/tests/test_auth.py::TestIntegrationScenarios -v",
        "quick": "python -m pytest app/tests/test_auth.py::TestUserRegistration::test_successful_registration app/tests/test_auth.py::TestUserLogin::test_first_time_login_success app/tests/test_auth.py::TestPasswordReset::test_forgot_password_success -v"
    }
    
    if test_type not in commands:
        print(f"{RED}Unknown test type: {test_type}{RESET}")
        print(f"{YELLOW}Available test types: {', '.join(commands.keys())}{RESET}")
        return False
    
    print_section(f"Running {test_type} tests...")
    
    # Run the test command
    result = run_command(commands[test_type])
    
    if result is None:
        return False
        
    # Print results
    if result.returncode == 0:
        print(f"{GREEN}✅ All tests passed!{RESET}")
        return True
    else:
        print(f"{RED}❌ Some tests failed{RESET}")
        
        # Extract test summary from output
        lines = result.stdout.split('\n')
        for line in lines:
            if 'failed' in line and 'passed' in line:
                print(f"{YELLOW}Results: {line}{RESET}")
                break
                
        return False

def show_test_summary():
    """Show a summary of available tests"""
    print_header("Available Test Categories")
    
    test_info = {
        "all": "Run all authentication tests (25 tests)",
        "registration": "User registration tests (6 tests)",
        "login": "User login tests (6 tests)",
        "password_reset": "Password reset tests (5 tests)", 
        "token_refresh": "Token refresh tests (2 tests)",
        "email_verification": "Email verification tests (3 tests)",
        "integration": "Integration scenario tests (2 tests)",
        "quick": "Quick smoke tests (3 critical tests)"
    }
    
    for test_type, description in test_info.items():
        print(f"{BLUE}{test_type:15}{RESET} - {description}")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print(f"{YELLOW}Usage: python run_tests.py <test_type>{RESET}")
        show_test_summary()
        return
    
    test_type = sys.argv[1].lower()
    
    if test_type == "help" or test_type == "--help":
        show_test_summary()
        return
    
    # Check if we're in the right directory
    if not os.path.exists("app/tests/test_auth.py"):
        print(f"{RED}Error: test_auth.py not found. Make sure you're in the project root directory.{RESET}")
        return
    
    # Run tests
    success = run_tests(test_type)
    
    if success:
        print(f"\n{GREEN}🎉 Test run completed successfully!{RESET}")
    else:
        print(f"\n{RED}💥 Test run completed with failures. Check the output above for details.{RESET}")
        print(f"{YELLOW}💡 Tip: Run 'python run_tests.py quick' for a fast smoke test{RESET}")

if __name__ == "__main__":
    main()
