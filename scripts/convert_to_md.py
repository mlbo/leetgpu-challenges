import os
import re
import shutil
from pathlib import Path
from markdownify import markdownify as md

def html_to_md(html_content, title="Challenge"):
    # Use markdownify for robust conversion
    # We want to preserve some tags or handle them specifically
    markdown = md(html_content, heading_style="ATX", bullets="*")
    
    # Prepend title
    markdown = f"# {title}\n\n" + markdown
    
    # Post-processing for LaTeX and math symbols
    # Replace math symbols
    markdown = markdown.replace('&le;', '<=')
    markdown = markdown.replace('&ge;', '>=')
    markdown = markdown.replace('&times;', 'x')
    markdown = markdown.replace('≤', '<=')
    markdown = markdown.replace('≥', '>=')
    
    # Handle LaTeX blocks: \[ ... \] -> $$ ... $$
    markdown = re.sub(r'\\\[\s*(.*?)\s*\\\]', r'\n$$\n\1\n$$\n', markdown, flags=re.DOTALL)
    # Handle inline LaTeX: \( ... \) -> $ ... $
    markdown = re.sub(r'\\\(\s*(.*?)\s*\\\)', r'$\1$', markdown)
    
    # Clean up multiple newlines
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    
    return markdown.strip()

def main():
    base_dir = Path("challenges")
    docs_root = Path("challenge_docs")
    
    all_challenges = []

    for diff in ["easy", "medium", "hard"]:
        diff_dir = base_dir / diff
        if not diff_dir.exists():
            continue
            
        # Create difficulty subdirectory directly in challenge_docs
        target_diff_dir = docs_root / diff
        target_diff_dir.mkdir(parents=True, exist_ok=True)
            
        for challenge_dir in sorted(diff_dir.iterdir(), key=lambda x: x.name):
            if not challenge_dir.is_dir():
                continue
                
            html_file = challenge_dir / "challenge.html"
            if html_file.exists():
                # Extract title from challenge.py if possible
                title = challenge_dir.name
                challenge_py = challenge_dir / "challenge.py"
                if challenge_py.exists():
                    content = challenge_py.read_text()
                    match = re.search(r'name="(.*?)"', content)
                    if match:
                        title = match.group(1)

                print(f"Converting {html_file}...")
                html_content = html_file.read_text()
                md_content = html_to_md(html_content, title)
                
                # Save in the challenge_docs/<diff>/ directory
                safe_name = challenge_dir.name
                md_file_docs = target_diff_dir / f"{safe_name}.md"
                md_file_docs.write_text(md_content)
                
                all_challenges.append({
                    "id": challenge_dir.name.split('_')[0],
                    "name": title,
                    "difficulty": diff,
                    "path": f"{diff}/{safe_name}.md",
                    "dir": str(challenge_dir)
                })

    # Create a CHALLENGES_INDEX.md index in challenge_docs/
    index_content = "# LeetGPU Challenges Index\n\n"
    for diff in ["easy", "medium", "hard"]:
        index_content += f"## {diff.capitalize()}\n\n"
        diff_challenges = [c for c in all_challenges if c["difficulty"] == diff]
        for c in sorted(diff_challenges, key=lambda x: int(x["id"]) if x["id"].isdigit() else 999):
            index_content += f"* [{c['id']}. {c['name']}]({c['path']}) (Dir: `{c['dir']}`)\n"
        index_content += "\n"
    
    (Path("challenge_docs/CHALLENGES_INDEX.md")).write_text(index_content)
    print(f"Created index at challenge_docs/CHALLENGES_INDEX.md")

if __name__ == "__main__":
    main()
