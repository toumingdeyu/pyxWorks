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
    ciphertext1 = ciphertext[24:]
    print('ciphertext1', len(ciphertext1), ciphertext1)
    
    ciphertext2 = str(base64.b64decode(ciphertext1))
    print('ciphertext2', len(ciphertext2), ciphertext2)
    
    aes = AES.new(key, AES.MODE_CBC, iv)
    
    plaintext = aes.decrypt(ciphertext2) 
    print('plaintext', plaintext)
    
    return plaintext


ciphertext = str('MTIzMTYwNjIyODU1ODQ1Ng==YmUhEiCutT2VkSlRy67v/s/dVeIl4rAPCqh+DprbsNU=br/')
print('ciphertext', len(ciphertext), ciphertext)

### key and iv must be bytes
iv = base64.b64decode(ciphertext[0:24])
#iv = str.encode(iv)
print('iv', len(iv), iv)

part = iv[3:13] 
print('part', part)

key = part + b'123456789012' + part ### must be 32 char length
#key = str.encode(key)
print('key', len(key), key)

plaintext = decrypt(key, iv, ciphertext)
print(plaintext)


sys.exit(0)





