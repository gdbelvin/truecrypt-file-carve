#include<stdio.h>
#include<stdlib.h>
#include<string.h>
#include<errno.h>
#include<string.h>
#include<locale.h>
#include<time.h>
#include<sys/types.h>
#include<sys/stat.h>
#include<fcntl.h>

void errif(int condition, char* msg)
{
    if (condition)
    {
        printf("%s: %s\n", msg, strerror(errno));
       // return(-1);
    }
}

int Search_in_File(char *fname, char *str) {
    FILE *fp;
    int fd;
    int line_num = 1;
    int find_result = 0;
    char temp[512];
    struct stat statbuf;
    long int total_bytes;
    long int i;
    double percent;
    time_t t;
    time_t start_time;
    long seconds_left;
    long seconds_elapsed;
    struct tm * time_left;
    struct tm * time_elapsed;
    char timestr[50];
    char elapsed[50];

    setlocale(LC_ALL, "");

    fp = fopen(fname, "r");
    fd = fileno(fp);
    errif(fp == NULL, "fopen");
    
    /* get capacity */
    errif(fstat(fd, &statbuf) != 0, "stat" );
    total_bytes = statbuf.st_size; 
    t = time(0);
    start_time = time(0);

    for (i=0; i < total_bytes; i++)
    {
        errif( fseek(fp, i, 0) != 0, "fseek");

        if(time(0) > t)
        {
            t = time(0);
            percent = i / (double) total_bytes;
            
            //seconds_left = seconds_elapsed * bytes_remaining  / (double) i;
            seconds_elapsed = (t - start_time);
            seconds_left = (t - start_time) * (total_bytes - i)  / (double) i;
            seconds_left = 3600 * 24  * 3 + 3600 + 60 + 30;
            time_elapsed = gmtime ( &seconds_elapsed );

            strftime(elapsed, sizeof(elapsed), "%T", time_elapsed);

            time_left = gmtime ( &seconds_left );
            strftime(timestr, sizeof(timestr), "%j|%T", time_left);


            fprintf(stderr, "%f%% (%'ld of %'ld), %d:%s elapsed, %d:%s remaining\n", 
                    percent*100, i, total_bytes, 
                    time_elapsed->tm_yday, elapsed, 
                    time_left->tm_yday, timestr);
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
