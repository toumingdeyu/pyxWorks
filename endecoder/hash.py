#!/usr/bin/python

import sys, os, io, time



if sys.version_info.major >= 3 and sys.version_info.minor >= 6:
    ### pip install pycryptodomex

    from hashlib import md5
    from base64 import b64decode
    from base64 import b64encode

    from crypto.Cipher import AES
    from crypto.Random import get_random_bytes
    from crypto.Util.Padding import pad, unpad


    class AESCipher:
        def __init__(self, key):
            self.key = md5(key.encode('utf8')).digest()

        def encrypt(self, data):
            iv = get_random_bytes(AES.block_size)
            self.cipher = AES.new(self.key, AES.MODE_CBC, iv)
            return b64encode(iv + self.cipher.encrypt(pad(data.encode('utf-8'), 
                AES.block_size)))

        def decrypt(self, data):
            raw = b64decode(data)
            self.cipher = AES.new(self.key, AES.MODE_CBC, raw[:AES.block_size])
            return unpad(self.cipher.decrypt(raw[AES.block_size:]), AES.block_size)


    if __name__ == '__main__':

        print('TESTING ENCRYPTION')
        msg = input('Message...: ')
        pwd = input('Password..: ')
        print('Ciphertext:', AESCipher(pwd).encrypt(msg).decode('utf-8'))

        print('\nTESTING DECRYPTION')
        cte = input('Ciphertext: ')
        pwd = input('Password..: ')
        print('Message...:', AESCipher(pwd).decrypt(cte).decode('utf-8'))




elif sys.version_info.major <= 2:
    ### unix: pip install pycrypto ###
    ### windows: easy_install http://www.voidspace.org.uk/downloads/pycrypto26/pycrypto-2.6.win-amd64-py2.7.exe ###

    ### https://techtutorialsx.com/2018/04/09/python-pycrypto-using-aes-128-in-ecb-mode/ ###        
    from Crypto.Cipher import AES
     
    key = 'abcdefghijklmnop'
     
    cipher = AES.new(key, AES.MODE_ECB)
    msg =cipher.encrypt('TechTutorialsX!!TechTutorialsX!!')
    print (type(msg))
     
    print(msg.encode("hex"))
     
    decipher = AES.new(key, AES.MODE_ECB)
    print(decipher.decrypt(msg))
