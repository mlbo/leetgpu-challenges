#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path

def get_challenges():
    challenges = []
    base_dir = Path("challenges")
    for diff in ["easy", "medium", "hard"]:
        diff_dir = base_dir / diff
        if not diff_dir.exists():
            continue
        # Sort challenges within each difficulty by ID (numeric)
        diff_challenges = []
        for d in diff_dir.iterdir():
            if d.is_dir() and "_" in d.name:
                try:
                    challenge_id = int(d.name.split("_")[0])
                    diff_challenges.append({
                        "id_int": challenge_id,
                        "id": str(challenge_id),
                        "name": d.name,
                        "difficulty": diff,
                        "path": d
                    })
                except ValueError:
                    continue
        
        # Sort by ID (numeric)
        diff_challenges.sort(key=lambda x: x["id_int"])
        challenges.extend(diff_challenges)
    return challenges

def run_interaction():
    challenges = get_challenges()
    if not challenges:
        print("\033[91mNo challenges found in challenges/ directory.\033[0m")
        return False

    print("\n\033[94m" + "="*40 + "\033[0m")
    print("\033[1;94m   LeetGPU Interactive Solver\033[0m")
    print("\033[94m" + "="*40 + "\033[0m")
    print(f"Found \033[92m{len(challenges)}\033[0m challenges.")

    print("\n\033[1mQuick Filters:\033[0m")
    print("  [e] Easy  [m] Medium  [h] Hard  [a] All  [q] Quit")
    
    search = input("\n\033[1m🔍 Search (ID, Name, or Filter): \033[0m").strip().lower()
    
    if search in ['q', 'exit', 'quit']:
        return False

    # 1. Handle exact ID match first
    exact_match = next((c for c in challenges if search == c["id"] or search == c["id"].zfill(2)), None)
    if exact_match:
        return handle_selected_challenge(exact_match)

    # 2. Handle Filters
    if search in ['e', 'easy']:
        filtered = [c for c in challenges if c["difficulty"] == "easy"]
    elif search in ['m', 'medium']:
        filtered = [c for c in challenges if c["difficulty"] == "medium"]
    elif search in ['h', 'hard']:
        filtered = [c for c in challenges if c["difficulty"] == "hard"]
    elif search in ['a', 'all'] or not search:
        filtered = challenges
    else:
        # 3. Handle fuzzy name search
        filtered = [c for c in challenges if search in c["name"].lower()]

    if not filtered:
        print("\033[91mNo matching challenges found.\033[0m")
        return True

    # If only one result and it's an exact name match, skip selection
    if len(filtered) == 1 and (search == filtered[0]["name"].lower() or search == filtered[0]["id"]):
        return handle_selected_challenge(filtered[0])

    print("\n\033[1mSelect a challenge:\033[0m")
    for c in filtered:
        color = "\033[92m" if c["difficulty"] == "easy" else "\033[93m" if c["difficulty"] == "medium" else "\033[91m"
        display_id = c['id'].zfill(2)
        print(f"  {display_id:>3}. [{color}{c['difficulty'].upper():6}\033[0m] {c['name']}")

    try:
        choice_input = input(f"\n\033[1m👉 Enter challenge ID (or 'b' for back): \033[0m").strip()
        if not choice_input or choice_input.lower() == 'b': return True
        if choice_input.lower() in ['q', 'exit', 'quit']: return False
        
        selected = next((c for c in filtered if c["id"] == choice_input or c["id"] == choice_input.lstrip('0') or (choice_input == '0' and c["id"] == '0')), None)
        
        if not selected:
            print(f"\033[91mInvalid ID: {choice_input}.\033[0m")
            return True
        return handle_selected_challenge(selected)
    except Exception as e:
        print(f"\033[91mError: {e}\033[0m")
        return True

def handle_selected_challenge(selected):
    challenge_path = selected["path"]
    print(f"\n\033[1;92m🚀 Selected: {selected['name']}\033[0m")
    
    ext = "cu"
    testing_dir = challenge_path / "Testing"
    solution_file = testing_dir / f"solution.{ext}"
    
    if not solution_file.exists():
        create = input(f"\n\033[1m❓ Solution file not found. Create from starter? (y/n): \033[0m").strip().lower()
        if create == 'y':
            testing_dir.mkdir(exist_ok=True)
            starter_file = challenge_path / "starter" / f"starter.{ext}"
            if starter_file.exists():
                solution_file.write_text(starter_file.read_text())
                print(f"\033[92m✅ Created {solution_file}\033[0m")
            else:
                solution_file.touch()
                print(f"\033[92m✅ Created empty {solution_file}\033[0m")
            
            print(f"\033[94m📖 Opening new solution file in editor...\033[0m")
            subprocess.run(["code", "-r", str(solution_file)])
            print("\033[93mReturning to challenge selection...\033[0m")
            return True
        else:
            print("\033[93mSkipping solution creation.\033[0m")
            return True
    
    action = input(f"\033[1m👉 Action: [r]un tests, [o]pen in editor, [b]ack to list: \033[0m").strip().lower()
    
    if action == 'o':
        print(f"\033[94m📖 Opening solution file in editor...\033[0m")
        subprocess.run(["code", "-r", str(solution_file)])
        return True
    elif action == 'b':
        return True
    elif action != 'r' and action != '':
        print("\033[93mInvalid action, returning to list.\033[0m")
        return True

    print(f"\n\033[1;94m🧪 Running local tests for {selected['name']}...\033[0m")
    print("\033[90m" + "-"*40 + "\033[0m")
    
    cmd = [
        sys.executable, 
        "scripts/run_challenge.py", 
        str(challenge_path), 
        "--language", "cuda", 
        "--local",
        "--output-dir", str(testing_dir)
    ]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\033[93mInterrupted.\033[0m")
    except Exception as e:
        print(f"\n\033[91mError running tests: {e}\033[0m")
    
    print("\033[90m" + "-"*40 + "\033[0m")
    input("\n\033[1mPress [Enter] to continue...\033[0m")
    return True

def main():
    try:
        while run_interaction():
            pass
    except KeyboardInterrupt:
        pass
    print("\n\033[1;94mGoodbye!\033[0m")

if __name__ == "__main__":
    main()
