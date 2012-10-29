/*
  A really stupid, brain-dead implementation of EAX mode (hardcoded to use AES
  with 128 bit keys). The idea is that it's easy to verify the code is correct.
  It is not fast. At all. It generates random keys and messages, and dumps
  various things to stdout - the intent of this code is to generate test
  vectors.

  There is a fast EAX implementation in Botan (http://botan.randombit.net)

  Requires OpenSSL 0.9.7 (for the AES support)

     (C) 2003 Jack Lloyd (lloyd@randombit.net)
        This program is free software; you can redistribute it and/or modify it
        under the terms of the GNU General Public License version 2 as
        published by the Free Software Foundation. This program is distributed
        in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
        even the implied warranty of MERCHANTABILITY or FITNESS FOR A
        PARTICULAR PURPOSE.
*/

#include <openssl/aes.h>

#include <string.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

/* PARAMETERS: Play with as desired */
#define MSG_MIN 0 /* anything */
#define MSG_MAX 32  /* anything >= MSG_MIN */
#define NONCE_SIZE 16 /* anything, will tend to be == blocksize of cipher */
#define HEADER_SIZE 8 /* anything */
#define TAG_SIZE 16 /* between 0 and 16 */

#define VECTORS 1 /* how many vectors to print at once */
#define DUMP_INTER 0 /* dump intermediate values */

typedef unsigned char byte;

void do_omac(const byte key[16], const byte data[], int length,
             byte mac[16]);

void do_omac_n(const byte key[16], const byte data[], int length,
             byte mac[16], byte tag);

void do_ctr(const byte key[16], const byte nonce[16],
            byte data[], int length);

void do_eax(const byte key[16], const byte nonce[16],
            const byte data[], int length,
            const byte header[], int h_length);

void dump(const char* name, const byte data[], int length, int always)
   {
   int j;

   if(!always && !DUMP_INTER)
      return;

   printf("%s: ", name);
   for(j = strlen(name); j < 8; j++)
      printf(" ");
   for(j = 0; j != length; j++)
      printf("%02X", data[j]);
   printf("\n");
   }

int main()
   {
   byte key[16]; /* key size is semi-fixed in this version */
   byte nonce[NONCE_SIZE]; /* this can be changed */
   byte message[MSG_MAX]; /* this can be changed */
   byte header[HEADER_SIZE]; /* this can be changed */
   int i, j;

   if(MSG_MIN > MSG_MAX)
      {
      printf("Bad params: MSG_MIN (%d) > MSG_MAX (%d)\n", MSG_MIN, MSG_MAX);
      return 1;
      }

   srand(time(0) ^ (getpid() << 16));

   for(i = 0; i != VECTORS; i++)
      {
      int range = 1 + MSG_MAX - MSG_MIN;
      int msg_size = MSG_MIN + (rand() % range);
      assert(msg_size >= MSG_MIN);
      assert(msg_size <= MSG_MAX);

      for(j = 0; j != sizeof(message); j++)
         message[j] = rand();
      for(j = 0; j != sizeof(key); j++)
         key[j] = rand();
      for(j = 0; j != sizeof(nonce); j++)
         nonce[j] = rand();
      for(j = 0; j != sizeof(header); j++)
         header[j] = rand();

      dump("MSG", message, msg_size, 1);
      dump("KEY", key, sizeof(key), 1);
      dump("IV", nonce, sizeof(nonce), 1);
      dump("HEADER", header, sizeof(header), 1);

      do_eax(key, nonce, message, msg_size, header, sizeof(header));
      printf("\n");
      }

   return 0;
   }

/* The overall EAX transform */
void do_eax(const byte key[16], const byte nonce[16],
            const byte data[], int length,
            const byte header[], int h_length)
   {
   byte mac_nonce[16], mac_data[16], mac_header[16];
   int j;

   /* this copy will be encrypted in CTR mode */
   byte* data_copy = (byte*)malloc(length);
   memcpy(data_copy, data, length);

   do_omac_n(key, nonce, 16, mac_nonce, 0);
   do_omac_n(key, header, h_length, mac_header, 1);
   do_ctr(key, mac_nonce, data_copy, length);
   /* MAC the ciphertext, not the plaintext */
   do_omac_n(key, data_copy, length, mac_data, 2);

   dump("MAC(H)", mac_header, 16, 0);
   dump("MAC(N)", mac_nonce, 16, 0);
   dump("MAC(C)", mac_data, 16, 0);

   printf("CIPHER:   ");
   for(j = 0; j != length; j++)
      printf("%02X", data_copy[j]);
   for(j = 0; j != TAG_SIZE; j++)
      printf("%02X", mac_nonce[j] ^ mac_data[j] ^ mac_header[j]);
   printf("\n");
   }

/* I copied this part from my 'real' OMAC source, so it's possible they are
   both wrong - this needs to be checked carefully.
*/
void poly_double(const byte in[16], byte out[16])
   {
   const int do_xor = (in[0] & 0x80) ? 1 : 0;
   int j;
   byte carry = 0;

   memcpy(out, in, 16);

   for(j = 16; j != 0; j--)
      {
      byte temp = out[j-1];
      out[j-1] = (temp << 1) | carry;
      carry = (temp >> 7);
      }

   if(do_xor)
      out[15] ^= 0x87; /* fixed polynomial for n=128, binary=10000111 */
   }

/* The OMAC parameterized PRF function */
void do_omac_n(const byte key[16], const byte data[], int length,
               byte mac[16], byte tag)
   {
   byte* data_copy = (byte*)malloc(length + 16);

   memset(data_copy, 0, length + 16);
   data_copy[15] = tag;
   memcpy(data_copy + 16, data, length);

   do_omac(key, data_copy, length + 16, mac);
   }

/* The OMAC / pad functions */
void do_omac(const byte key[16], const byte data[], int length,
             byte mac[16])
   {
   AES_KEY aes_key;
   byte L[16] = { 0 }, P[16] = { 0 }, B[16] = { 0 };
   int j;
   int total_len = 0;
   byte* data_padded = 0;
   const byte* xor_pad;

   AES_set_encrypt_key(key, 128, &aes_key);

   AES_encrypt(L, L, &aes_key); /* create L */
   poly_double(L, B); /* B = 2L */
   poly_double(B, P); /* P = 2B = 2(2L) = 4L */

   dump("L", L, 16, 0);
   dump("B", B, 16, 0);
   dump("P", P, 16, 0);

   if(length && length % 16 == 0) /* if of size n, 2n, 3n... */
      total_len = length; /* no padding */
   else
      total_len = length + (16 - length % 16); /* round up to next 16 bytes */

   data_padded = (byte*)malloc(total_len);
   memset(data_padded, 0, total_len);
   memcpy(data_padded, data, length);

   if(total_len != length) /* if add padding */
      data_padded[length] = 0x80;

   dump("OMAC_IN", data, length, 0);
   dump("PADDED", data_padded, total_len, 0);

   /* If no padding, XOR in B, otherwise XOR in P */
   xor_pad = (total_len == length) ? B : P;

   for(j = total_len - 16; j != total_len; j++)
      {
      data_padded[j] ^= *xor_pad;
      xor_pad++;
      }

   dump("POSTXOR", data_padded, total_len, 0);

   assert(total_len % 16 == 0); /* sanity check */
   memset(mac, 0, 16);

   for(j = 0; j != total_len; j += 16)
      {
      int k;
      for(k = 0; k != 16; k++) mac[k] ^= data_padded[j+k];
      dump("C_i", mac, 16, 0);
      AES_encrypt(mac, mac, &aes_key);
      }

   dump("C_m", mac, 16, 0);
   }

/* CTR encryption */
void do_ctr(const byte key[16], const byte nonce[16],
            byte data[], int length)
   {
   AES_KEY aes_key;
   byte state[16]; /* the actual counter */
   byte buffer[16]; /* encrypted counter */
   int j;

   memcpy(state, nonce, 16);

   AES_set_encrypt_key(key, 128, &aes_key);
   /* Initial encryption of the counter */
   AES_encrypt(state, buffer, &aes_key);

   while(length)
      {
      int to_xor = (length < 16) ? length : 16;

      for(j = 0; j != to_xor; j++)
         data[j] ^= buffer[j];
      data += to_xor;
      length -= to_xor;

      /* Compute E(counter++) */
      for(j = 15; j >= 0; j--)
         if(++state[j])
            break;
      AES_encrypt(state, buffer, &aes_key);
      }
   }

