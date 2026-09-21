#!/usr/bin/env python3.12
"""
Daily runner for FX Supertrend strategy.

1. Generate signal (Supertrend + ADX)
2. Execute trades (entries + exits)
3. Report
"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

script_dir = Path(__file__).parent

def run(cmd, timeout=300):
    """Run command, return (stdout, exit_code)."""
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=script_dir,
        capture_output=True,
        text=True,
        timeout=timeout
    )
    return result.stdout, result.returncode

def main():
    print("=" * 70)
    print("FX SUPERTREND — Daily Run")
    print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70)
    
    # Step 1: Generate signal
    print("\n[1/3] Generating signal...")
    out, code = run("python3.12 generate_signal.py")
    if code != 0:
        print(f"🔴 FAILED (exit {code})")
        print(out[-500:])
        sys.exit(1)
    print("✅ Signal generated")
    
    # Step 2: Execute strategy
    print("\n[2/3] Executing strategy...")
    out, code = run("python3.12 execute_strategy.py")
    if code != 0:
        print(f"🔴 FAILED (exit {code})")
        print(out[-500:])
        sys.exit(1)
    print(out)
    print("✅ Execution complete")
    
    # Step 3: Report (TODO)
    print("\n[3/3] Report")
    print("  (report script not yet implemented)")
    
    print("\n" + "=" * 70)
    print("Daily run complete")
    print("=" * 70)

if __name__ == "__main__":
    main()
