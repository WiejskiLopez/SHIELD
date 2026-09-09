#!/usr/bin/env python3
import os, ast

check_files = [
    'shell/execution_service/domain/execution/aggregates/edge_execution/edge_execution.py',
    'shell/execution_service/domain/execution/aggregates/edge_link_execution/edge_link_execution.py',
    'shell/execution_service/domain/execution/aggregates/graph_execution/graph_execution.py',
    'shell/user_service/domain/user/aggregates/auth_session/auth_session.py',
]

for f in check_files:
    if not os.path.exists(f):
        print(f'{os.path.basename(f)}: MISSING')
        continue
    with open(f) as fh:
        content = fh.read()
        first_line = content.split('\n')[0].strip()
        has_doc = first_line.startswith('"""') or first_line.startswith("'''")
        print(f'{os.path.basename(f)}: has_doc={has_doc}')