from pathlib import Path
from collections import Counter

LOG_FILE = Path("logs/pipeline.log")

def parse_log(log_path: Path)-> None:
    if not log_path.exists():
        print(f"Log file not found {log_path}")
        return
    
    counts = Counter()
    errors = []
    warnings = []


    with open(log_path, "r") as f:
        for line in f:
            if "| ERROR |" in line:
                counts["ERROR"] += 1
                errors.append(line.strip())
            elif "| WARNING |" in line:
                counts["WARNING"] += 1
                warnings.append(line.strip())
            elif "| INFO |" in line:
                counts["INFO"] += 1

    total = sum(counts.values())

    print(f"\n{'='*60}")
    print(f"LOG SUMMARY: {log_path}")
    print(f"{'='*60}")
    print(f"Total lines : {total}")
    print(f"INFO        : {counts['INFO']}")
    print(f"WARNING     : {counts['WARNING']}")
    print(f"ERROR       : {counts['ERROR']}")

    if errors:
        print(f"\n--- ERRORS {len(errors)} ---")
        for e in errors:
            print(f"    {e}")
    
    if warnings:
        print(f"\n--- WARNINGS {len(warnings)} ---")
        for e in warnings:
            print(f"    {e}")

    if not errors and not warnings:
        print(f"\nNo errors or warnings found.")

    print(f"{'='*60}\n")

if __name__ == "__main__":
    parse_log(LOG_FILE)