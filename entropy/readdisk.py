#!/usr/bin/env python3
import sys
import os
import math
import binascii
import logging

SECTOR_SIZE = 512


logger = logging.getLogger("entropy")
logging.basicConfig(level=logging.INFO,
                    handlers=[logging.FileHandler("example1.log"),
                              logging.StreamHandler()])
                   

class Finder(object):
    def sizeof_fmt(self, num):
        for x in ['bytes','KB','MB','GB']:
            if num < 1024.0:
                return "%3.1f%s" % (num, x)
            num /= 1024.0
        return "%3.1f%s" % (num, 'TB')

    def print_sec(self, f, disk, sector):
        data = self.readsector(disk, sector, 1)
        print("%d|%d:%s %s" % (sector, sector*SECTOR_SIZE,
                    f(data), binascii.hexlify(data[0:16])) )

    def findBlocks(self, path, start=0,
                   size = 200 * (1024 * 1024 * 1024) ):
        logger.debug("Opening %s" % path)
        disk = open(path, 'rb')
        end = os.path.getsize(path)
        
        def pos(data):
            return self.getEntropy(data) > 0.9

        ranges = []
        while True:
            result = self.logSearchContiguous(disk, start, end, size, pos)
            logger.debug("Found: (%s, %s) - (%s, %s) %s" % 
                          (self.sizeof_fmt(result[0][0]),
                           self.sizeof_fmt(result[0][1]),
                           self.sizeof_fmt(result[1][0]),
                           self.sizeof_fmt(result[1][1]),
                           self.sizeof_fmt(result[1][1] - result[0][0])))
            if result == ((0,0),(0,0)):
                break
            else:
                end_ref = self.refineEdge(disk, result[1][0], result[1][1], pos)
                start_ref = self.refineEdge(disk, result[0][1], result[0][0], pos)
                self.print_sec(pos, disk, int(start_ref/SECTOR_SIZE) - 1)
                self.print_sec(pos, disk, int(start_ref/SECTOR_SIZE) )
                self.print_sec(pos, disk, int(start_ref/SECTOR_SIZE) + 1)
                logger.info("R:(%d, %d) (%d, %d) (%s - %s: %s)" % (
                            start_ref, end_ref, 
                            start_ref/SECTOR_SIZE, end_ref/SECTOR_SIZE, 
                            self.sizeof_fmt(start_ref),
                            self.sizeof_fmt(end_ref),
                            self.sizeof_fmt(end_ref-start_ref)
                            ))
                start = result[1][1] 
                
                # Convert to sectors
                ranges.append((start_ref, end_ref, end_ref-start_ref))
        return ranges

    
    def logSearchContiguous(self, disk, start, end, min_size, f):
        '''
        Searches for a contiguous region of true values of f
        returns the byte offset of the found location
        disk    - file to search
        start   - byte offset to start search
        end     - byte offset to end search
        size    - the minimum size of the object to search for in bytes
        f       - a function(data) that returns true or false 
        '''
        logger.debug("search: %s to %s for %s" % (self.sizeof_fmt(start),
                                             self.sizeof_fmt(end),
                                             self.sizeof_fmt(min_size)))
        end_sector = math.ceil(end / SECTOR_SIZE)
        min_size_sector = math.ceil(min_size / SECTOR_SIZE)
        start = math.ceil(start / SECTOR_SIZE)

        i = 0
        size = 2**i
        sector = size + start        
        last_true_sector=0
        last_false_sector=start
        start_range = (0, 0)
        end_range   = (0, 0)
        last_value = False
        min_sample = int(3*1024 * 1024 * 1024 / SECTOR_SIZE)

        while sector < end_sector:
            data = self.readsector(disk, sector, 1)
            value = f(data)

            #False to True
            if (not last_value and value):
                start_range = (last_false_sector, sector)
                end_range = (0,0)
                #re-base for the next contiguous section
                logger.debug("%2d:%d\t %s->%s: %s" % (i, sector, last_value, value, 
                                                    start_range))
                start = sector
                i = 0
               
            #True to false
            elif(last_value and not value):
                end_range = (last_true_sector, sector)
                #re-base for the next contiguous section
                logger.debug("%2d:%d\t %s->%s: %s %s" % (i, sector, last_value, value, 
                                                    start_range, end_range))
                start = sector
                i = 0
            
            #True to True
            #False to False
            #  Continue exponentially searching
            
            #End condition
            if( end_range[1] - start_range[0] >= min_size_sector):
                break

            #Advance counter
            if(value):
                last_true_sector = sector
            else:
                last_false_sector = sector
            last_value = value

            i = i+1
            size_exp = 2**i
            size_lin = min_sample * i
            # sample at least every GB, after a ?certain? point
            size = min (size_exp, size_lin)
            sector = size + start        

        #Convert back to bytes
        return ((start_range[0] * SECTOR_SIZE, start_range[1] * SECTOR_SIZE),
                ( end_range[0]  * SECTOR_SIZE, end_range[1] * SECTOR_SIZE))

    def refineEdge(self, disk, start, end, f):
        '''Finds the edge of a contiguous block of data
           Finds the next false value from start'''
        start_sec = math.ceil(start / SECTOR_SIZE)
        end_sec = math.ceil(end / SECTOR_SIZE)

        i = 0
        #Sanity Check
        data = self.readsector(disk, start_sec, 1)
        value = f(data)
        if not value:
            raise Exception("Input data is not contiguous")

        if(start < end):
            sector = start_sec + 2**i 
        else:
            sector = start_sec - 2**i

        while sector <= end_sec if(start < end) else sector >= end_sec:
            data = self.readsector(disk, sector, 1)
            value = f(data)
            logger.debug("%d: %d %d %s %s" % (i, sector, sector*SECTOR_SIZE, 
                        value, binascii.hexlify(data[0:8]) ))
            if (not value):
                if(i == 0):
                    #return last true value
                    if(start < end):
                        last_true_sec  = sector - 1
                    else:
                        last_true_sec = sector + 1
                    return last_true_sec * SECTOR_SIZE
                #rebase
                logger.debug("rebasing, %d" % i)
                if(start < end):
                    start_sec = start_sec + 2**(i -1)
                else:
                    start_sec = start_sec - 2**(i -1)
                i = 0
            else:
                i = i+1

            if(start < end):
                sector = start_sec + 2**i 
            else:
                sector = start_sec - 2**i

        raise Exception("No edge found")

    def binarysearch(self, start, end, disk):
        logger.debug("binary search between %d - %d " % (start, end))
        
        lo, hi = start, end 
        value = 0.9
        mid = 0
        while lo <= hi:
            mid = (lo + hi) / 2
            if self.entropysector(disk, mid) < value:
                lo = mid + 1
            elif value < self.entropysector(disk, mid):
                hi = mid - 1
            else:
                return mid

        mid = int(mid)
        logger.info ("found %d" % mid)
        e, data = self.entropysectordata(disk, mid -1)
        logger.debug("\t%d: %f %s" % ( mid-1, e, binascii.hexlify(data[0:16])))
        e, data = self.entropysectordata(disk, mid )
        logger.debug("\t%d: %f %s" % ( mid, e, binascii.hexlify(data[0:16])))
        e, data = self.entropysectordata(disk, mid+1 )
        logger.debug("\t%d: %f %s" % ( mid+1, e, binascii.hexlify(data[0:16])))
              
        return mid

    def entropysectordata(self, disk, sector):
        sector = int(sector)
        data = self.readsector(disk, sector, 1)
        return (self.entropytest(data), data)

    def entropysector(self, disk, sector):
        sector = int(sector)
        data = self.readsector(disk, sector, 1)
        return self.entropytest(data)

    def getEntropy(self, data):
        byte_counts = [0] * 256
        total = len(data)
        entropy = 0

        for byte in data:
            byte_counts[byte] += 1

        for count in byte_counts:
            # If no bytes of this value were seen in the value, it doesn't
            # affect the entropy of the file.
            if count == 0:
                continue
            # p is the probability of seeing this byte in the file, as a
            # floating- point number
            p = 1.0 * count / total
            entropy -= p * math.log(p, 256)
        
        return entropy


    def readsector(self, disk, sector, length):
        '''Length is in sectors'''
        disk.seek(sector * SECTOR_SIZE)
        return disk.read(length * SECTOR_SIZE)

def get_sizeof_fmt(fmtstr):
    j = 0
    for i in range(len(fmtstr)):
        if (not fmtstr[i].isdigit()):
            j = i-1
            break

    num = fmtstr[0:i]
    unit = fmtstr[i:]
    units = {'bytes': 1,
             'KB'   : 1024,
             'MB'   : 1024 * 1024,
             'GB'   : 1024 * 1024 * 1024,
             'TB'   : 1024 * 1024 * 1024 * 1024
             }
    val = int(num) * units[unit]
    logger.debug ("%s => %d" % (fmtstr, val))
    return val


if __name__ == "__main__":
    
    import argparse
    parser = argparse.ArgumentParser(
            description='Find large blocks of random bytes')

    parser.add_argument('path', help='The file to search in')    
    parser.add_argument('-o', dest='offset', default = 0, 
            help='bytes into the file to start search at')  
    parser.add_argument('-s', dest='size', default = "50GB",
            help='size in units of the file to search for.\n eg. 24 GB')

    args = parser.parse_args()

    f = Finder()
    offsets = f.findBlocks( args.path, 
                            args.offset,
                            get_sizeof_fmt(args.size))
    from pprint import  pprint
    pprint (offsets)
