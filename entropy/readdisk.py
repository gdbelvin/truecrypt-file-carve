#!/usr/bin/env python3
import sys
import os
import math
import binascii

SECTOR_SIZE = 512

def dbg(msg):
    if False:
        print (msg)

def main(path = '/dev/sda'):
    dbg("Opening %s" % path)
    disk = open(path, 'rb')
    
    partstart = 512923383
    partend   = 976768064
    size      = 100 * (1024 * 1024 * 1024)  / SECTOR_SIZE # Gigabytes in sectors
    s, e = getstart(disk, partstart, partend, size)

    binarysearch(s, e, disk)

def getstart(disk, start, end, size):
    ilimit    = math.log(size, 2)
    last = 0

    i = 0
    e = 1
    offset = start
    last_end = end
    while True:
        x = 2**i + offset
        e = entropysector(disk, x)
        data = readsector(disk, x, 1)
        e = entropytest(data)
        if (i >= ilimit): 
            return (last_end, offset)
            

        if (i == 0) or (i > 14):
            print("%2d: %d: %f %s" % (i, x, e, binascii.hexlify(data[0:16])))

        if (abs(last - e) > 0.3):
            last_end = 2**(i-1) + offset
            offset = x
            i = 0
        else:
            i += 1
        last = e

def binarysearch(start, end, disk):
    print("binary search between %d - %d " % (start, end))
    
    lo, hi = start, end 
    value = 0.9
    while lo <= hi:
        mid = (lo + hi) / 2
        if entropysector(disk, mid) < value:
            lo = mid + 1
        elif value < entropysector(disk, mid):
            hi = mid - 1
        else:
            return mid

    print ("found %d" % mid)
    e, data = entropysectordata(disk, mid -1)
    print("    %d: %f %s" % ( mid-1, e, binascii.hexlify(data[0:16])))
    e, data = entropysectordata(disk, mid )
    print("    %d: %f %s" % ( mid, e, binascii.hexlify(data[0:16])))
    e, data = entropysectordata(disk, mid+1 )
    print("    %d: %f %s" % ( mid+1, e, binascii.hexlify(data[0:16])))
          
    return None

def entropysectordata(disk, sector):
    sector = int(sector)
    data = readsector(disk, sector, 1)
    return (entropytest(data), data)

def entropysector(disk, sector):
    sector = int(sector)
    data = readsector(disk, sector, 1)
    return entropytest(data)

def entropytest(data):

    byte_counts = [0] * 256
    total = len(data)
    entropy = 0

    for byte in data:
        byte_counts[byte] += 1

    for count in byte_counts:
        # If no bytes of this value were seen in the value, it doesn't affect
        # the entropy of the file.
        if count == 0:
            continue
        # p is the probability of seeing this byte in the file, as a floating-
        # point number
        p = 1.0 * count / total
        entropy -= p * math.log(p, 256)
    
    return entropy


def readsector(disk, sector, length):
    '''Length is in sectors'''
    disk.seek(sector * SECTOR_SIZE)
    return disk.read(length * SECTOR_SIZE)



if __name__ == "__main__":
    main()
