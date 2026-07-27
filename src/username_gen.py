import random
import string
from typing import List, Iterator
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
    def generate(cls, count: int = 1000, pattern: str = "mixed") -> Iterator[str]:
        generated = set()
        
        if pattern in ('short', 'mixed'):
            chars = string.ascii_lowercase + string.digits
            for length in [2, 3, 4]:
                if len(generated) >= count:
                    break
                for combo in itertools.product(chars, repeat=length):
                    if len(generated) >= count:
                        break
                    username = ''.join(combo)
                    if cls._is_valid(username):
                        generated.add(username)
                        yield username
        
        if pattern in ('words', 'mixed'):
            for word in cls.COMMON_WORDS:
                if len(generated) >= count:
                    break
                for suffix in cls.SUFFIXES:
                    username = f"{word}{suffix}"
                    if cls._is_valid(username) and username not in generated:
                        generated.add(username)
                        yield username
                    for num in range(0, 1000, 11):
                        username = f"{word}{num}"
                        if len(username) <= 32 and cls._is_valid(username) and username not in generated:
                            generated.add(username)
                            yield username
        
        if pattern == 'leet':
            leet_map = {'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 't': '7'}
            for word in cls.COMMON_WORDS[:30]:
                if len(generated) >= count:
                    break
                leet = ''.join(leet_map.get(c, c) for c in word)
                if cls._is_valid(leet) and leet not in generated:
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
