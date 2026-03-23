#!/usr/bin/env python
"""
Configuration Validation Script
Checks if all required environment variables and files are set up correctly
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def check_env_file():
    """Check if .env file exists"""
    print("✓ Checking .env file...")
    if os.path.exists('.env'):
        print("  ✅ .env file found")
        return True
    else:
        print("  ❌ .env file not found")
        print("  ℹ️  Please copy .env.example to .env and fill in your API keys")
        return False

def check_env_variables():
    """Check if required environment variables are set"""
    print("\n✓ Checking environment variables...")
    
    required_vars = ['GEMINI_API_KEY', 'GNEWS_API_KEY']
    optional_vars = ['MODEL_PATH', 'TFIDF_PATH', 'CONFIG_PATH', 'MODEL_VERSION']
    
    load_dotenv()
    
    all_ok = True
    
    for var in required_vars:
        value = os.getenv(var, '')
        if value and value != 'your_key_here' and not value.startswith('your_'):
            print(f"  ✅ {var}: Configured")
        else:
            print(f"  ❌ {var}: Not configured or placeholder value")
            all_ok = False
    
    for var in optional_vars:
        value = os.getenv(var, '')
        if value:
            print(f"  ℹ️  {var}: {value}")
        else:
            print(f"  ℹ️  {var}: Using default")
    
    return all_ok

def check_model_files():
    """Check if required model files exist"""
    print("\n✓ Checking model files...")
    
    model_files = [
        'models/pipeline.joblib',
        'models/tfidf.joblib',
        'models/config.json'
    ]
    
    all_ok = True
    for file in model_files:
        if os.path.exists(file):
            size_mb = os.path.getsize(file) / (1024 * 1024)
            print(f"  ✅ {file} ({size_mb:.1f} MB)")
        else:
            print(f"  ⚠️  {file}: Not found")
            all_ok = False
    
    return all_ok

def check_data_files():
    """Check if data files exist"""
    print("\n✓ Checking data files...")
    
    data_files = [
        'data/Fake.csv',
        'data/True.csv',
        'test_news_samples.txt'
    ]
    
    all_ok = True
    for file in data_files:
        if os.path.exists(file):
            size_mb = os.path.getsize(file) / (1024 * 1024)
            print(f"  ✅ {file} ({size_mb:.1f} MB)")
        else:
            print(f"  ℹ️  {file}: Not found (optional for running)")
    
    return True

def check_required_packages():
    """Check if required packages are installed"""
    print("\n✓ Checking required packages...")
    
    packages = [
        ('streamlit', 'Streamlit'),
        ('sklearn', 'scikit-learn'),
        ('joblib', 'joblib'),
        ('numpy', 'NumPy'),
        ('pandas', 'Pandas'),
        ('fastapi', 'FastAPI (optional)'),
        ('dotenv', 'python-dotenv'),
    ]
    
    all_ok = True
    for package, name in packages:
        try:
            __import__(package)
            print(f"  ✅ {name}")
        except ImportError:
            if 'optional' in name:
                print(f"  ℹ️  {name}: Not installed (optional)")
            else:
                print(f"  ❌ {name}: Not installed")
                all_ok = False
    
    return all_ok

def check_directories():
    """Check if required directories exist"""
    print("\n✓ Checking directories...")
    
    directories = [
        'models/',
        'data/',
        'data_new/',
        'logs/',
        'app_pages/',
        'assets/'
    ]
    
    all_ok = True
    for dir in directories:
        if os.path.isdir(dir):
            print(f"  ✅ {dir}/")
        else:
            print(f"  ❌ {dir}/: Not found")
            all_ok = False
    
    return all_ok

def main():
    """Run all checks"""
    print("=" * 60)
    print("🔍 Fake News Detector - Configuration Validation")
    print("=" * 60)
    
    results = {
        'env_file': check_env_file(),
        'env_vars': check_env_variables(),
        'model_files': check_model_files(),
        'data_files': check_data_files(),
        'packages': check_required_packages(),
        'directories': check_directories(),
    }
    
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for check, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {check.replace('_', ' ').title()}")
    
    print(f"\nTotal: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n✅ All checks passed! You're ready to run the application.")
        print("\nQuick start commands:")
        print("  • Web app:  streamlit run app.py")
        print("  • API:      python api.py")
        print("  • Training: python train.py")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("See QUICK_START.md for help.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
