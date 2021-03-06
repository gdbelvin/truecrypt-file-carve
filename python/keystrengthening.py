## keystrengthening.py - PBKDF2 algorithm.
## Copyright (c) 2008 Bjorn Edstrom <be@bjrn.se>
##
## Permission is hereby granted, free of charge, to any person
## obtaining a copy of this software and associated documentation
## files (the "Software"), to deal in the Software without
## restriction, including without limitation the rights to use,
## copy, modify, merge, publish, distribute, sublicense, and/or sell
## copies of the Software, and to permit persons to whom the
## Software is furnished to do so, subject to the following
## conditions:
##
## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.
##
## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
## OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
## HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
## WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
## FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
## OTHER DEALINGS IN THE SOFTWARE.
## --
## Changelog
## Jan 4 2008: Initial version. Plenty of room for improvements.

try:
    import psyco
    psyco.full()
except ImportError:
    pass

import struct
import math

import hashlib
import ripemd
import whirlpool

#
# Hash funcs.
#

def HASH_SHA1(data):
    return hashlib.sha1(data).digest()

def HASH_WHIRLPOOL(data):
    return whirlpool.new(data).digest()

def HASH_RIPEMD160(data):
    return ripemd.new(data).digest()

def hexdigest(S):
    tmp = ''
    for s in S:
        tmp += '%02x' % ord(s)
    return tmp

#
# HMAC funcs.
# http://en.wikipedia.org/wiki/HMAC
#

def HMAC(hash_func, hash_block_size, key, message):
    assert bytes == type(message)
    assert bytes == type(key)
    if len(key) > hash_block_size:
        key = hash_func(key)
    if len(key) < hash_block_size:
        key += b'\x00' * (hash_block_size - len(key))
    assert len(key) == hash_block_size
    ipad = b''
    opad = b''
    for i in range(hash_block_size):
        ipad += bytes([0x36 ^ key[i]])
        opad += bytes([0x5c ^ key[i]])
    return hash_func(opad + hash_func(ipad + message))

def HMAC_SHA1(key, message):
    return HMAC(HASH_SHA1, 64, key, message)
    
def HMAC_RIPEMD160(key, message):
    return HMAC(HASH_RIPEMD160, 64, key, message)
    
def HMAC_WHIRLPOOL(key, message):
    return HMAC(HASH_WHIRLPOOL, 64, key, message)

#
# PBKDF2.
# http://www.ietf.org/rfc/rfc2898.txt
#
import numpy
def xor_string(aa,bb):
    b = numpy.fromstring(bb, dtype=numpy.uint32)
    numpy.bitwise_xor(numpy.frombuffer(aa,dtype=numpy.uint32), b, b)
    return b.tostring()


def PBKDF2(hmacfunc, password, salt, iterations, derivedlen):
    """Derive keys using the PBKDF2 key strengthening algorithm."""
    assert bytes == type(password)
    hLen = len(hmacfunc(b'', b'')) # digest size
    l = int(math.ceil(derivedlen / float(hLen)))
    r = derivedlen - (l - 1) * hLen
    def F(P, S, c, i):
        U_prev = hmacfunc(P, S + struct.pack('>L', i))
        res = U_prev
        for cc in range(2, c+1):
            U_c = hmacfunc(P, U_prev)
            res = xor_string(res, U_c)
            U_prev = U_c
        return res
    tmp = b''
    i = 1
    while True:
        tmp += F(password, salt, iterations, i)
        if len(tmp) > derivedlen:
            break
        i += 1
    return tmp[0:derivedlen]

#
# Tests.
# http://tools.ietf.org/html/rfc2202
#

assert HMAC_SHA1(b'\x0b'*20, b"Hi There") == b"\xb6\x17\x31\x86\x55\x05\x72\x64\xe2\x8b\xc0\xb6\xfb\x37\x8c\x8e\xf1\x46\xbe\x00"
assert HMAC_SHA1(b'\xaa'*80, b"Test Using Larger Than Block-Size Key and Larger Than One Block-Size Data") == b"\xe8\xe9\x9d\x0f\x45\x23\x7d\x78\x6d\x6b\xba\xa7\x96\x5c\x78\x08\xbb\xff\x1a\x91"
assert HMAC_SHA1(b"\x50\x51\x52\x53\x54\x55\x56\x57\x58\x59\x5a\x5b\x5c\x5d\x5e\x5f\x60\x61\x62\x63\x64\x65\x66\x67\x68\x69\x6a\x6b\x6c\x6d\x6e\x6f\x70\x71\x72\x73\x74\x75\x76\x77\x78\x79\x7a\x7b\x7c\x7d\x7e\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3", b"Sample #3") == b"\xbc\xf4\x1e\xab\x8b\xb2\xd8\x02\xf3\xd0\x5c\xaf\x7c\xb0\x92\xec\xf8\xd1\xa3\xaa"
assert HMAC_SHA1(b"\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b", b"Hi There") == b"\xb6\x17\x31\x86\x55\x05\x72\x64\xe2\x8b\xc0\xb6\xfb\x37\x8c\x8e\xf1\x46\xbe\x00"
assert HMAC_SHA1(b"Jefe", b"what do ya want for nothing?") == b"\xef\xfc\xdf\x6a\xe5\xeb\x2f\xa2\xd2\x74\x16\xd5\xf1\x84\xdf\x9c\x25\x9a\x7c\x79"
assert HMAC_SHA1(b'\xaa'*20, b'\xdd'*50) == b"\x12\x5d\x73\x42\xb9\xac\x11\xcd\x91\xa3\x9a\xf4\x8a\xa1\x7b\x4f\x63\xf1\x75\xd3"
assert HMAC_RIPEMD160(b"\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99\xaa\xbb\xcc\xdd\xee\xff\x01\x23\x45\x67", b"message digest") == b"\xf8\x36\x62\xcc\x8d\x33\x9c\x22\x7e\x60\x0f\xcd\x63\x6c\x57\xd2\x57\x1b\x1c\x34"
assert HMAC_RIPEMD160(b"\x01\x23\x45\x67\x89\xab\xcd\xef\xfe\xdc\xba\x98\x76\x54\x32\x10\x00\x11\x22\x33", b"12345678901234567890123456789012345678901234567890123456789012345678901234567890") == b"\x85\xf1\x64\x70\x3e\x61\xa6\x31\x31\xbe\x7e\x45\x95\x8e\x07\x94\x12\x39\x04\xf9"
assert HMAC_WHIRLPOOL(b"\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99\xAA\xBB\xCC\xDD\xEE\xFF\x01\x23\x45\x67\x89\xAB\xCD\xEF\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99\xAA\xBB\xCC\xDD\xEE\xFF\x01\x23\x45\x67\x89\xAB\xCD\xEF\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99\xAA\xBB\xCC\xDD\xEE\xFF", b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq") == b"\x03\x91\xd2\x80\x00\xb6\x62\xbb\xb8\xe6\x23\x3e\xe8\x6c\xf2\xb2\x84\x74\x4c\x73\x8b\x58\x00\xba\x28\x12\xed\x52\x6f\xe3\x15\x3a\xb1\xba\xe7\xe2\x36\xbe\x96\x54\x49\x3f\x19\xfa\xce\xa6\x44\x1f\x60\xf5\xf0\x18\x93\x09\x11\xa5\xe5\xce\xd8\xf2\x6a\xbf\xa4\x02"
assert PBKDF2(HMAC_SHA1, b"password", b"\x12\x34\x56\x78", 5, 4) == b'\x5c\x75\xce\xf0'
assert PBKDF2(HMAC_RIPEMD160, b"password", b"\x12\x34\x56\x78", 5, 4) == b'\x7a\x3d\x7c\x03'
assert PBKDF2(HMAC_WHIRLPOOL, b"password", b"\x12\x34\x56\x78", 5, 4) == b'\x50\x7c\x36\x6f'
