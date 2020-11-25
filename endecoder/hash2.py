#!/usr/bin/python

import sys, os, io, time, binascii, base64, random, json, string

from Crypto.Cipher import AES
from Crypto.Util import Counter
from Crypto import Random

# AES supports multiple key sizes: 16 (AES128), 24 (AES192), or 32 (AES256).
key_lenght = 32
iv_lenght = 16


### key and iv must be bytes, key must be 32 char length
key = "" 
key = str.encode(key)

iv = key[:16]

def encrypt(key, iv, text):
    cipher = AES.new( key, AES.MODE_CBC, iv )
    return base64.b64encode( cipher.encrypt( text ) ) 

def decrypt(key, iv, ciphertext):
    assert len(key) == key_lenght
    assert len(iv) == iv_lenght
    ciphertext = base64.b64decode(ciphertext)
    aes = AES.new(key, AES.MODE_CBC, iv)
    plain_text = aes.decrypt(ciphertext).decode('utf-8').strip()
    readable_text = str()
    for c in plain_text:
        if c in string.printable: readable_text += c    
    return readable_text 

text = ''
text += (16-len(text)%16) * " "
text = str.encode(text)

cipher_text = encrypt(key, iv, text)
print(cipher_text)

plain_text = decrypt(key, iv, cipher_text)
print(plain_text)



sys.exit(0)





