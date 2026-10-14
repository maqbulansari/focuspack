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
    if "\\" in doc:
        if is_module:
            candidate = f'r"""\n{doc}\n"""'
        else:
            candidate = f'{indent}r"""{doc}"""'
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=SyntaxWarning)
                ast.parse(f"def _():\n    {candidate.strip()}\n")
            return [candidate]
        except Exception:
            escaped = doc.replace("\\", "\\\\")
            if '"""' in escaped:
                escaped = escaped.replace('"""', r"\"\"\"")
            if is_module:
                return [f'"""\n{escaped}\n"""']
            return [f'{indent}"""{escaped}"""']
    else:
        if '"""' in doc:
            escaped = doc.replace('"""', r"\"\"\"")
            if is_module:
                return [f'"""\n{escaped}\n"""']
            return [f'{indent}"""{escaped}"""']
        if is_module:
            return [f'"""\n{doc}\n"""']
        return [f'{indent}"""{doc}"""']


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
                # Check if body is large (more than min_lines statements)
                if len(node.body) > 3 or (
                    hasattr(node, "end_lineno")
                    and hasattr(node, "lineno")
                    and (node.end_lineno - node.lineno) > min_lines
                ):
                    doc = ast.get_docstring(node)
                    new_body = []
                    if doc:
                        new_body.append(ast.Expr(value=ast.Constant(value=doc)))
                    new_body.append(ast.Expr(value=ast.Constant(value=Ellipsis)))
                    node.body = new_body
                return node

            def visit_AsyncFunctionDef(self, node):
                self.generic_visit(node)
                if len(node.body) > 3 or (
                    hasattr(node, "end_lineno")
                    and hasattr(node, "lineno")
                    and (node.end_lineno - node.lineno) > min_lines
                ):
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

        def format_arg(arg: ast.arg) -> str:
            res = arg.arg
            if arg.annotation:
                res += f": {ast.unparse(arg.annotation)}"
            return res

        def format_arguments(args: ast.arguments) -> str:
            parts = []
            posonly_count = len(args.posonlyargs)
            for a in args.posonlyargs:
                parts.append(format_arg(a))
            if posonly_count > 0:
                parts.append("/")

            default_offset = len(args.args) - len(args.defaults)
            for i, a in enumerate(args.args):
                s = format_arg(a)
                if i >= default_offset:
                    default_idx = i - default_offset
                    s += f" = {ast.unparse(args.defaults[default_idx])}"
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
                elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    val = f" = {ast.unparse(item.value)}" if item.value else ""
                    res.append(
                        f"{inner_indent}{item.target.id}: {ast.unparse(item.annotation)}{val}"
                    )
                    has_body = True
                elif isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            res.append(f"{inner_indent}{target.id} = ...")
                            has_body = True

            if not has_body:
                res.append(f"{inner_indent}...")
            return res

        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                lines.append(ast.unparse(node))
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
                        lines.append(f"{target.id} = ...")

        result = "\n".join(lines).strip()
        return result or code

    @classmethod
    def extract_js_ts_skeleton(cls, code: str) -> str:
        """Extract TypeScript/JavaScript signatures, interfaces, classes, and exported functions."""
        lines: list[str] = []
        for line in code.splitlines():
            stripped = line.strip()
            if stripped.startswith(
                ("import ", "export type ", "export interface ", "interface ", "type ")
            ):
                lines.append(line)
            elif re.match(r"^(export\s+)?(abstract\s+)?class\s+\w+", stripped):
                lines.append(line)
            elif re.match(r"^(export\s+)?(async\s+)?function\s+\w+", stripped):
                sig = re.sub(r"\{.*$", "{ ... }", line)
                if not sig.endswith("}"):
                    sig += " { ... }"
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
