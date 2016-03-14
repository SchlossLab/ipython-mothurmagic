# mothurmagic.py
from __future__ import print_function
import json
import os
import subprocess as sub
import random
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
        self.local_ns = self.shell.user_ns.copy()

        # Load _mothur_current from the local_ns if it exists. If it does not exist try loading from file.
        # If file does not exist assume this is the first time %%mothur has been run in this notebook
        # and create the entry in the local ns.
        if '_mothur_current' not in self.local_ns:
            try:
                with open('mothur.current.json', 'r') as in_handle:
                    _mothur_current = json.load(in_handle)
                    self.local_ns['_mothur_current'] = _mothur_current
            except IOError as e:
                # file doesn't exist or can't be read so create new user_ns entry for current
                #TODO differentiate permission error from file does not exist error.
                print('Couldn\'t load _mothur.current variables from file: ', e.args[1])
                _mothur_current = {}
                self.local_ns['_mothur_current'] = _mothur_current

        self.number = line
        self.code = cell

        #commands = self.code.split("\n")

        commands = parse_input(self)
        mothurbatch = "; ".join(commands)
        output = run_command(mothurbatch)
        output_files = parse_output(output)

        # update _mothur_current and push to notebook environment
        self.local_ns['_mothur_current'].update(output_files)
        self.shell.user_ns.update(self.local_ns)

        # create/overwrite mothur.current.json with contents of _mothur_current
        # from current notebook environment.
        try:
            with open('mothur.current.json', 'w') as out_handle:
                json.dump(self.shell.user_ns['_mothur_current'], out_handle)
        except IOError as e:
            #TODO differentiate permission error from file does not exist error.
            print('Couldn\'t save _mothur_current variables to file: ', e.ars[1])

        display_output(output)


def parse_input(self):
    """Parse commands and insert current variables form local namespace.

    Prepends commands with set.commands to set mothur current varibales with variables from
    local namespace. Appends get.current to end of commands so that output will contain new
    current variables for parsing."""

    new_commands = [command for command in self.code.split("\n")]
    current_vars = ', '.join(['%s=%s' % (k, v) for k,v in self.local_ns['_mothur_current'].items()])
    new_commands.insert(0, 'set.current(%s)' % current_vars)
    new_commands.append('get.current()')
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
    current_files = {}
    for line in lines:
        if "Current files saved by mothur:" in line:
            while True:
                try:
                    output_file = (next(line for line in lines)).split()
                    if output_file:
                        file_type = output_file[0].split('=')[0]
                        file_name = output_file[0].split('=')[1]
                        current_files[file_type] = file_name
                    else:
                        break
                except StopIteration:
                    break

    return current_files


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