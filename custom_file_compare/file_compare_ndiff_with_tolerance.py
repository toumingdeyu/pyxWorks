#!/usr/bin/python

import sys, os
import getopt
import getpass 
import telnetlib
import time, datetime
import difflib
import subprocess
import re
import argparse
import glob
import socket

class bcolors:
        DEFAULT    = '\033[99m'
        WHITE      = '\033[97m'
        CYAN       = '\033[96m'
        MAGENTA    = '\033[95m'
        HEADER     = '\033[95m'
        OKBLUE     = '\033[94m'
        BLUE       = '\033[94m'
        YELLOW     = '\033[93m'
        GREEN      = '\033[92m'
        OKGREEN    = '\033[92m'
        WARNING    = '\033[93m'
        RED        = '\033[91m'
        FAIL       = '\033[91m'
        GREY       = '\033[90m'
        ENDC       = '\033[0m'
        BOLD       = '\033[1m'
        UNDERLINE  = '\033[4m'

class nocolors:
        DEFAULT    = ''
        WHITE      = ''
        CYAN       = ''
        MAGENTA    = ''
        HEADER     = ''
        OKBLUE     = ''
        BLUE       = ''
        YELLOW     = ''
        GREEN      = ''
        OKGREEN    = ''
        WARNING    = ''
        RED        = ''
        FAIL       = ''
        GREY       = ''
        ENDC       = ''
        BOLD       = ''
        UNDERLINE  = ''

COL_DELETED = bcolors.RED
COL_ADDED   = bcolors.GREEN
COL_DIFFDEL = bcolors.BLUE
COL_DIFFADD = bcolors.YELLOW
COL_EQUAL   = bcolors.GREY
COL_PROBLEM = bcolors.RED


note_ndiff_string  = "ndiff( %s'-' missed, %s'+' added, %s'-\\n%s+' difference, %s' ' equal%s) [no filters]\n" % \
    (bcolors.RED,bcolors.GREEN,bcolors.RED,bcolors.GREEN,bcolors.GREY,bcolors.ENDC )
note_ndiff0_string = "ndiff0(%s'-' missed, %s'+' added, %s'-\\n%s+' difference, %s' ' equal%s)\n" % \
    (COL_DELETED,COL_ADDED,COL_DIFFDEL,COL_DIFFADD,COL_EQUAL,bcolors.ENDC )
note_pdiff0_string = "pdiff0(%s'-' missed, %s'+' added, %s'!' difference,    %s' ' equal%s)\n" % \
    (COL_DELETED,COL_ADDED,COL_DIFFADD,COL_EQUAL,bcolors.ENDC )

default_problemline_list   = []
default_ignoreline_list    = [r' MET$', r' UTC$']
default_linefilter_list    = []
default_compare_columns    = []
default_printalllines_list = []


def get_difference_string_from_string_or_list(
    old_string_or_list, \
    new_string_or_list, \
    diff_method = 'ndiff0', \
    ignore_list = default_ignoreline_list, \
    problem_list = default_problemline_list, \
    printalllines_list = default_printalllines_list, \
    linefilter_list = default_linefilter_list, \
    compare_columns = [], \
    print_equallines = None, \
    tolerance_percentage = None, \
    debug = None, \
    note = True ):
    '''
    FUNCTION get_difference_string_from_string_or_list:
    INPUT PARAMETERS:
      - OLD_STRING_OR_LIST - content of old file in string or list type
      - NEW_STRING_OR_LIST - content of new file in string or list type
      - DIFF_METHOD - ndiff, ndiff0, pdiff0
      - IGNORE_LIST - list of regular expressions or strings when line is ignored for file (string) comparison
      - PROBLEM_LIST - list of regular expressions or strings which detects problems, even if files are equal
      - PRINTALLLINES_LIST - list of regular expressions or strings which will be printed grey, even if files are equal
      - LINEFILTER_LIST - list of regular expressions which filters each line (regexp results per line comparison)
      - COMPARE_COLUMNS - list of columns which are intended to be different , other columns in line are ignored
      - PRINT_EQUALLINES - True/False prints all equal new file lines with '=' prefix , by default is False
      - TOLERANCE_PERCENTAGE - All numbers/selected columns in line with % tolerance. String columns must be equal.
      - DEBUG - True/False, prints debug info to stdout, by default is False
      - NOTE - True/False, prints info header to stdout, by default is True
    RETURNS: string with file differencies , all_ok [True/False]

    PDIFF0 FORMAT: The head of line is
    '-' for missing line,
    '+' for added line,
    '!' for line that is different and
    ' ' for the same line, but with problem.
    RED for something going DOWN or something missing or failed.
    ORANGE for something going UP or something NEW (not present in pre-check)
    '''
    print_string, all_ok = str(), True
    if note:
       print_string = "DIFF_METHOD: "
       if diff_method   == 'ndiff0': print_string += note_ndiff0_string
       elif diff_method == 'pdiff0': print_string += note_pdiff0_string
       elif diff_method == 'ndiff' : print_string += note_ndiff_string

    # MAKE LIST FROM STRING IF IS NOT LIST ALREADY -----------------------------
    old_lines_unfiltered = old_string_or_list if type(old_string_or_list) == list else old_string_or_list.splitlines()
    new_lines_unfiltered = new_string_or_list if type(new_string_or_list) == list else new_string_or_list.splitlines()

    # NDIFF COMPARISON METHOD---------------------------------------------------
    if diff_method == 'ndiff':
        diff = difflib.ndiff(old_lines_unfiltered, new_lines_unfiltered)
        for line in list(diff):
            try:    first_chars = line[0]+line[1]
            except: first_chars = str()
            ignore = False
            for ignore_item in ignore_list:
                if (re.search(ignore_item,line)) != None: ignore = True
            if ignore: continue
            if len(line.strip())==0: pass
            elif '+ ' == first_chars: print_string += COL_ADDED + line + bcolors.ENDC + '\n'
            elif '- ' == first_chars: print_string += COL_DELETED + line + bcolors.ENDC + '\n'
            elif '? ' == first_chars or first_chars == str(): pass
            elif print_equallines: print_string += COL_EQUAL + line + bcolors.ENDC + '\n'
            else:
                print_line, ignore = False, False
                for item in printalllines_list:
                    if (re.search(item,line)) != None: print_line = True
                if print_line:
                    print_string += COL_EQUAL + line + bcolors.ENDC + '\n'
        return print_string

    # NDIFF0 COMPARISON METHOD--------------------------------------------------
    if diff_method == 'ndiff0' or diff_method == 'pdiff0':
        ignore_previous_line = False
        diff = difflib.ndiff(old_lines_unfiltered, new_lines_unfiltered)
        listdiff_nonfiltered = list(diff)
        listdiff = []
        # FILTER DIFF LINES OUT OF '? ' AND VOID LINES -------------------------
        for line in listdiff_nonfiltered:
            # This ignore filter is much faster
            ignore = False
            for ignore_item in ignore_list:
                if (re.search(ignore_item,line)) != None: ignore = True
            if ignore: continue
            try:    first_chars = line[0]+line[1]
            except: first_chars = str()
            if '+ ' in first_chars or '- ' in first_chars or '  ' in first_chars:
                listdiff.append(line)
        del diff, listdiff_nonfiltered
        # MAIN NDIFF0/PDIFF0 LOOP ----------------------------------------------
        previous_minus_line_is_change = False
        for line_number,line in enumerate(listdiff):
            print_color, print_line = COL_EQUAL, str()
            try:    first_chars_previousline = listdiff[line_number-1][0]+listdiff[line_number-1][1].replace('\t',' ')
            except: first_chars_previousline = str()
            try:    first_chars = line[0]+line[1].replace('\t',' ')
            except: first_chars = str()
            try:    first_chars_nextline = listdiff[line_number+1][0]+listdiff[line_number+1][1].replace('\t',' ')
            except: first_chars_nextline = str()
            # CHECK IF ARE LINES EQUAL AFTER FILTERING (compare_columns + linefilter_list)
            split_line,split_next_line,linefiltered_line,linefiltered_next_line = str(),str(),str(),str()
            ### CLEAR AUXILIARY VARIABLES WHEN NO -/+ FIRST CHARACTERS ---------
            if first_chars.strip() == str():
                ignore_previous_line = False
                previous_minus_line_is_change = False
            ### POSSIBLE CHANGE in LINE ----------------------------------------
            if '-' in first_chars and '+' in first_chars_nextline:
                ### SELECT COMPARE_COLUMNS -------------------------------------
                for split_column in compare_columns:
                    # +1 MEANS EQUAL OF DELETION OF FIRST COLUMN -
                    try: temp_column = line.split()[split_column+1]
                    except: temp_column = str()
                    split_line += ' ' + temp_column.replace('/',' ')
                for split_column in compare_columns:
                    # +1 MEANS EQUAL OF DELETION OF FIRST COLUMN +
                    try: temp_column = listdiff[line_number+1].split()[split_column+1]
                    except: temp_column = str()
                    split_next_line += ' ' + temp_column.replace('/',' ')
                ### LINEFILTER -------------------------------------------------
                for linefilter_item in linefilter_list:
                    try: next_line = listdiff[line_number+1]
                    except: next_line = str()
                    if line and (re.search(linefilter_item,line)) != None:
                        linefiltered_line = re.findall(linefilter_item,line)[0]
                    if next_line and (re.search(linefilter_item,next_line)) != None:
                        linefiltered_next_line = re.findall(linefilter_item,line)[0]
                ### IF SPLIT_LINE DOES not EXIST FROM COMPARE_COLUMNS DO IT ----
                if not split_line: split_line = line.replace('/',' ')
                if not split_next_line: split_next_line = listdiff[line_number+1].replace('/',' ')
                ### TOLERANCE_PERCENTAGE = COMPARING NUMBER COLUMNS with TOLERANCE
                columns_are_equal = 0
                for split_column,split_next_column in zip(split_line.split()[1:],split_next_line.split()[1:]):
                    try: next_column_is_number = float(split_next_column.replace(',','').replace('%','').replace('(',''))
                    except: next_column_is_number = None
                    try: column_is_number = float(split_column.replace(',','').replace('%','').replace('(',''))
                    except: column_is_number = None
                    if column_is_number and next_column_is_number and tolerance_percentage:
                        if column_is_number <= next_column_is_number * ((100 + float(tolerance_percentage))/100)\
                            and column_is_number >= next_column_is_number * ((100 - float(tolerance_percentage))/100):
                                columns_are_equal += 1
                    elif split_column and split_next_column and split_column == split_next_column:
                        columns_are_equal += 1
                ### IF LINES ARE EQUAL WITH +/- TOLERANCE ----------------------
                if columns_are_equal > 0 and columns_are_equal + 1 == len(split_line.split()) \
                    and columns_are_equal + 1 == len(split_next_line.split()):
                        ignore_previous_line = True
                        continue
                ### LINES ARE EQUAL AFTER FILTERING - filtered linefilter and columns commands
                if (split_line and split_next_line and split_line == split_next_line) or \
                   (linefiltered_line and linefiltered_next_line and linefiltered_line == linefiltered_next_line):
                    ignore_previous_line = True
                    continue
            # CONTINUE CHECK DELETED/ADDED LINES--------------------------------
            if '-' in first_chars:
                ignore_previous_line = False
                # FIND IF IT IS CHANGEDLINE OR DELETED LINE
                line_list_lenght, the_same_columns = len(line.split()), 0
                percentage_of_equality = 0
                try: nextline_sign_column = listdiff[line_number+1].split()[0]
                except: nextline_sign_column = str()
                if nextline_sign_column == '+':
                    for column_number,column in enumerate(line.split()):
                        try: next_column = listdiff[line_number+1].split()[column_number]
                        except: next_column = str()
                        if column == next_column: the_same_columns += 1
                    if line_list_lenght>0:
                        percentage_of_equality = (100*the_same_columns)/line_list_lenght
                # CHANGED LINE -------------------------------------------------
                if percentage_of_equality > 54:
                    previous_minus_line_is_change = True
                    if diff_method == 'ndiff0':
                        print_color, print_line = COL_DIFFDEL, line
                # LOST/DELETED LINES -------------------------------------------
                else: print_color, print_line = COL_DELETED, line
            # IGNORE EQUAL -/= LINES or PRINT printall and problem lines -------
            elif '+' in first_chars and ignore_previous_line:
                line = ' ' + line[1:]
                ignore_previous_line = False
            # ADDED NEW LINE ---------------------------------------------------
            elif '+' in first_chars and not ignore_previous_line:
                if previous_minus_line_is_change:
                    previous_minus_line_is_change = False
                    if diff_method == 'pdiff0': line = '!' + line[1:]
                    print_color, print_line = COL_DIFFADD, line
                else: print_color, print_line = COL_ADDED, line
            # PRINTALL ---------------------------------------------------------
            elif print_equallines: print_color, print_line = COL_EQUAL, line
            # PRINTALL LINES GREY IF not ALREADY PRINTED BY ANOTHER COLOR ------
            if not print_line:
                for item in printalllines_list:
                    if (re.search(item,line)) != None: print_color, print_line = COL_EQUAL, line
            # PROBLEM LIST - IN CASE OF DOWN/FAIL WRITE ALSO EQUAL VALUES !!! --
            for item in problem_list:
                if (re.search(item,line)) != None: print_color, print_line = COL_PROBLEM, line
            # TEST if ALL_OK ---------------------------------------------------
            if len(print_line)>0:
                if print_color == COL_PROBLEM or print_line[0] in ['+','-','!']: all_ok = False
            # Final PRINT ------------------------------------------------------
            if print_line: print_string += "%s%s%s\n" % (print_color,print_line,bcolors.ENDC)
    return print_string, all_ok


parser = argparse.ArgumentParser()
parser.add_argument("-f1", "--file1", action = "store", default = '',help = "file1 (pre)")
parser.add_argument("-f2", "--file2", action = "store", default = '',help = "file2 (post)")
parser.add_argument("--diff", action = "store", dest = "diff", \
                    choices = ['ndiff0','pdiff0','ndiff'], \
                    default = 'ndiff0' , help = "different filediff formats")
parser.add_argument("-pe", "--printequallines",action = "store_true", default = False,
                    help = "print equal lines")
parser.add_argument("--nocolors",
                    action = 'store_true', dest = "nocolors", default = False,
                    help = "print mode with no colors.")
aargs = parser.parse_args()

if aargs.nocolors: bcolors = nocolors

COL_DELETED = bcolors.RED
COL_ADDED   = bcolors.GREEN
COL_DIFFDEL = bcolors.BLUE
COL_DIFFADD = bcolors.YELLOW
COL_EQUAL   = bcolors.GREY
COL_PROBLEM = bcolors.RED

def main():

    old_lines='''totally equal line
    the same line type1 different whitespaces on start
changed line THISISCHANGEMINUS
missing1 line
missing2 line with DOWN
the same line type2 with UP
the same line type3 with DOWN
missingx line ddddddddddd
missing line xxxx
changed3 line ggggggggggggg
    '''
    new_lines='''totally equal line
the same line type1 different whitespaces on start
changed line THISISCHANGEPLUS
the same line type2 with UP
added line xxxxxxxxxxxx
added line with DOWN
the same line type3 with DOWN
added line ddddddd
changed3 line ggggggggggggggggg
added4 line gggggggggggggg
    '''

    if aargs.file1:
        with io.open(aargs.file1) as file1: old_lines = file1.read()

    if aargs.file2:
        with io.open(aargs.file2) as file2: new_lines = file2.read()


    text, ok = get_difference_string_from_string_or_list(old_lines, \
                            new_lines,diff_method = aargs.diff, \
                            print_equallines = aargs.printequallines, \
                            note=True)
    print(text)


if __name__ == "__main__": main()