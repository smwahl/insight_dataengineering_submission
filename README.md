# Table of Contents
1. [Introduction](README.md#introduction)
2. [Implementation details](README.md#implementation-details)
3. [Input files](README.md#input-files)
4. [Output file](README.md#output-file)
5. [Python Module](README.md#python-module)
6. [Command Line Script](README.md#comand-line-script)
7. [Tests](README.md#example)
8. [Dependencies](README.md#dependicies)

# Introduction

This is the submission for Sean Wahl, for the Insight Data Engeneering coding
challenge. As described in the [prompt]( https://github.com/InsightDataScience/edgar-analytics), the code is designed to parse log files provided by the Securities and Exchange Commission's Electronic Data Gathering, Analysis and Retrieval (EDGAR) system.

Your goal of the code to build a pipeline to ingest that stream of data in the form of the SEC EDGAR logs, under the assumption that data would be provided as a real-time stream into the program, and calculate how long a particular user spends on EDGAR during a visit and how many documents that user requests during the session. 

# Implementation details

The program expects two input files, both located in the `input` directory:

* `log.csv`: EDGAR weblog data
* `inactivity_period.txt`: Holds a single value denoting the period of inactivity that should be used to identify when a user session is over

The source code for the EDGAR weblog parser is a Python module located in:

* `src/sessionization.py`

While the python module can be imported into python code in the usual fashion,
`sessionization.py` also contains a script implementation that can be called from the
command-line via:

* `python src/sessionionization.py ./input/log.csv ./input/inactivity_period.txt ./output/sessionization.txt`

In the current example this script is called by a shell-script:

* `./run.sh`

## Input files

### `log.csv`

The SEC provides weblogs stretching back years and is [regularly updated, although with a six month delay](https://www.sec.gov/dera/data/edgar-log-file-data-set.html). 

For the purposes of this challenge, I assume that the data is being streamed into the program in the same order that it appears in the file with the first line (after the header) being the first request and the last line being the latest, and that the data is listed in chronological order for the purposes of this challenge.

The code makes use of the following variables

* `ip`: identifies the IP address of the device requesting the data. While the SEC anonymizes the last three digits, it uses a consistent formula that allows you to assume that any two `ip` fields with the duplicate values are referring to the same IP address
* `date`: date of the request (yyyy-mm-dd) 
* `time`:  time of the request (hh:mm:ss)
* `cik`: SEC Central Index Key
* `accession`: SEC document accession number
* `extention`: Value that helps determine the document being requested

The logfile contains a header line, which the code uses to know which column of the
log corresponds to which variable.

### `inactivity_period.txt`
This file will hold a single integer value denoting the period of inactivity (in seconds) that your program should use to identify a user session. The value will range from 1 to 86,400 (i.e., one second to 24 hours)

# Output file

Once the program identifies the start and end of a session, it gathers the following fields and write them out to a line in the output file, `sessionization.txt`. The fields on each line must be separated by a `,`:

* IP address of the user exactly as found in `log.csv`
* date and time of the first webpage request in the session (yyyy-mm-dd hh:mm:ss)
* date and time of the last webpage request in the session (yyyy-mm-dd hh:mm:ss)
* duration of the session in seconds
* count of webpage requests during the session

## Python Module

The submitted code is implemented in Python 2.7.12.

The Python module contained in `src/sessionization.py` defines two classes:

* `User`: Represents a user in a SEC EDGAR data log and tracks requests during a session
* `SessionParser`: Defines a parser object for SEC EDGAR log data

A `User` is initialized with a unique integer identifier `lid`, the user's ip address
`ip` and `start_time`, a datetime object representing the time of the user's first
request in a session.

The function `User.update()` is called for each subsequent request in a session, during
which the `User` tracks the session length and number of documents requested.

A `SessionParser` is initialized with `output` a file object to for the parsed session
information, `inactivity_period` the integer number of seconds beyond which a session
is terminated, and `fields` a dictionary storing the column numbers for the necessary
fields.

Once initialized EDGAR log data is passed to the parser via
`SessionParser.parse_requests()`. This can be called an arbitrary number of times to
parse data from different log-files in sequence, and the parser object is able to
track a User session that continues over those two log files.

The parser includes checks so that it should gracefully skip over any invalid entries
in a log file, and continue parsing the sessions under the asssumption that these
entries can be ignored, and prints a warning when this occurs.

Finally, `SessionParser.terminate_remaining_sessions() must be run after all desired
log data has been passed to the parser to finish terminating sessions that were
active at the the end of the last data source.

## Command Line Script

The command line script contained in `src/sessionization.py` implements an example of
the code in which the EDGAR weblog data is read from a single log file. The script
passes the log data to the parser a fixed number of lines at the time. This is
intended so that the output can be viewd while a very large data sourced in is being
parced, and to function in a similar manner as a real-time stream of data. The size
of this line buffer can be specified by the commandline option '-h'.

usage: sessionization.py [-h] [-n LINE_BUFFER] [-d HEADER]
                         log*.csv inactivity_period output

Parse SEC EDGAR log into Sessions.

positional arguments:
  log*.csv              EDGAR weblog data file (csv)
  inactivity_period     text file storing integer inactivity period
  output                output text file with session information

optional arguments:
  -h, --help            show this help message and exit
  -n LINE_BUFFER, --line_buffer LINE_BUFFER
                        number of lines to parse at a time
  -d HEADER, --header HEADER
                        number of header lines to skip at start of log file




## Tests

To make sure that your code has the correct directory structure and the format of the output files are correct, we have included a test script called `run_tests.sh` in the `insight_testsuite` folder.

The tests are stored simply as text files under the `insight_testsuite/tests` folder. Each test should have a separate folder with an `input` folder for `inactivity_period.txt` and `log.csv` and an `output` folder for `sessionization.txt`.

You can run the test with the following command from within the `insight_testsuite` folder:

    insight_testsuite~$ ./run_tests.sh 

On a failed test, the output of `run_tests.sh` should look like:

    [FAIL]: test_1
    [Thu Mar 30 16:28:01 PDT 2017] 0 of 1 tests passed

On success:

    [PASS]: test_1
    [Thu Mar 30 16:25:57 PDT 2017] 1 of 1 tests passed

The other tests were deisgned to check that the parser works as intended for
different choices of `inactivity_period`, for beginning at an arbitry time, and for
skipping invalid input data.

## Dependencies

The python module for the parser depends only on the following modules contained form the Standard Python Library:

* `sys`
* `argparse`
* `datetime`
* `itertools`
* `warnings`
