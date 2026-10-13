"""Tests for ASTParser."""

from repodigest.ast_parser import ASTParser


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
