## xts.py - The XTS cryptographic mode.
## Copyright (c) 2012 Gary Belvin <gbelvin1@jhu.edu>
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

try:
    import psyco
    psyco.full()
except ImportError:
    pass

from gf2n import *

def str2int(str):
    return int.from_bytes(str, 'big')

import math
def int2str(N):
    l = math.ceil(N.bit_length() / 8)
    return N.to_bytes(l,'big')

import numpy
def xorstring16(aa,bb):
    b = numpy.fromstring(bb, dtype=numpy.uint32)
    numpy.bitwise_xor(numpy.frombuffer(aa,dtype=numpy.uint32), b, b)
    return b.tostring()

alpha = 2
def Laj(L, j):
    #L<<1 xor (135 * MSB(L)) eq. 6.1 
    if(j == 0):
        return L
    else:
        l = str2int(L)
        l1 = (l << 1) & 0x7fffffffffffffffffffffffffffffff
        r = l1 ^  ( 135 * (l >> 127) )
        return int2str(r)

def XEX2(Enc, xtskey, i, j, X):
    assert len(xtskey) == 32
    K1 = str2int(xtskey)
    K2 = str2int(xtskey>>128)

    L = Enc(K2, i)
    D = Laj(L, j)
    #return Enc(K1, (X xor D)) xor D
    return xorstring(Enc(K1, xorstring(X, D)), D)

# D = (E_K2 (n) * alpha ^ i)
# C_i = E_K1(P_i ^ D) ^ D

# Note that cipherfunc = E_K1, that is the key should already be set in E.
# xtskey = K2.
def XTS(cipherfunc, xtskey, i, j, block):
    """Perform a XTS operation."""
    assert len(block) == 16

    # C_i = E_K1(P_i ^ K2i) ^ K2i
    K2i = int2str(gf2pow128mul(K2, i))
    K2i = b'\x00' * (16 - len(K2i)) + K2i
    return xorstring16(K2i, cipherfunc(xorstring16(K2i, block)))

def XTSMany(cipherfunc, xtskey, i, blocks):
    length = len(blocks)
    assert length % 16 == 0
    data = b''
    for j in range(length // 16):
        data += XEX2(cipherfunc, xtskey, i, j, blocks[0:16])
        blocks = blocks[16:]
    return data
    #TODO: handle partial blocks with ciphertext stealing
