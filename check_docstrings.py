import os
import re

root = r"C:\Users\palysiewicz\IdeaProjects\SHELL\shell\platform"

def has_module_docstring(content):
    """Check if file has a module-level docstring at the top."""
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#!') or line.startswith('# -*-') or line.startswith('# coding'):
            i += 1
            continue
        if line.startswith('"""') or line.startswith("'''"):
            return True
        if line.startswith('from __future__'):
            j = i + 1
            while j < len(lines):
                l = lines[j].strip()
                if l.startswith('"""') or l.startswith("'''"):
                    return True
                if l and not l.startswith('#'):
                    break
                j += 1
            return False
        if line and not line.startswith('#'):
            return False
        i += 1
    return False

files_without = []
for root_dir, dirs, files in os.walk(r"C:\Users\palysiewicz\IdeaProjects\SHELL\shell\platform"):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root_dir, f)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if not has_module_docstring(content):
                    files_without.append(path)
            except:
                pass

print(f"Files without module docstring: {len(files_without)}")
for f in sorted(files_without):
    print(f)