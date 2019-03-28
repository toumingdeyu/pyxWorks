#!/usr/bin/python
import io
import os
import sys
import difflib
import argparse
import re

class bcolors:
    DEFAULT = '\033[99m'
    WHITE = '\033[97m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    RED='\033[91m'
    GREY = '\033[90m'
    ENDC='\033[0m'
    BOLD='\033[1m'
    UNDERLINE='\033[4m'

parser = argparse.ArgumentParser()
parser.add_argument("-f1", "--file1", action = "store", default = '',help = "file1")
parser.add_argument("-f2", "--file2", action = "store", default = '',help = "file2")
parser.add_argument("--diff", action = "store", dest = "diff", choices = ['ndiff','ndiff2','new'],
                    default = 'new', help = "filediff method ndiff/new")
parser.add_argument("-pe", "--printequals",action = "store_true", default = False,
                    help = "print equal lines")
aargs = parser.parse_args()

note_string = "DIFF('-' missing, '+' added, '!' different, '=' equal with problem):\n"
default_problem_list = []   #[' DOWN', ' down','Down','Fail', 'FAIL', 'fail']
default_ignoreline_list = [r' MET$', r' UTC$']
default_linefilter_list = []   #[r'^\w+\s+\w+']


def get_difference_string_from_string_or_list(
    old_string_or_list, \
    new_string_or_list, \
    diff_method = 'new', \
    problem_list = default_problem_list, \
    ignore_list = default_ignoreline_list, \
    linefilter_list = default_linefilter_list, \
    print_equals = None, \
    debug = None, \
    note = True ):
    '''
    FUNCTION get_difference_string_from_string_or_list:
    INPUT PARAMETERS:
      - old_string_or_list - content of old file in string or list type
      - new_string_or_list - content of new file in string or list type
      - diff_method - ndiff or new
      - problem_list - list of regular expressions or strings which detects problems, even if files are equal
      - ignore_list - list of regular expressions or strings when line is ignored for file (string) comparison
      - linefilter_list - list of regular expressions which filters each line
      - print_equals - True/False prints all equal new file lines with '=' prefix , by default is False
      - debug - True/False, prints debug info to stdout, by default is False
      - note - True/False, prints info header to stdout, by default is True
    RETURNS: string with file differencies

    The head of line is
    '-' for missing line,
    '+' for added line,
    '!' for line that is different and
    '=' for the same line, but with problem.
    RED for something going DOWN or something missing or failed.
    ORANGE for something going UP or something NEW (not present in pre-check)
    '''
    print_string = str()
    if diff_method == 'new': print_string = note_string if note else str()

    # make list from string if is not list already
    old_lines_unfiltered = old_string_or_list if type(old_string_or_list) == list else old_string_or_list.splitlines()
    new_lines_unfiltered = new_string_or_list if type(new_string_or_list) == list else new_string_or_list.splitlines()

    # make filtered-out list of lines from both files
    old_lines, new_lines = [], []
    for line in old_lines_unfiltered:
        ignore=False
        for ignore_item in ignore_list:
            if (re.search(ignore_item,line)) != None: ignore = True
        for linefilter_item in linefilter_list:
            if (re.search(linefilter_item,line)) != None:
                line = re.findall(linefilter_item,line)[0]
        if not ignore: old_lines.append(line)

    for line in new_lines_unfiltered:
        ignore=False
        for ignore_item in ignore_list:
            if (re.search(ignore_item,line)) != None: ignore = True
        for linefilter_item in linefilter_list:
            if (re.search(linefilter_item,line)) != None:
                line = re.findall(linefilter_item,line)[0]
        if not ignore: new_lines.append(line)

    del old_lines_unfiltered
    del new_lines_unfiltered

    # NDIFF COMPARISON METHOD
    if diff_method == 'ndiff':
        diff = difflib.ndiff(old_lines, new_lines)
        for line in list(diff):
            try:    first_chars = line.strip()[0]+line.strip()[1]
            except: first_chars = str()
            if '+ ' == first_chars: print_string += bcolors.GREEN + line + bcolors.ENDC + '\n'
            elif '- ' == first_chars: print_string += bcolors.RED + line + bcolors.ENDC + '\n'
            elif '! ' == first_chars: print_string += bcolors.RED + line + bcolors.ENDC + '\n'
            elif '? ' == first_chars or first_chars == str(): pass
            elif print_equals: print_string += line + '\n'
        return print_string

    # NEW COMPARISON METHOD CONTINUE
    enum_old_lines = enumerate(old_lines)
    enum_new_lines = enumerate(new_lines)

    if old_lines and new_lines:
        new_first_words = [line.split(' ')[0] for line in new_lines]
        old_first_words = [line.split(' ')[0] for line in old_lines]
        if debug: print('11111 :',old_first_words,new_first_words)

        lost_lines = [item for item in old_first_words if item not in new_first_words]
        added_lines = [item for item in new_first_words if item not in old_first_words]
        if debug: print('----- :',lost_lines)
        if debug: print('+++++ :',added_lines)

        try:    j, old_line = next(enum_old_lines)
        except: j, old_line = -1, str()

        try:    i, line = next(enum_new_lines)
        except: i, line = -1, str()

        while i >= 0 and j>=0:
            go, diff_sign, color, print_line = 'void', ' ', bcolors.WHITE, str()

            # void new lines
            if not line.strip():
                while len(line.strip()) == 0 and i >= 0:
                    try:    i, line = next(enum_new_lines)
                    except: i, line = -1, str()

            # void old lines
            if not old_line.strip():
                while len(old_line.strip()) == 0 and j >= 0:
                    try:    j, old_line = next(enum_old_lines)
                    except: j, old_line = -1, str()

            # auxiliary first words
            try: first_line_word = line.strip().split()[0]
            except: first_line_word = str()
            try: first_old_line_word = old_line.strip().split()[0]
            except: first_old_line_word = str()

            # if again - lines are the same
            if line.strip() == old_line.strip():
                if print_equals: go, diff_sign, color, print_line= 'line_equals', '=', bcolors.WHITE, line
                else:            go, diff_sign, color, print_line= 'line_equals', '=', bcolors.WHITE, str()

                # In case of DOWN/FAIL write also equal values !!!
                for item in problem_list:
                    if (re.search(item,line)) != None: color, print_line = bcolors.RED, line

                try:    j, old_line = next(enum_old_lines)
                except: j, old_line = -1, str()

                try:    i, line = next(enum_new_lines)
                except: i, line = -1, str()

            # changed line
            elif first_line_word == first_old_line_word and not new_first_words[i] in added_lines:
                go, diff_sign, color, print_line = 'changed_line', '!', bcolors.YELLOW, line
                print_old_line = old_line

                for item in problem_list:
                    if (re.search(item,line)) != None: color = bcolors.RED

                try:    j, old_line = next(enum_old_lines)
                except: j, old_line = -1, str()

                try:    i, line = next(enum_new_lines)
                except: i, line = -1, str()

            # added line
            elif first_line_word in added_lines:
                go, diff_sign, color, print_line = 'added_line','+',  bcolors.YELLOW, line

                for item in problem_list:
                    if (re.search(item,line)) != None: color = bcolors.RED

                try:    i, line = next(enum_new_lines)
                except: i, line = -1, str()

            # lost line
            elif not first_line_word in lost_lines and old_line.strip():
                go, diff_sign, color, print_line = 'lost_line', '-',  bcolors.RED, old_line

                try:    j, old_line = next(enum_old_lines)
                except: j, old_line = -1, str()
            else:
                # added line on the end
                if first_line_word and not first_old_line_word:
                    go, diff_sign, color, print_line = 'added_line_on_end','+',  bcolors.YELLOW, line

                    for item in problem_list:
                        if (re.search(item,line)) != None: color = bcolors.RED

                    try:    i, line = next(enum_new_lines)
                    except: i, line = -1, str()
                # lost line on the end
                elif not first_line_word and first_old_line_word:
                    go, diff_sign, color, print_line = 'lost_line_on_end', '-',  bcolors.RED, old_line

                    try:    j, old_line = next(enum_old_lines)
                    except: j, old_line = -1, str()
                else: print('!!! PARSING PROBLEM: ',j,old_line,' -- vs -- ',i,line,' !!!')

            if debug: print('####### %s  %s  %s  %s\n'%(go,color,diff_sign,print_line))
            if print_line:
                if not print_old_line:
                    print_string=print_string+'%s  %s  %s%s\n'%(color,diff_sign,print_line.rstrip(),bcolors.ENDC)
                else:
                    if diff_method == 'ndiff2':
                        print_string=print_string+'%s  %s  %s%s\n'%(bcolors.RED,'-',print_old_line.rstrip(),bcolors.ENDC)
                        print_string=print_string+'%s  %s  %s%s\n'%(bcolors.GREEN,'+',print_line.rstrip(),bcolors.ENDC)
                    else:
                        print_string=print_string+'%s  %s  %s%s\n'%(color,diff_sign,print_line.rstrip(),bcolors.ENDC)
                    print_old_line=None
    return print_string



def main():

    old_lines='''
    aaa fdffd hjhjgj down


bbb dfsfsd sss jyjyjtu
ddd ggggggggggggg
eee ffsgf srgwrgwfg down
ccc sfewfweg  sdgwrg
ssss ssss down
ddd ddddddddddd

sssss dsss
ddd ggggggggggggg

    '''
    new_lines='''aaa fdffd hjhjgj down
bbb dfsfsd jyjyjtu
ccc sfewfweg  sdgwrg
fff dsgg ethtq hthtyh
gggg dsvsvvsf down
ssss ssss down

dddd jjjj
ddd ggggggggggggggggg

eee gggggggggggggg

    '''

    if aargs.file1:
        with io.open(aargs.file1) as file1: old_lines = file1.read()

    if aargs.file2:
        with io.open(aargs.file2) as file2: new_lines = file2.read()

    print(get_difference_string_from_string_or_list(old_lines, \
                            new_lines,diff_method = aargs.diff, \
                            print_equals = aargs.printequals, \
                            note=True))


if __name__ == "__main__": main()