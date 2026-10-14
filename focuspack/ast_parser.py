"""
AST & signature extraction module for repodigest.
Produces compressed skeleton outlines of files, reducing token usage by up to 80%
while preserving full architectural, class, and method context for LLMs.
"""

from __future__ import annotations

import ast
import re


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
    def extract_python_skeleton(cls, code: str) -> str:
        """
        Extract clean Python module outline containing imports, classes, methods,
        signatures, docstrings, and type annotations, with bodies replaced by '...'.
        """
        try:
            tree = ast.parse(code)
        except Exception:
            return code  # Fallback to full code if syntax error

        lines: list[str] = []

        # Module docstring
        mod_doc = ast.get_docstring(tree)
        if mod_doc:
            lines.append(f'"""\n{mod_doc}\n"""\n')

        def format_arg(arg: ast.arg) -> str:
            res = arg.arg
            if arg.annotation:
                res += f": {ast.unparse(arg.annotation)}"
            return res

        def format_arguments(args: ast.arguments) -> str:
            parts = []
            # Positional only
            posonly_count = len(args.posonlyargs)
            for a in args.posonlyargs:
                parts.append(format_arg(a))
            if posonly_count > 0:
                parts.append("/")

            # Standard positional
            default_offset = len(args.args) - len(args.defaults)
            for i, a in enumerate(args.args):
                s = format_arg(a)
                if i >= default_offset:
                    default_idx = i - default_offset
                    s += f" = {ast.unparse(args.defaults[default_idx])}"
                parts.append(s)

            # Vararg (*args)
            if args.vararg:
                parts.append(f"*{format_arg(args.vararg)}")
            elif args.kwonlyargs:
                parts.append("*")

            # Keyword-only
            for i, a in enumerate(args.kwonlyargs):
                s = format_arg(a)
                default = args.kw_defaults[i]
                if default is not None:
                    s += f" = {ast.unparse(default)}"
                parts.append(s)

            # Kwarg (**kwargs)
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
                res.append(f'{indent}    """{doc}"""')
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
                res.append(f'{inner_indent}"""{doc}"""')
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
            # Imports / Exports / Type / Interface
            if stripped.startswith(
                ("import ", "export type ", "export interface ", "interface ", "type ")
            ) or re.match(r"^(export\s+)?(abstract\s+)?class\s+\w+", stripped):
                lines.append(line)
            # Function declaration
            elif re.match(r"^(export\s+)?(async\s+)?function\s+\w+", stripped):
                sig = re.sub(r"\{.*$", "{ ... }", line)
                if not sig.endswith("}"):
                    sig += " { ... }"
                lines.append(sig)
            # Method or property signatures inside interfaces/types
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
            elif (
                stripped.startswith("import ")
                or stripped.startswith("type ")
                and ("struct" in stripped or "interface" in stripped)
            ):
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
            if stripped.startswith("use ") or re.match(
                r"^(pub\s+)?(struct|enum|trait)\s+\w+", stripped
            ):
                lines.append(line)
            elif re.match(r"^(pub\s+)?(async\s+)?fn\s+\w+", stripped):
                sig = re.sub(r"\{.*$", "{ ... }", line)
                if not sig.endswith("}"):
                    sig += " { ... }"
                lines.append(sig)
        result = "\n".join(lines).strip()
        return result if len(result) > 20 else code
