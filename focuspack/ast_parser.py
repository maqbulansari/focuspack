"""
AST & signature extraction module for focuspack.
Produces compressed skeleton outlines of files, reducing token usage by up to 80%
while preserving full architectural, class, and method context for LLMs.
"""

from __future__ import annotations

import ast
import re
import warnings


def _format_docstring(doc: str, indent: str = "", is_module: bool = False) -> list[str]:
    """
    Format docstring safely preserving raw string prefix for escape sequences.
    Prevents SyntaxError or invalid escape sequence warnings on paths like C:\\Users.
    """
    if not doc:
        return []

    # If raw string works and does not end with quote, try it
    if "\\" in doc and not doc.endswith('"'):
        candidate = f'r"""\n{doc}\n"""' if is_module else f'{indent}r"""{doc}"""'
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=SyntaxWarning)
                ast.parse(f"def _():\n    {candidate.strip()}\n")
            return [candidate]
        except Exception:
            pass

    # Normal escaping: escape backslashes, internal triple quotes, and trailing quotes
    escaped = doc.replace("\\", "\\\\").replace('"""', r"\"\"\"")
    if escaped.endswith('"'):
        idx = len(escaped)
        while idx > 0 and escaped[idx - 1] == '"':
            idx -= 1
        trailing_count = len(escaped) - idx
        escaped = escaped[:idx] + (r"\"" * trailing_count)

    if is_module:
        return [f'"""\n{escaped}\n"""']
    return [f'{indent}"""{escaped}"""']


class ASTParser:
    """Extracts structural code skeletons and API signatures."""

    @classmethod
    def can_parse(cls, file_path: str) -> bool:
        """Check if file type is supported for AST skeleton extraction."""
        path_lower = file_path.lower()
        return path_lower.endswith((".py", ".ts", ".js", ".tsx", ".jsx", ".go", ".rs"))

    @classmethod
    def extract_skeleton(cls, content: str, file_path: str) -> str:
        """Extract code skeleton based on file language extension."""
        path_lower = file_path.lower()
        if path_lower.endswith(".py"):
            return cls.extract_python_skeleton(content)
        elif path_lower.endswith((".ts", ".tsx", ".js", ".jsx")):
            return cls.extract_js_ts_skeleton(content)
        elif path_lower.endswith(".go"):
            return cls.extract_go_skeleton(content)
        elif path_lower.endswith(".rs"):
            return cls.extract_rust_skeleton(content)
        return content

    @classmethod
    def strip_docstrings_python(cls, code: str) -> str:
        """
        Cleanly remove docstrings from Python AST without damaging multiline code.
        Preserves imports, signatures, annotations, and code structure.
        """
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=SyntaxWarning)
                tree = ast.parse(code)
        except Exception:
            return code

        class DocstringStripper(ast.NodeTransformer):
            def _strip(self, body_list):
                if (
                    body_list
                    and isinstance(body_list[0], ast.Expr)
                    and isinstance(body_list[0].value, ast.Constant)
                    and isinstance(body_list[0].value.value, str)
                ):
                    body_list.pop(0)
                    if not body_list:
                        body_list.append(ast.Expr(value=ast.Constant(value=Ellipsis)))
                return body_list

            def visit_FunctionDef(self, node):
                self.generic_visit(node)
                node.body = self._strip(node.body)
                return node

            def visit_AsyncFunctionDef(self, node):
                self.generic_visit(node)
                node.body = self._strip(node.body)
                return node

            def visit_ClassDef(self, node):
                self.generic_visit(node)
                node.body = self._strip(node.body)
                return node

            def visit_Module(self, node):
                self.generic_visit(node)
                node.body = self._strip(node.body)
                return node

        stripped = DocstringStripper().visit(tree)
        ast.fix_missing_locations(stripped)
        return ast.unparse(stripped)

    @classmethod
    def compress_large_methods_python(cls, code: str, min_lines: int = 15) -> str:
        """
        Compress large internal function/method bodies in Python AST to '...',
        preserving class definitions, signatures, parameter types, and docstrings.
        """
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=SyntaxWarning)
                tree = ast.parse(code)
        except Exception:
            return code

        class BodyCompressor(ast.NodeTransformer):
            def visit_FunctionDef(self, node):
                self.generic_visit(node)
                # Size-based compression strictly adhering to min_lines
                line_count = (
                    (node.end_lineno - node.lineno)
                    if (hasattr(node, "end_lineno") and hasattr(node, "lineno"))
                    else len(node.body)
                )
                if line_count > min_lines:
                    doc = ast.get_docstring(node)
                    new_body = []
                    if doc:
                        new_body.append(ast.Expr(value=ast.Constant(value=doc)))
                    new_body.append(ast.Expr(value=ast.Constant(value=Ellipsis)))
                    node.body = new_body
                return node

            def visit_AsyncFunctionDef(self, node):
                self.generic_visit(node)
                line_count = (
                    (node.end_lineno - node.lineno)
                    if (hasattr(node, "end_lineno") and hasattr(node, "lineno"))
                    else len(node.body)
                )
                if line_count > min_lines:
                    doc = ast.get_docstring(node)
                    new_body = []
                    if doc:
                        new_body.append(ast.Expr(value=ast.Constant(value=doc)))
                    new_body.append(ast.Expr(value=ast.Constant(value=Ellipsis)))
                    node.body = new_body
                return node

        compressed = BodyCompressor().visit(tree)
        ast.fix_missing_locations(compressed)
        return ast.unparse(compressed)

    @classmethod
    def extract_python_skeleton(cls, code: str) -> str:
        """
        Extract clean Python module outline containing imports, classes, methods,
        signatures, docstrings, and type annotations, with bodies replaced by '...'.
        """
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=SyntaxWarning)
                tree = ast.parse(code)
        except Exception:
            return code

        lines: list[str] = []

        mod_doc = ast.get_docstring(tree)
        if mod_doc:
            lines.extend(_format_docstring(mod_doc, "", is_module=True))
            lines.append("")

        def _should_preserve_value(val_node: ast.expr | None) -> bool:
            if val_node is None:
                return False
            if isinstance(
                val_node, (ast.Constant, ast.List, ast.Tuple, ast.Dict, ast.Set, ast.Name)
            ):
                unp = ast.unparse(val_node)
                return "\n" not in unp and len(unp) <= 80
            unp = ast.unparse(val_node)
            return "\n" not in unp and len(unp) <= 60

        def format_arg(arg: ast.arg) -> str:
            res = arg.arg
            if arg.annotation:
                res += f": {ast.unparse(arg.annotation)}"
            return res

        def format_arguments(args: ast.arguments) -> str:
            parts = []
            all_pos = args.posonlyargs + args.args
            posonly_count = len(args.posonlyargs)
            default_offset = len(all_pos) - len(args.defaults)

            for i, a in enumerate(args.posonlyargs):
                s = format_arg(a)
                if i >= default_offset:
                    s += f" = {ast.unparse(args.defaults[i - default_offset])}"
                parts.append(s)

            if posonly_count > 0:
                parts.append("/")

            for i, a in enumerate(args.args, start=posonly_count):
                s = format_arg(a)
                if i >= default_offset:
                    s += f" = {ast.unparse(args.defaults[i - default_offset])}"
                parts.append(s)

            if args.vararg:
                parts.append(f"*{format_arg(args.vararg)}")
            elif args.kwonlyargs:
                parts.append("*")

            for i, a in enumerate(args.kwonlyargs):
                s = format_arg(a)
                default = args.kw_defaults[i]
                if default is not None:
                    s += f" = {ast.unparse(default)}"
                parts.append(s)

            if args.kwarg:
                parts.append(f"**{format_arg(args.kwarg)}")

            return ", ".join(parts)

        def format_decorators(decorator_list: list[ast.expr], indent: str = "") -> list[str]:
            res = []
            for dec in decorator_list:
                res.append(f"{indent}@{ast.unparse(dec)}")
            return res

        def format_function(
            node: ast.FunctionDef | ast.AsyncFunctionDef, indent: str = ""
        ) -> list[str]:
            res = format_decorators(node.decorator_list, indent)
            prefix = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
            sig = f"{indent}{prefix}{node.name}({format_arguments(node.args)})"
            if node.returns:
                sig += f" -> {ast.unparse(node.returns)}:"
            else:
                sig += ":"
            res.append(sig)

            doc = ast.get_docstring(node)
            if doc:
                res.extend(_format_docstring(doc, f"{indent}    "))
            res.append(f"{indent}    ...")
            return res

        def format_class(node: ast.ClassDef, indent: str = "") -> list[str]:
            res = format_decorators(node.decorator_list, indent)
            bases_str = ", ".join(ast.unparse(b) for b in node.bases)
            if bases_str:
                res.append(f"{indent}class {node.name}({bases_str}):")
            else:
                res.append(f"{indent}class {node.name}:")

            doc = ast.get_docstring(node)
            has_body = False
            inner_indent = indent + "    "
            if doc:
                res.extend(_format_docstring(doc, inner_indent))
                has_body = True

            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    res.append("")
                    res.extend(format_function(item, inner_indent))
                    has_body = True
                elif isinstance(item, ast.ClassDef):
                    res.append("")
                    res.extend(format_class(item, inner_indent))
                    has_body = True
                elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    val = f" = {ast.unparse(item.value)}" if item.value else ""
                    res.append(
                        f"{inner_indent}{item.target.id}: {ast.unparse(item.annotation)}{val}"
                    )
                    has_body = True
                elif isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            if item.value and (
                                target.id == "__all__"
                                or target.id.isupper()
                                or _should_preserve_value(item.value)
                            ):
                                res.append(f"{inner_indent}{target.id} = {ast.unparse(item.value)}")
                            else:
                                res.append(f"{inner_indent}{target.id} = ...")
                            has_body = True

            if not has_body:
                res.append(f"{inner_indent}...")
            return res

        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                lines.append(ast.unparse(node))
            elif isinstance(node, ast.If):
                test_str = ast.unparse(node.test)
                if "TYPE_CHECKING" in test_str:
                    lines.append(f"if {test_str}:")
                    for sub_node in node.body:
                        if isinstance(sub_node, (ast.Import, ast.ImportFrom)):
                            lines.append(f"    {ast.unparse(sub_node)}")
            elif isinstance(node, ast.Try):
                import_nodes = [
                    sub for sub in node.body if isinstance(sub, (ast.Import, ast.ImportFrom))
                ]
                if import_nodes:
                    lines.append("try:")
                    for sub in node.body:
                        if isinstance(sub, (ast.Import, ast.ImportFrom)):
                            lines.append(f"    {ast.unparse(sub)}")
                        else:
                            lines.append("    ...")
                    for handler in node.handlers:
                        exc = f" {ast.unparse(handler.type)}" if handler.type else ""
                        as_name = f" as {handler.name}" if handler.name else ""
                        lines.append(f"except{exc}{as_name}:")
                        handler_imports = [
                            sub
                            for sub in handler.body
                            if isinstance(sub, (ast.Import, ast.ImportFrom))
                        ]
                        if handler_imports:
                            for sub in handler.body:
                                if isinstance(sub, (ast.Import, ast.ImportFrom)):
                                    lines.append(f"    {ast.unparse(sub)}")
                                else:
                                    lines.append("    ...")
                        else:
                            lines.append("    ...")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                lines.append("")
                lines.extend(format_function(node))
            elif isinstance(node, ast.ClassDef):
                lines.append("")
                lines.extend(format_class(node))
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                val = f" = {ast.unparse(node.value)}" if node.value else ""
                lines.append(f"{node.target.id}: {ast.unparse(node.annotation)}{val}")
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if node.value and (
                            target.id == "__all__"
                            or target.id.isupper()
                            or _should_preserve_value(node.value)
                        ):
                            lines.append(f"{target.id} = {ast.unparse(node.value)}")
                        else:
                            lines.append(f"{target.id} = ...")

        result = "\n".join(lines).strip()
        return result or code

    @classmethod
    def extract_js_ts_skeleton(cls, code: str) -> str:
        """Extract TypeScript/JavaScript signatures, interfaces, classes, and exported functions."""
        lines: list[str] = []
        in_multiline_import = False
        import_buffer: list[str] = []

        for line in code.splitlines():
            stripped = line.strip()

            # Handle multi-line imports
            if in_multiline_import:
                import_buffer.append(line)
                if (
                    "from " in line
                    or ";" in line
                    or stripped.endswith("';")
                    or stripped.endswith('";')
                ):
                    lines.extend(import_buffer)
                    import_buffer = []
                    in_multiline_import = False
                continue
            elif stripped.startswith("import ") and (
                "from " not in stripped and not stripped.endswith(";")
            ):
                in_multiline_import = True
                import_buffer = [line]
                continue

            if stripped.startswith(
                ("import ", "export type ", "export interface ", "interface ", "type ")
            ):
                lines.append(line)
            elif re.match(r"^(export\s+)?(default\s+)?(abstract\s+)?class\s+\w+", stripped):
                lines.append(line)
            elif re.match(r"^(export\s+)?(default\s+)?(async\s+)?function\s*\w*", stripped):
                sig = re.sub(r"\{.*$", "{ ... }", line)
                if not sig.endswith("}"):
                    sig += " { ... }"
                lines.append(sig)
            elif re.match(
                r"^(export\s+)?(const|let|var)\s+\w+\s*=\s*(async\s+)?(\([^)]*\)|[a-zA-Z0-9_$]+)\s*=>",
                stripped,
            ):
                sig = re.sub(r"(=>).*$", r"\1 { ... }", line)
                lines.append(sig)
            elif re.match(r"^\w+\??\(.*\)\s*:\s*.*", stripped) or re.match(
                r"^\w+\??\s*:\s*.*", stripped
            ):
                lines.append(line)
        result = "\n".join(lines).strip()
        return result if len(result) > 20 else code

    @classmethod
    def extract_go_skeleton(cls, code: str) -> str:
        """Extract Go package, imports, struct, interface, and func signatures."""
        lines: list[str] = []
        in_import_block = False
        for line in code.splitlines():
            stripped = line.strip()
            if stripped.startswith("package "):
                lines.append(line)
            elif stripped == "import (":
                in_import_block = True
                lines.append(line)
            elif in_import_block:
                lines.append(line)
                if stripped == ")":
                    in_import_block = False
            elif stripped.startswith("import "):
                lines.append(line)
            elif stripped.startswith("type ") and ("struct" in stripped or "interface" in stripped):
                lines.append(line)
            elif stripped.startswith("func "):
                sig = re.sub(r"\{.*$", "{ ... }", line)
                if not sig.endswith("}"):
                    sig += " { ... }"
                lines.append(sig)
        result = "\n".join(lines).strip()
        return result if len(result) > 20 else code

    @classmethod
    def extract_rust_skeleton(cls, code: str) -> str:
        """Extract Rust traits, structs, enums, and fn signatures."""
        lines: list[str] = []
        for line in code.splitlines():
            stripped = line.strip()
            if stripped.startswith("use "):
                lines.append(line)
            elif re.match(r"^(pub\s+)?(struct|enum|trait)\s+\w+", stripped):
                lines.append(line)
            elif re.match(r"^(pub\s+)?(async\s+)?fn\s+\w+", stripped):
                sig = re.sub(r"\{.*$", "{ ... }", line)
                if not sig.endswith("}"):
                    sig += " { ... }"
                lines.append(sig)
        result = "\n".join(lines).strip()
        return result if len(result) > 20 else code
