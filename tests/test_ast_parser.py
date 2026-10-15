"""Tests for ASTParser."""

from focuspack.ast_parser import ASTParser


def test_python_skeleton_extraction():
    sample_code = '''
"""Module docstring."""

import os
from typing import List, Optional

GLOBAL_VAR = "hello"

def helper_function(name: str, count: int = 1) -> str:
    """A helper function."""
    res = name * count
    return res

class UserManager:
    """Manages users in the system."""
    db_name: str = "users.db"

    def __init__(self, host: str):
        self.host = host
        self.connected = True

    async def get_user(self, user_id: int) -> Optional[dict]:
        """Fetch user by id."""
        data = {"id": user_id}
        return data
'''

    skeleton = ASTParser.extract_python_skeleton(sample_code)
    assert '"""\nModule docstring.\n"""' in skeleton
    assert "import os" in skeleton
    assert "from typing import List, Optional" in skeleton
    assert "def helper_function(name: str, count: int = 1) -> str:" in skeleton
    assert '"""A helper function."""' in skeleton
    assert "class UserManager:" in skeleton
    assert '"""Manages users in the system."""' in skeleton
    assert "def __init__(self, host: str):" in skeleton
    assert "async def get_user(self, user_id: int) -> Optional[dict]:" in skeleton
    assert "..." in skeleton
    # Ensure implementation details are stripped
    assert "res = name * count" not in skeleton
    assert "self.connected = True" not in skeleton


def test_python_syntax_error_fallback():
    broken_code = "def invalid_syntax(:"
    fallback = ASTParser.extract_python_skeleton(broken_code)
    assert fallback == broken_code


def test_ts_skeleton_extraction():
    ts_code = """
import { useState } from 'react';
export interface UserProps {
    id: string;
    name: string;
}
export function UserCard(props: UserProps) {
    const [state, setState] = useState(0);
    return <div>{props.name}</div>;
}
"""
    skeleton = ASTParser.extract_js_ts_skeleton(ts_code)
    assert "export interface UserProps" in skeleton
    assert "UserCard" in skeleton
    assert "const [state, setState]" not in skeleton


def test_python_raw_docstring_preservation():
    # click/utils.py edge case: Windows paths in raw docstrings
    code = r'''
def get_app_dir(app_name: str) -> str:
    r"""Returns the config folder for the application.
    Windows (roaming):
      ``C:\Users\<user>\AppData\Roaming\Foo Bar``
    Windows (not roaming):
      ``C:\Users\<user>\AppData\Local\Foo Bar``
    """
    return "dir"
'''
    skeleton = ASTParser.extract_python_skeleton(code)
    import ast

    # Skeletons must be valid parseable Python without raising SyntaxError
    tree = ast.parse(skeleton)
    assert tree is not None
    assert "C:\\Users\\<user>\\AppData" in skeleton or r"C:\Users\<user>\AppData" in skeleton
    assert 'r"""' in skeleton


def test_python_skeleton_constants_and_nested_classes():
    code = """
__all__ = ["OuterClass", "CONFIG_VALUE"]
CONFIG_VALUE = 42

class OuterClass:
    INNER_CONST = "hello"

    class NestedClass:
        def nested_method(self) -> int:
            return 1
"""
    skeleton = ASTParser.extract_python_skeleton(code)
    assert "__all__ =" in skeleton and "OuterClass" in skeleton and "CONFIG_VALUE" in skeleton
    assert "CONFIG_VALUE = 42" in skeleton
    assert "class OuterClass:" in skeleton
    assert "INNER_CONST =" in skeleton and "hello" in skeleton
    assert "class NestedClass:" in skeleton
    assert "def nested_method(self) -> int:" in skeleton


def test_python_skeleton_scoped_imports():
    code = """
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import User

try:
    import fast_json as json
except ImportError:
    import json
"""
    skeleton = ASTParser.extract_python_skeleton(code)
    assert "if TYPE_CHECKING:" in skeleton
    assert "from app.models import User" in skeleton
    assert "try:" in skeleton
    assert "import fast_json as json" in skeleton
    assert "except ImportError:" in skeleton
    assert "import json" in skeleton


def test_ts_skeleton_arrow_functions_and_multiline_imports():
    ts_code = """
import {
    Alpha,
    Beta
} from './alphabet';

export default class MainService {
    run(): void {
        console.log("running");
    }
}

export const helper = async (id: string) => {
    return id.trim();
};
"""
    skeleton = ASTParser.extract_js_ts_skeleton(ts_code)
    assert "import {" in skeleton
    assert "Alpha," in skeleton
    assert "Beta" in skeleton
    assert "} from './alphabet';" in skeleton
    assert "export default class MainService" in skeleton
    assert "export const helper = async (id: string) =>" in skeleton


def test_size_based_method_compression():
    # 5-line function should NOT be compressed with min_lines=15
    short_func = "def short_fn():\n    a = 1\n    b = 2\n    c = 3\n    return a + b + c\n"
    res_short = ASTParser.compress_large_methods_python(short_func, min_lines=15)
    assert "return a + b + c" in res_short

    # 20-line function SHOULD be compressed with min_lines=15
    long_func = (
        "def long_fn():\n" + "".join(f"    x_{i} = {i}\n" for i in range(20)) + "    return x_19\n"
    )
    res_long = ASTParser.compress_large_methods_python(long_func, min_lines=15)
    assert "..." in res_long
    assert "x_19" not in res_long
