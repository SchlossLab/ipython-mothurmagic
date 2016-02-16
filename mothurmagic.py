# mothurmagic.py
from __future__ import print_function

import os
import subprocess as sub
import random
from IPython.core.magic import (Magics, magics_class, line_magic, cell_magic, line_cell_magic)
from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring
from IPython.display import display_pretty


MOTHUR_CURRENT_FILES = dict()


class mothurMagicError(Exception):
    pass

@magics_class
class Mothur(Magics):

    @cell_magic
    def mothur(self, line, cell):
        """Run mothur command.
        
        Usage:
        
            %%mothur 
            help()

        """
        self.number = line
        self.code = cell

        commands = self.code.split("\n")
        new_commands = []

        #output = run_command(commands)
        #display_output(output)
        for command in commands:
            new_command = parse_input(command)
            output = run_command(new_command)
            parse_output(output)
            display_output(output)


def parse_input(command):
    print('\n>> parsing input...')
    print('command', command)
    return command


def run_command(command):
    print('\n>> running mothur...')

    #mothurbatch = "; ".join(commands)
    random.seed()
    rn = random.randint(10000,99999)
    logfile = "mothur.ipython.%d.logfile" % rn
    mothurbatch = "set.logfile(name=%s); " % logfile + command

    try:
        sub.call(['mothur',  "#%s" % mothurbatch])
        return(logfile)
    except OSError as e:
        if e.errno == os.errno.ENOENT:
            try:
                sub.call(['./mothur',  "#%s" % mothurbatch])
                return(logfile)
            except OSError as e:
                print("Can't open mothur: " + e.args[1])  # "mothur not in path"
                return logfile
        else:
            print("Something went wrong while opening mothur. Here's what I know: " + e)
            return logfile
    except:
        print("uh oh, something went really wrong.")
        return logfile


def parse_output(output):
    print('\n>> parsing output...')

    with open(output, 'r') as log:
        lines = (line for line in log.readlines())

    for line in lines:
        if "Output File Names:" in line:
            while True:
                try:
                    #next(parse_output_line(line) for line in lines)
                    filename = (next(line for line in lines)).split()
                    if filename:
                        filetype = filename[0].split('.')[-1]
                        MOTHUR_CURRENT_FILES[filetype] = filename[0]
                    else:
                        break
                except StopIteration:
                    break

    for k, v in MOTHUR_CURRENT_FILES.items():
        print(k, v)

    return


def parse_output_line(line):


    #    MOTHUR_CURRENT_FILES[filetype] = line

    return


def display_output(logfile):
    print('\n>> displaying output...')
    print('logfile: ', logfile)
    with open(logfile, 'r') as log:
        count = 0
        lines = log.readlines()
        for idx, line in enumerate(lines):
            if line.startswith("mothur >") and not line.startswith("mothur > set.logfile"):
                for l in lines[idx:]:
                    if count > 1000:
                        return "output exceded 1000 lines. See logfile %s for complete output." % logfile
                        break
                    print(l.strip())
                    count = count + 1
                break


def load_ipython_extension(ipython):
    # The `ipython` argument is the currently active `InteractiveShell`
    # instance, which can be used in any way. This allows you to register
    # new magics or aliases, for example.
    ipython.register_magics(Mothur)

