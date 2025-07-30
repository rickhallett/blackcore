#!/usr/bin/env python3
"""Merge hook files from .claude and .claude_to_merge directories."""

import os
from pathlib import Path

def merge_python_files(file1_path, file2_path, output_path):
    """Merge two Python files by concatenating their content with section markers."""
    
    # Read both files
    content1 = ""
    content2 = ""
    
    if os.path.exists(file1_path):
        with open(file1_path, 'r') as f:
            content1 = f.read()
    
    if os.path.exists(file2_path):
        with open(file2_path, 'r') as f:
            content2 = f.read()
    
    # If files are identical, just keep one version
    if content1 == content2:
        with open(output_path, 'w') as f:
            f.write(content1)
        return
    
    # Extract shebang and script metadata from first file
    lines1 = content1.split('\n') if content1 else []
    lines2 = content2.split('\n') if content2 else []
    
    header_lines = []
    content1_start = 0
    content2_start = 0
    
    # Extract header from first file that has content
    for i, line in enumerate(lines1 if lines1 else lines2):
        if line.startswith('#!') or line.strip().startswith('# ///') or (i > 0 and line.strip() == '# ///'):
            header_lines.append(line)
            content1_start = i + 1 if lines1 else 0
            content2_start = i + 1 if lines2 else 0
        else:
            break
    
    # Build merged content
    merged_lines = header_lines + ['']
    
    # Add imports section - merge unique imports from both
    imports1 = []
    imports2 = []
    other1 = []
    other2 = []
    
    # Separate imports from other content
    for line in lines1[content1_start:]:
        if line.strip().startswith('import ') or line.strip().startswith('from '):
            imports1.append(line)
        else:
            other1.append(line)
    
    for line in lines2[content2_start:]:
        if line.strip().startswith('import ') or line.strip().startswith('from '):
            imports2.append(line)
        else:
            other2.append(line)
    
    # Merge imports (remove duplicates)
    all_imports = []
    seen_imports = set()
    for imp in imports1 + imports2:
        if imp.strip() and imp.strip() not in seen_imports:
            seen_imports.add(imp.strip())
            all_imports.append(imp)
    
    if all_imports:
        merged_lines.extend(all_imports)
        merged_lines.append('')
    
    # Add content from both versions
    if other1 and other1 != ['']:
        merged_lines.append('# ===== FROM .claude VERSION =====')
        merged_lines.extend(other1)
        if other1[-1].strip():  # Add blank line if not already there
            merged_lines.append('')
    
    if other2 and other2 != [''] and '\n'.join(other1).strip() != '\n'.join(other2).strip():
        merged_lines.append('# ===== FROM .claude_to_merge VERSION =====')
        merged_lines.extend(other2)
    
    # Write merged content
    with open(output_path, 'w') as f:
        f.write('\n'.join(merged_lines))

def main():
    base_dir = Path.cwd()
    claude_dir = base_dir / '.claude'
    merge_dir = base_dir / '.claude_to_merge'
    
    # Files to merge
    files_to_merge = [
        'hooks/notification.py',
        'hooks/stop.py',
        'hooks/pre_tool_use.py',
        'hooks/subagent_stop.py',
        'hooks/utils/llm/oai.py',
        'hooks/utils/llm/anth.py',
        'hooks/utils/tts/pyttsx3_tts.py',
        'hooks/utils/tts/openai_tts.py',
        'hooks/utils/tts/elevenlabs_tts.py',
    ]
    
    for file_path in files_to_merge:
        file1 = claude_dir / file_path
        file2 = merge_dir / file_path
        output = claude_dir / file_path
        
        print(f"Merging {file_path}...")
        merge_python_files(file1, file2, output)
    
    print("Python file merging complete!")

if __name__ == '__main__':
    main()