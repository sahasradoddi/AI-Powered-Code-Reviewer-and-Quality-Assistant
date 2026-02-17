#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path

def passes_quality_gate(file_path):
    """Run analysis, allow LOW smells only"""
    result = subprocess.run([
        'python', 'cli.py', 'scan', file_path, '-o', '/dev/null'
    ], capture_output=True, text=True)
    
    # PASS if exit 0 OR only low severity (check stderr for "LOW")
    output = result.stdout + result.stderr
    if result.returncode == 0:
        return True
    if "LOW" in output and "MEDIUM" not in output and "HIGH" not in output:
        return True
    return False

staged_files = sys.argv[1:] if len(sys.argv) > 1 else ['.']

failed_files = []
for file_path in staged_files:
    if Path(file_path).suffix == '.py':
        print(f"Analyzing: {file_path}")
        if not passes_quality_gate(file_path):
            failed_files.append(file_path)

if failed_files:
    print("Quality gate failed! Fix these files:")
    for f in failed_files:
        print(f"   {f}")
    sys.exit(1)

print(" All staged Python files passed quality gate!")
