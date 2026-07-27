import string
from typing import List

class UsernameGenerator:
    @staticmethod
    def _is_valid(username: str) -> bool:
        """Strict Discord username validation"""
        if not username:
            return False
        if not (2 <= len(username) <= 32):
            return False
        if not any(c in string.ascii_lowercase for c in username):
            return False
        if username[0] in '._' or username[-1] in '._':
            return False
        if '..' in username or '__' in username or '._' in username or '_.' in username:
            return False
        allowed = set(string.ascii_lowercase + string.digits + '._')
        if not all(c in allowed for c in username):
            return False
        return True

    @classmethod
    def from_file(cls, filepath: str) -> List[str]:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return [line.strip().lower() for line in f if line.strip() and not line.startswith('#') and cls._is_valid(line.strip().lower())]
        except FileNotFoundError:
            return []
