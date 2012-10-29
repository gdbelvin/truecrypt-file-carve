import truecrypt
from rijndael import Rijndael
import unittest
import binascii
import xts

class XTSTest(unittest.TestCase):
	def setUp(self):
		self.cipher = truecrypt.CipherChain([Rijndael])
	
	def test_laj(self):
		L  = binascii.unhexlify(b"f142434445464748494a4b4c4d4e4f50")
		actual = xts.Laj(L, 0)
		self.assertEqual(L, actual)
		actual = xts.Laj(L, 1)
		expected = 130952455433044198268351453357118627367 
		expected = expected.to_bytes(16, 'big')
		self.assertEqual(expected, actual)
		
	def test_v1(self):
		dataunit = 0
		blocknum = 0 
		key =                    b"abcdefghijklmnopabcdefghijklmnop"
		ct  = binascii.unhexlify(b"0dd7fdac73180383cab81f81f63ce69a")
		pt  = binascii.unhexlify(b"4142434445464748494a4b4c4d4e4f50")

		decrypt  = b''
		decrypt += xts.XTS(self.cipher.decrypt, key, dataunit, ct)
		self.assertEqual(pt, decrypt)


if __name__ == "__main__":
	unittest.main()

