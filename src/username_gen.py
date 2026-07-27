import random
import string
from typing import List, Iterator, Optional, Tuple
import itertools

class UsernameGenerator:
    # Words that sound good, have character, might actually be available
    RARE_WORDS = [
        "abyssal", "boreal", "cryo", "drift", "ember", "fable", "glimmer",
        "hollow", "iris", "jolt", "kismet", "lunar", "mire", "nexus", "omen",
        "prism", "quill", "rift", "shroud", "tidal", "umbra", "vox", "wisp",
        "xenon", "yield", "zenith", "aether", "blight", "cinder", "dusk",
        "ethos", "frost", "gale", "hush", "ink", "jade", "keen", "lyric",
        "myth", "noct", "onyx", "pulse", "quasar", "relic", "sol", "thrum",
        "urn", "vex", "wraith", "xylo", "yew", "zeph", "arc", "bolt", "cusp",
        "dirge", "echo", "flint", "goss", "hex", "io", "jinx", "kore", "lux",
        "meld", "nigh", "or", "pact", "quay", "rove", "seer", "tome", "ultra",
        "vial", "weft", "xyst", "yore", "zest"
    ]
    
    COOL_SUFFIXES = ["", "x", "z", "ify", "ism", "oid", "ite", "ine", "ic", "al"]
    
    @classmethod
    def _parse_length(cls, length_spec: str) -> Tuple[Optional[int], Optional[int]]:
        length_spec = length_spec.strip()
        if '-' in length_spec:
            a, b = length_spec.split('-')
            return int(a), int(b)
        elif '+' in length_spec:
            return int(length_spec.replace('+', '')), 32
        else:
            return int(length_spec), int(length_spec)

    @classmethod
    def generate(cls, count: int = 5000, pattern: str = "mixed", length: str = "5-7") -> Iterator[str]:
        min_len, max_len = cls._parse_length(length)
        generated = set()
        
        def ok(s): 
            return min_len <= len(s) <= max_len and cls._is_valid(s)

        # Strategy 1: Rare words + suffixes (highest chance of availability)
        if pattern in ('words', 'mixed'):
            for word in cls.RARE_WORDS:
                if len(generated) >= count:
                    break
                for suffix in cls.COOL_SUFFIXES:
                    variants = [
                        f"{word}{suffix}",
                        f"{suffix}{word}" if suffix else word,
                        f"{word}_{suffix}" if suffix else word,
                        f"{word}.{suffix}" if suffix else word,
                    ]
                    for v in variants:
                        if ok(v) and v not in generated:
                            generated.add(v)
                            yield v
        
        # Strategy 2: Short random with structure (consonant-vowel pattern)
        if pattern in ('short', 'mixed'):
            vowels = "aeiou"
            consonants = "bcdfghjklmnpqrstvwxyz"
            for _ in range(min(count * 2, 10000)):
                if len(generated) >= count:
                    break
                # CVCVC or VCVCV pattern - pronounceable
                pattern_choice = random.choice([
                    lambda: ''.join(random.choice(consonants) if i%2==0 else random.choice(vowels) for i in range(random.randint(min_len, max_len))),
                    lambda: ''.join(random.choice(vowels) if i%2==0 else random.choice(consonants) for i in range(random.randint(min_len, max_len))),
                ])
                username = pattern_choice()
                if ok(username) and username not in generated:
                    generated.add(username)
                    yield username
        
        # Strategy 3: Leet speak on rare words
        if pattern == 'leet':
            leet_map = {'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 't': '7', 'g': '9'}
            for word in cls.RARE_WORDS[:40]:
                if len(generated) >= count:
                    break
                leet = ''.join(leet_map.get(c, c) for c in word)
                if ok(leet) and leet not in generated:
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
    
    @classmethod
    def generate_watchlist_variants(cls, base_names: List[str]) -> List[str]:
        """Generate variations of watchlist names to monitor"""
        variants = set(base_names)
        for name in base_names:
            # Common leet variations
            leet = name.replace('a','4').replace('e','3').replace('i','1').replace('o','0')
            variants.add(leet)
            # With suffixes
            for suffix in ['x', 'z', 'tv', 'gg', 'io']:
                variants.add(f"{name}{suffix}")
                variants.add(f"{name}_{suffix}")
        return [v for v in variants if cls._is_valid(v)]
