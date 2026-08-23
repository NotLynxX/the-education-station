#!/usr/bin/env python3
"""
Generates the SHA-256 hash for any of this site's secrets (the reveal
phrase, the edit code, or the admin trigger word), so you can swap in
your own without ever putting the real value in plain text inside
index.html.

Usage:
    python3 hash_code.py

Then paste the value you want when prompted, copy the hash it prints,
and paste it into index.html in place of the matching constant:
  - REVEAL_HASH    (typed into the AP search bar to open the resource library)
  - keyHashB       (the edit-mode code)
  - trigHashB      (the hidden word typed to bring up the edit-code screen -
                     also update trigLenB to match the new word's length)
"""

import hashlib
import getpass

if __name__ == "__main__":
    code = getpass.getpass("Type the new value (input hidden), then press Enter: ")
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
    print("\nYour hash (paste this into index.html):\n")
    print(digest)
    print()
