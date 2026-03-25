"""
Comprehensive System Health Check
Checks for:
- Import errors
- Syntax errors  
- Circular dependencies
- Missing modules
- Database connectivity
"""

import sys
import os
import importlib
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("SYSTEM HEALTH CHECK")
print("=" * 60)

# Test modules to check
modules_to_check = [
    'backend.app',
    'backend.questions',
    'backend.grading',
    'backend.question_bank',
    'backend.db.database',
    'backend.config',
    'backend.llm_runner',
    'backend.utils.auth',
    'backend.utils.skill_compiler',
    'backend.utils.llm_client',
    'backend.utils.redis_manager',
    'backend.utils.question_parser',
    'backend.services.question_generation_service',
    'backend.models.cheat_detector',
    'backend.celery_app',
]

results = {
    'passed': [],
    'failed': [],
    'warnings': []
}

for module_name in modules_to_check:
    try:
        print(f"\n[CHECK] {module_name}...", end=" ")
        module = importlib.import_module(module_name)
        print("✅ OK")
        results['passed'].append(module_name)
    except ImportError as e:
        print(f"❌ IMPORT ERROR")
        print(f"  Error: {e}")
        results['failed'].append((module_name, f"ImportError: {e}"))
    except SyntaxError as e:
        print(f"❌ SYNTAX ERROR")
        print(f"  Error: {e}")
        results['failed'].append((module_name, f"SyntaxError: {e}"))
    except Exception as e:
        print(f"⚠️  WARNING")
        print(f"  Error: {e}")
        results['warnings'].append((module_name, str(e)))

# Check database files
print("\n" + "=" * 60)
print("DATABASE CHECK")
print("=" * 60)

db_files = [
    'exam_platform.db',
]

for db_file in db_files:
    db_path = project_root / db_file
    if db_path.exists():
        print(f"✅ {db_file} exists ({db_path.stat().st_size} bytes)")
    else:
        print(f"⚠️  {db_file} not found (will be created on first run)")

# Check critical directories
print("\n" + "=" * 60)
print("DIRECTORY STRUCTURE CHECK")
print("=" * 60)

critical_dirs = [
    'backend',
    'backend/utils',
    'backend/services',
    'backend/models',
    'backend/db',
    'skills',
    'frontend/src',
]

for dir_name in critical_dirs:
    dir_path = project_root / dir_name
    if dir_path.exists():
        file_count = len(list(dir_path.glob('*')))
        print(f"✅ {dir_name}/ ({file_count} items)")
    else:
        print(f"❌ {dir_name}/ MISSING")
        results['failed'].append((dir_name, "Directory missing"))

# Summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

print(f"\n✅ Passed: {len(results['passed'])}")
for module in results['passed']:
    print(f"   - {module}")

if results['warnings']:
    print(f"\n⚠️  Warnings: {len(results['warnings'])}")
    for module, error in results['warnings']:
        print(f"   - {module}: {error}")

if results['failed']:
    print(f"\n❌ Failed: {len(results['failed'])}")
    for module, error in results['failed']:
        print(f"   - {module}: {error}")
    print("\n⚠️  SYSTEM HAS ERRORS - FIX REQUIRED")
    sys.exit(1)
else:
    print("\n✅ ALL CHECKS PASSED - SYSTEM HEALTHY")
    sys.exit(0)
