#!/usr/bin/python

import sys, os, io, time, binascii, base64, random, json

from Crypto.Cipher import AES
from Crypto.Util import Counter
from Crypto import Random

# AES supports multiple key sizes: 16 (AES128), 24 (AES192), or 32 (AES256).
key_lenght = 32
iv_lenght = 16



def decrypt(key, iv, ciphertext):
    assert len(key) == key_lenght
    assert len(iv) == iv_lenght
    ciphertext = base64.b64decode(ciphertext)
    aes = AES.new(key, AES.MODE_CBC, iv)
    plaintext = aes.decrypt(ciphertext)        
    return plaintext

plaintext = decrypt(key, iv, ciphertext)
print(plaintext)

sys.exit(0)





