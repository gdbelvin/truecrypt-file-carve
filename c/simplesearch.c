#include<stdio.h>
#include<stdlib.h>
#include<string.h>
#include<sys/statvfs.h>
#include<errno.h>
#include<string.h>
#include<locale.h>
#include<time.h>

void errif(int condition, char* msg)
{
    if (!condition)
    {
        printf("%s: %s\n", msg, strerror(errno));
    }
}

int Search_in_File(char *fname, char *str) {
    FILE *fp;
    int line_num = 1;
    int find_result = 0;
    char temp[512];
    struct statvfs statbuf;
    long int total_bytes;
    long int i;
    time_t t;

    double percent;
   
    setlocale(LC_ALL, "");

    if((fp = fopen(fname, "r")) == NULL) {
      return(-1);
    }
    
    /* get capacity */
    errif(statvfs(fname, &statbuf) == 0, "statvfs" );
    total_bytes = statbuf.f_blocks*statbuf.f_frsize;

    printf("blocks: %ld\n", statbuf.f_blocks);
    printf("free blocks: %ld\n", statbuf.f_bfree);
    printf("available blocks: %ld\n", statbuf.f_bavail);
    printf("block size: %ld\n", statbuf.f_frsize);
    printf("total bytes: %ld\n", statbuf.f_blocks*statbuf.f_frsize);
    t = time(0);
    for (i=0; i < total_bytes; i++)
    {
        percent = i * 100 / (double) total_bytes;
        if(time(0) > t)
        {
            fprintf(stderr, "\rprogress: %f (%'ld of %'ld)", percent, i, total_bytes);
            t = time(0);
        }

    }
    
    /*Seek to byte n */

    while(fgets(temp, 512, fp) != NULL) {
        if((strstr(temp, str)) != NULL) {
            printf("A match found on line: %d\n", line_num);
            printf("\n%s\n", temp);
            find_result++;
        }
        line_num++;
    }

    if(find_result == 0) {
        printf("\nSorry, couldn't find a match.\n");
    }
    
    //Close the file if still open.
    if(fp) {
        fclose(fp);
    }
    return(0);
}

void Usage(char* filename)
{
    printf("Usage %s <file> <string>\n", filename);
}

//Our main function.
int main(int argc, char *argv[]) {
    int result, errno;

    if(argc < 3 || argc > 3) {
        Usage(argv[0]);
        exit(1);
    }

    //Use system("cls") on windows
    //Use system("clear") on Unix/Linux
    system("clear");

    result = Search_in_File(argv[1], argv[2]);
    if(result == -1) {
        perror("Error");
        printf("Error number = %d\n", errno);
        exit(1);
    }
    return(0);
}
