# mothurmagic.py
from __future__ import print_function
import json
import os
import subprocess as sub
import random
import re
from IPython.core.magic import Magics, magics_class, line_magic, cell_magic, line_cell_magic


class mothurMagicError(Exception):
    pass

@magics_class
class MothurMagic(Magics):
    """Runs mothur commands from the Jupyter notebook environment.

    Provides the %%mothur magic."""


    def __init__(self, shell):
        Magics.__init__(self, shell=shell)


    @cell_magic('mothur')
    def mothur(self, line, cell):
        """Run mothur command.
        
        Usage:
        
            %%mothur 
            help()

        """

        # save notebooks variables so we have access to them
        user_ns = self.shell.user_ns.copy()
        self.local_ns = user_ns

        # Load _mothur_current from user_ns if it exists. If it does not exist try loading from file.
        # If file does not exist assume this is the first time %%mothur has been run in this notebook
        # and create the entry in user_ns.
        if '_mothur_current' in user_ns:
            _mothur_current = user_ns['_mothur_current']
        else:
            try:
                with open('mothur.current.json', 'r') as in_handle:
                    _mothur_current = json.load(in_handle)
                    user_ns['_mothur_current'] = _mothur_current
            except IOError as e:
                # file doesn't exist or can't be read so create new user_ns entry for current
                #TODO differentiate permission error from file does not exist error.
                print('Couldn\'t load _mothur.current variables from file: ', e.args[1])
                _mothur_current = {}
                user_ns['_mothur_current'] = _mothur_current

        self.number = line
        self.code = cell

        #commands = self.code.split("\n")

        commands = parse_input(self)
        mothurbatch = "; ".join(commands)
        output = run_command(mothurbatch)
        output_files = parse_output(output)

        # update _mothur_current and push to notebook environment
        _mothur_current.update(output_files)
        user_ns['_mothur_current'].update(_mothur_current)
        self.shell.user_ns.update(user_ns)

        # create/overwrite mothur.current.json with contents of _mothur_current
        # from current notebook environment.
        try:
            with open('mothur.current.json', 'w') as out_handle:
                json.dump(self.shell.user_ns['_mothur_current'], out_handle)
        except IOError as e:
            #TODO differentiate permission error from file does not exist error.
            print('Couldn\'t save mothur_current variables to file: ', e.ars[1])

        display_output(output)


def parse_input(self):
    """Parse commands and insert local variables.

    Arguments:
        - code: mothur commands entered in the notebook cell

    Split the commands (if more than one) and parse the first command, replacing 'current' selections
    with the appropriate file path specified in _mothur_current. Recombine the commands and return.
    """

    commands = self.code.split("\n")

    new_commands = []
    for idx, command in enumerate(commands):
        # parse first command
        if idx == 0:
            first_command = command
            split_command = (re.split('\(|\)', first_command))
            mothur_command = split_command[0]
            command_arguments = split_command[1]

            # parse command arguments
            new_arguments = []
            for argument in command_arguments.split(', '):
                split_argument = argument.split('=')
                argument_type = split_argument[0]
                argument_argument = split_argument[1]
                if argument_argument.lower() == 'current':
                    _mothur_current = self.local_ns['_mothur_current']
                    argument_argument = _mothur_current[argument_type]
                    new_argument = '%s=%s' % (argument_type, argument_argument)
                    new_arguments.append(new_argument)
                else:
                    new_arguments.append(argument)
            new_arguments = ', '.join(new_arguments)
            new_command = '%s(%s)' % (mothur_command, new_arguments)
            new_commands.append(new_command)
        else:
            new_commands.append(command)

    return new_commands


def run_command(mothurbatch):
    """Run mothur using command line mode.

    Arguments:
        - mothurbatch: batched mothur commands seperated by ';'

    Output from mothur is stored in a randomly numbered log file.
    """

    random.seed()
    rn = random.randint(10000,99999)
    logfile = "mothur.ipython.%d.logfile" % rn
    mothur_command = "set.logfile(name=%s); " % logfile + mothurbatch

    try:
        sub.call(['mothur',  "#%s" % mothur_command])
    except OSError as e:
        if e.errno == os.errno.ENOENT:
            try:
                sub.call(['./mothur',  "#%s" % mothur_command])
            except OSError as e:
                print("Can't open mothur: " + e.args[1])  # "mothur not in path"
        else:
            print("Something went wrong while opening mothur. Here's what I know: " + e)
    except:
        print("uh oh, something went really wrong.")

    return logfile


def parse_output(logfile):
    """Parse mothur logfile to extract output files."""

    with open(logfile, 'r') as log:
        lines = (line for line in log.readlines())
    output_files = {}
    for line in lines:
        if "Output File Names:" in line:
            while True:
                try:
                    filename = (next(line for line in lines)).split()
                    if filename:
                        filetype = filename[0].split('.')[-1]
                        output_files[filetype] = filename[0]
                    else:
                        break
                except StopIteration:
                    break

    return output_files


def display_output(logfile):
    """Print contents of logfile to the notebook.

    Arguments:
        - logfile: path of the output log file generated by mothur
    """

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

    return


def load_ipython_extension(ipython):
    # The `ipython` argument is the currently active `InteractiveShell`
    # instance, which can be used in any way. This allows you to register
    # new magics or aliases, for example.
    ipython.register_magics(MothurMagic)