#!/usr/bin/python

import sys, os, io, time, binascii, base64, random, json, string

from Crypto.Cipher import AES
from Crypto.Util import Counter
from Crypto import Random

### AES supports multiple key sizes: 16 (AES128), 24 (AES192), or 32 (AES256).
### PY3: string = bytes.decode()
### key and iv must be bytes, key must be 32 char length




def hash_encrypt(text = None, key = None, iv = None):
    if not text: return str()
    if not key:
        key = base64.b64decode(b'cGFpaVVORE9wYWlpVU5ET3BhaWlVTkRPcGFpaVVORE8=')
    try:
        key = str.encode(key)
    except: pass
    if not iv: iv = key[:16]
    assert len(key) == 32
    assert len(iv) == 16
    text += (16-len(text)%16) * " "
    text = str.encode(text)
    cipher = AES.new( key, AES.MODE_CBC, iv )
    return base64.b64encode( cipher.encrypt( text ) )

def hash_decrypt(text = None, key = None, iv = None):
    if not text: return str()
    if not key:
        key = base64.b64decode(b'cGFpaVVORE9wYWlpVU5ET3BhaWlVTkRPcGFpaVVORE8=')
    try:
        key = str.encode(key)
    except: pass
    if not iv: iv = key[:16]
    assert len(key) == 32
    assert len(iv) == 16
    ciphertext = base64.b64decode(text)
    aes = AES.new(key, AES.MODE_CBC, iv)
    plain_text = aes.decrypt(ciphertext).decode('utf-8').strip()
    readable_text = str()
    for c in plain_text:
        if c in string.printable: readable_text += c
    return readable_text

text = 'aa####bb'

cipher_text = hash_encrypt(text)
print(cipher_text)

plain_text = hash_decrypt(cipher_text)
print(plain_text)



sys.exit(0)





