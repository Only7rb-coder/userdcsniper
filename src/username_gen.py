import random
import string
from typing import List, Iterator, Optional, Tuple
import itertools

class UsernameGenerator:
    COMMON_WORDS = [
        "alpha", "beta", "gamma", "neo", "crypto", "dark", "shadow",
        "ghost", "night", "star", "moon", "fire", "ice", "dragon",
        "wolf", "tiger", "hawk", "raven", "fox", "zero", "x", "z",
        "apex", "prime", "elite", "pro", "max", "ultra", "mega",
        "cyber", "tech", "cloud", "code", "byte", "pixel", "flux",
        "pulse", "wave", "void", "nova", "galaxy", "nebula"
    ]
    
    SUFFIXES = ["", "x", "z", "tv", "gg", "yt", "hq", "io", "dev", "ai", "vr", "3d", "nft", "web3"]

    @classmethod
    def _parse_length(cls, length_spec: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Parse length spec: '2' = exact 2, '2-4' = range, '3+' = min 3
        Returns (min_len, max_len)
        """
        length_spec = length_spec.strip()
        if '-' in length_spec:
            parts = length_spec.split('-')
            return int(parts[0]), int(parts[1])
        elif '+' in length_spec:
            return int(length_spec.replace('+', '')), 32
        else:
            exact = int(length_spec)
            return exact, exact

    @classmethod
    def generate(cls, count: int = 1000, pattern: str = "mixed", length: str = "2-32") -> Iterator[str]:
        """
        pattern: short | words | mixed | leet
        length: exact (2), range (2-4), or min (3+)
        """
        min_len, max_len = cls._parse_length(length)
        generated = set()
        
        # Helper to check length
        def in_range(s: str) -> bool:
            return min_len <= len(s) <= max_len

        if pattern in ('short', 'mixed'):
            chars = string.ascii_lowercase + string.digits
            # Only brute-force short lengths if requested
            for length_val in range(max(2, min_len), min(max_len + 1, 5)):
                if len(generated) >= count:
                    break
                for combo in itertools.product(chars, repeat=length_val):
                    if len(generated) >= count:
                        break
                    username = ''.join(combo)
                    if in_range(username) and cls._is_valid(username):
                        generated.add(username)
                        yield username

        if pattern in ('words', 'mixed'):
            for word in cls.COMMON_WORDS:
                if len(generated) >= count:
                    break
                for suffix in cls.SUFFIXES:
                    username = f"{word}{suffix}"
                    if in_range(username) and cls._is_valid(username) and username not in generated:
                        generated.add(username)
                        yield username
                    
                    for num in range(0, 10000, 7):
                        username = f"{word}{num}"
                        if in_range(username) and cls._is_valid(username) and username not in generated:
                            generated.add(username)
                            yield username

        if pattern == 'leet':
            leet_map = {'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 't': '7'}
            for word in cls.COMMON_WORDS[:50]:
                if len(generated) >= count:
                    break
                leet = ''.join(leet_map.get(c, c) for c in word)
                if in_range(leet) and cls._is_valid(leet) and leet not in generated:
                    generated.add(leet)
                    yield leet

    @staticmethod
    def _is_valid(username: str) -> bool:
        if not (2 <= len(username) <= 32):
            return False
        if username[0] in '._' or username[-1] in '._':
            return False
        if '..' in username or '__' in username or '._' in username or '_.' in username:
            return False
        allowed = set(string.ascii_lowercase + string.digits + '._')
        return all(c in allowed for c in username)

    @classmethod
    def from_file(cls, filepath: str) -> List[str]:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return [line.strip().lower() for line in f if line.strip()]
        except FileNotFoundError:
            return []
