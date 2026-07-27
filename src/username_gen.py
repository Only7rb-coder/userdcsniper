import random
import string
from typing import List, Iterator
import itertools

class UsernameGenerator:
    """Generate username candidates based on patterns."""
    
    # Discord username rules: 2-32 chars, a-z, 0-9, _, .
    # Cannot start/end with . or _, no consecutive . or _
    
    COMMON_WORDS = [
        "alpha", "beta", "gamma", "delta", "neo", "crypto", "dark", "light",
        "shadow", "ghost", "phantom", "night", "star", "moon", "sun", "sky",
        "fire", "ice", "thunder", "storm", "dragon", "wolf", "tiger", "hawk",
        "raven", "fox", "bear", "lion", "eagle", "shark", "viper", "cobra",
        "zero", "one", "x", "z", "v", "k", "j", "q", "apex", "prime", "elite",
        "pro", "max", "ultra", "mega", "super", "hyper", "meta", "cyber",
        "tech", "net", "web", "cloud", "data", "code", "byte", "bit", "pixel",
        "vector", "matrix", "core", "node", "link", "flux", "pulse", "wave",
        "rift", "void", "null", "sync", "dash", "bolt", "spark", "flash",
        "blaze", "frost", "nova", "comet", "cosmos", "galaxy", "nebula", "quasar"
    ]
    
    POPULAR_SUFFIXES = ["", "x", "z", "tv", "gg", "yt", "hq", "io", "dev", "bot", "ai", "vr", "xr", "3d", "nft", "dao", "web3", "defi", "gm", "wagmi"]
    
    @classmethod
    def generate(cls, count: int = 1000, pattern: str = "mixed") -> Iterator[str]:
        """
        Patterns:
        - 'short': 2-4 chars (OG style)
        - 'words': dictionary words + suffixes
        - 'mixed': combination strategies
        - 'leet': l33t speak variations
        """
        generated = set()
        
        if pattern in ('short', 'mixed'):
            # Short usernames (2-4 chars) - highly valuable
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
            # Word-based
            for word in cls.COMMON_WORDS:
                if len(generated) >= count:
                    break
                for suffix in cls.POPULAR_SUFFIXES:
                    username = f"{word}{suffix}"
                    if cls._is_valid(username) and username not in generated:
                        generated.add(username)
                        yield username
                    
                    # Add numbers
                    for num in range(0, 1000, 7):  # Skip by 7 for variety
                        username = f"{word}{num}"
                        if len(username) <= 32 and cls._is_valid(username) and username not in generated:
                            generated.add(username)
                            yield username
        
        if pattern == 'leet':
            # L33t variations of common words
            leet_map = {'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 't': '7'}
            for word in cls.COMMON_WORDS[:50]:
                if len(generated) >= count:
                    break
                leet = ''.join(leet_map.get(c, c) for c in word)
                if cls._is_valid(leet) and leet not in generated:
                    generated.add(leet)
                    yield leet
    
    @staticmethod
    def _is_valid(username: str) -> bool:
        """Validate Discord username format."""
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
        """Load usernames from file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return [line.strip().lower() for line in f if line.strip()]
        except FileNotFoundError:
            return []