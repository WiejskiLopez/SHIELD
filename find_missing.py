import ast, os

# Find classes inheriting from AggregateRoot without descriptions
for root, dirs, files in os.walk('shell'):
    for f in files:
        if not f.endswith('.py'):
            continue
        path = os.path.join(root, f)
        try:
            with open(path) as fh:
                tree = ast.parse(fh.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        for base in node.bases:
                            if isinstance(base, ast.Name) and base.id == 'AggregateRoot':
                                # Check if it already has a docstring as first statement
                                first_stmt = node.body[0] if node.body else None
                                has_doc = isinstance(first_stmt, ast.Expr) and isinstance(first_stmt.value, ast.Constant) and isinstance(first_stmt.value.value, str)
                                if not has_doc:
                                    print(f'{path}:{node.lineno}: {node.name} - NEEDS DESCRIPTION')
                                break
                        break
        except Exception as e:
            pass