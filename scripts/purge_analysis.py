#!/usr/bin/env python3
"""
CODE PURGE ANALYSIS SCRIPT
Identifierar konkreta targets för code purge
"""

import os
import ast
import json
from pathlib import Path
from collections import defaultdict
import subprocess


def find_large_files(min_lines=200):
    """Find files that are suspiciously large"""
    large_files = []
    
    for root, dirs, files in os.walk('.'):
        # Skip common excludes
        dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', '.pytest_cache']]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        line_count = len(f.readlines())
                    
                    if line_count > min_lines:
                        large_files.append((file_path, line_count))
                except:
                    continue
    
    return sorted(large_files, key=lambda x: x[1], reverse=True)


def find_unused_functions():
    """Find potentially unused functions (basic analysis)"""
    functions = {}
    calls = set()
    
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__']]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    tree = ast.parse(content)
                    
                    # Find function definitions
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            functions[node.name] = file_path
                        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                            calls.add(node.func.id)
                            
                except:
                    continue
    
    # Find functions that are defined but never called
    unused = []
    for func_name, file_path in functions.items():
        if func_name not in calls and not func_name.startswith('_'):  # Skip private functions
            unused.append((func_name, file_path))
    
    return unused


def count_files_by_directory():
    """Count files per directory to identify bloated areas"""
    dir_counts = defaultdict(int)
    
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__']]
        
        # Count Python files only
        py_files = [f for f in files if f.endswith('.py')]
        if py_files:
            dir_counts[root] = len(py_files)
    
    return sorted(dir_counts.items(), key=lambda x: x[1], reverse=True)


def analyze_scripts_directory():
    """Analyze /scripts directory for consolidation opportunities"""
    scripts_path = Path('./scripts')
    if not scripts_path.exists():
        return []
    
    scripts = []
    for script_file in scripts_path.glob('*.py'):
        try:
            with open(script_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = len(content.splitlines())
                
            # Simple heuristics
            has_main = 'if __name__ == "__main__"' in content
            has_docstring = '"""' in content[:500]  # Docstring in first 500 chars
            
            scripts.append({
                'file': str(script_file),
                'lines': lines, 
                'has_main': has_main,
                'has_docstring': has_docstring,
                'size_kb': script_file.stat().st_size // 1024
            })
        except:
            continue
    
    return sorted(scripts, key=lambda x: x['lines'], reverse=True)


def analyze_dependencies():
    """Analyze requirements.txt for potential bloat"""
    deps = {}
    
    req_files = ['requirements.txt', 'services/orchestrator/requirements.txt']
    
    for req_file in req_files:
        if os.path.exists(req_file):
            with open(req_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        pkg_name = line.split('==')[0].split('>=')[0].split('<=')[0]
                        deps[pkg_name] = req_file
    
    return deps


def run_ruff_analysis():
    """Get current ruff issues for cleanup"""
    try:
        result = subprocess.run(
            ['docker', 'exec', 'alice-orchestrator', 'ruff', 'check', '/app', '--output-format=json'],
            capture_output=True, text=True
        )
        if result.stdout:
            return json.loads(result.stdout)
    except:
        pass
    return []


def main():
    print("🧹 CODE PURGE ANALYSIS")
    print("=" * 50)
    
    # 1. Large Files Analysis
    print("\n📏 LARGE FILES (>200 lines):")
    large_files = find_large_files()
    for file_path, lines in large_files[:10]:
        print(f"  {lines:4d} lines: {file_path}")
    
    # 2. Directory Bloat Analysis  
    print("\n📁 DIRECTORY FILE COUNTS:")
    dir_counts = count_files_by_directory()
    for directory, count in dir_counts[:10]:
        print(f"  {count:2d} files: {directory}")
    
    # 3. Scripts Analysis
    print("\n📜 SCRIPTS ANALYSIS:")
    scripts = analyze_scripts_directory()
    if scripts:
        print(f"  Total scripts: {len(scripts)}")
        for script in scripts[:10]:
            status = "✅" if script['has_main'] and script['has_docstring'] else "⚠️"
            print(f"  {status} {script['lines']:3d} lines: {script['file']}")
    
    # 4. Dependencies Analysis
    print("\n📦 DEPENDENCIES:")
    deps = analyze_dependencies()
    print(f"  Total unique packages: {len(deps)}")
    heavy_deps = [
        'pandas', 'pyarrow', 'fastparquet', 'numpy', 
        'openai', 'httpx', 'requests', 'pytest'
    ]
    for dep in heavy_deps:
        if dep in deps:
            print(f"  📦 {dep} in {deps[dep]}")
    
    # 5. Ruff Issues
    print("\n🔍 CURRENT RUFF ISSUES:")
    issues = run_ruff_analysis()
    if issues:
        issue_types = defaultdict(int)
        for issue in issues:
            issue_types[issue.get('code', 'unknown')] += 1
        
        for issue_type, count in sorted(issue_types.items()):
            print(f"  {issue_type}: {count} issues")
    else:
        print("  No ruff issues detected (or Docker not accessible)")
    
    # 6. Summary & Recommendations
    print("\n🎯 PURGE RECOMMENDATIONS:")
    if large_files:
        print(f"  1. Review {len([f for f in large_files if f[1] > 500])} files >500 lines")
    if scripts and len(scripts) > 15:
        print(f"  2. Consolidate {len(scripts)} scripts (many seem single-use)")
    if len(deps) > 25:
        print(f"  3. Audit {len(deps)} dependencies for necessity")
    
    bloated_dirs = [d for d, c in dir_counts if c > 8 and 'test' not in d[0]]
    if bloated_dirs:
        print(f"  4. Review bloated directories: {bloated_dirs[:3]}")
    
    print("\n✅ Analysis complete! See CODE_PURGE_PLAN.md for execution strategy.")


if __name__ == "__main__":
    main()