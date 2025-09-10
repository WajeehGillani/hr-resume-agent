#!/usr/bin/env python3
"""
Cleanup utility for HR Interview Orchestrator artifacts.
Use this script to organize and clean up the artifacts directory.
"""
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.file_manager import CleanupUtility
from src.config import config

def main():
    parser = argparse.ArgumentParser(
        description="Clean up and organize HR Interview Orchestrator artifacts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cleanup.py                    # Full cleanup, keep 10 latest runs
  python cleanup.py --keep-runs 5     # Keep only 5 latest runs
  python cleanup.py --list-runs       # List recent runs
  python cleanup.py --aggressive      # Remove all old runs and cache
        """
    )
    
    parser.add_argument(
        "--keep-runs", 
        type=int, 
        default=10,
        help="Number of recent runs to keep (default: 10)"
    )
    
    parser.add_argument(
        "--list-runs", 
        action="store_true",
        help="List recent runs without cleaning up"
    )
    
    parser.add_argument(
        "--aggressive", 
        action="store_true",
        help="Aggressive cleanup: remove cache and keep only 3 runs"
    )
    
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Show what would be cleaned without actually doing it"
    )
    
    args = parser.parse_args()
    
    if args.list_runs:
        CleanupUtility.list_runs()
        return
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be deleted")
        print(f"Would keep {args.keep_runs} latest runs")
        print(f"Artifacts directory: {config.ARTIFACTS_DIR}")
        return
    
    if args.aggressive:
        print("⚠️  AGGRESSIVE CLEANUP MODE")
        response = input("This will remove cache and keep only 3 runs. Continue? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
        CleanupUtility.full_cleanup(keep_runs=3, keep_cache=False)
    else:
        CleanupUtility.full_cleanup(keep_runs=args.keep_runs, keep_cache=True)

if __name__ == "__main__":
    main()
