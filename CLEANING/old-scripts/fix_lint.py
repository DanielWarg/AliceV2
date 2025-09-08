#!/usr/bin/env python3
"""
Auto-fix lint issues found by ruff
Priority: Critical bugs first, then code quality
"""

import subprocess


def run_command(cmd):
    """Run shell command and return output"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode


def fix_unused_imports():
    """Remove unused imports with ruff --fix"""
    print("🔧 Fixing unused imports...")
    cmd = "docker exec alice-orchestrator ruff check /app --fix --select F401"
    stdout, stderr, code = run_command(cmd)
    print(f"Unused imports: {stdout}")


def fix_f_strings_without_placeholders():
    """Fix f-strings without placeholders"""
    print("🔧 Fixing f-strings without placeholders...")
    cmd = "docker exec alice-orchestrator ruff check /app --fix --select F541"
    stdout, stderr, code = run_command(cmd)
    print(f"F-strings: {stdout}")


def fix_unused_variables():
    """Fix unused variables"""
    print("🔧 Fixing unused variables...")
    cmd = "docker exec alice-orchestrator ruff check /app --fix --select F841"
    stdout, stderr, code = run_command(cmd)
    print(f"Unused variables: {stdout}")


def report_remaining_issues():
    """Report issues that need manual fixing"""
    print("\n📊 Remaining lint issues that need manual attention:")
    cmd = "docker exec alice-orchestrator ruff check /app --output-format=concise"
    stdout, stderr, code = run_command(cmd)

    if stdout:
        issues = stdout.strip().split("\n")

        # Categorize issues
        bare_except = [i for i in issues if "E722" in i]
        undefined_names = [i for i in issues if "F821" in i]
        other = [i for i in issues if "E722" not in i and "F821" not in i]

        if bare_except:
            print(f"\n❌ BARE EXCEPT CLAUSES ({len(bare_except)}):")
            for issue in bare_except[:5]:  # Show first 5
                print(f"  {issue}")

        if undefined_names:
            print(f"\n❌ UNDEFINED NAMES ({len(undefined_names)}):")
            for issue in undefined_names:
                print(f"  {issue}")

        if other:
            print(f"\n⚠️  OTHER ISSUES ({len(other)}):")
            for issue in other[:10]:  # Show first 10
                print(f"  {issue}")

        print(f"\n📈 TOTAL REMAINING: {len(issues)} issues")
    else:
        print("✅ NO REMAINING LINT ISSUES!")


def main():
    print("🚀 AUTOMATED LINT FIXER")
    print("=" * 50)

    # Auto-fix what we can
    fix_unused_imports()
    fix_f_strings_without_placeholders()
    fix_unused_variables()

    # Report what needs manual work
    report_remaining_issues()

    print("\n🎯 Next steps:")
    print("  1. Fix remaining bare except clauses manually")
    print("  2. Fix undefined names (potential bugs)")
    print("  3. Run tests to ensure fixes didn't break anything")


if __name__ == "__main__":
    main()
