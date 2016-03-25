# mothurmagic.py
from __future__ import print_function
import json
import os
import subprocess as sub
import random
from IPython.core.magic import Magics, magics_class, line_magic, cell_magic, line_cell_magic


class MothurMagicError(Exception):
    pass

@magics_class
class MothurMagic(Magics):
    """Runs mothur commands from the Jupyter notebook environment.

    Provides the %%mothur magic."""


    def __init__(self, shell):
        Magics.__init__(self, shell=shell)

        # save notebooks variables so we have access to them
        self.local_ns = self.shell.user_ns.copy()

        try:
            with open('mothur.variables.json', 'r') as in_handle:
                mothur_variables = json.load(in_handle)
                print('Mothur variables loaded from file.')
        except IOError as e:
            # file doesn't exist or can't be read so create new user_ns entry for current
            #TODO differentiate permission error from file does not exist error etc.
            print('[ERROR] Couldn\'t load mothur_variables variables from file: %s.'
                  '\nIgnore this warning if this is your first time running this notebook.' % e.args[1])
            mothur_variables = dict()
            mothur_variables['current'], mothur_variables['dirs'] = {}, {}
        self.local_ns['mothur_variables'] = mothur_variables


    @cell_magic('mothur')
    def mothur(self, line, cell):
        """Run mothur command.
        
        Usage:
        
            %%mothur 
            help()

        """

        self.number = line
        #self.code = cell
        self.commands = cell.split("\n")

        commands = _parse_input(self.commands, self.local_ns)
        mothurbatch = '; '.join(commands)
        output = _run_command(mothurbatch)
        output_files, dirs = _parse_output(output)

        # update mothur_variables and push to notebook environment
        if output_files:
            self.local_ns['mothur_variables']['current'].update(output_files)
        if dirs:
            self.local_ns['mothur_variables']['dirs'].update(dirs)
        self.shell.user_ns.update(self.local_ns)

        _display_output(self.commands, output)

        #print('logfile: %s' % output)

        # overwrite mothur.current.json with contents of mothur_variables from current notebook environment.
        try:
            with open('mothur.variables.json', 'w') as out_handle:
                json.dump(self.shell.user_ns['mothur_variables'], out_handle)
                print('Mothur variables saved to file.')
        except IOError as e:
            #TODO differentiate permission error from file does not exist error.
            print('[ERROR] Couldn\'t save mothur_variables variables to file: ', e.ars[1])


def _parse_input(commands, namespace):
    """Parse commands and insert current variables form local namespace.

    Prepends commands with set.commands and set.dir to set mothur's current variables with variables from
    the local namespace. Appends get.current to end of commands so that output will contain new current
    variables for parsing.

    Arguments:
        - commands:     list of mothur commands
        - namespace:    local notebook namespace
    """

    new_commands = [command for command in commands]
    current_files = ', '.join(['%s=%s' % (k, v) for k, v in namespace['mothur_variables']['current'].items()])
    current_dirs = ', '.join(['%s=%s' % (k, v) for k, v in namespace['mothur_variables']['dirs'].items()])

    new_commands.insert(0, 'set.current(%s)' % current_files)
    new_commands.insert(0, 'set.dir(%s)' % current_dirs)
    new_commands.append('get.current()')

    return new_commands


def _run_command(mothurbatch):
    """Run mothur using command line mode.

    Arguments:
        - mothurbatch:  batched mothur commands separated by ';'

    Output from mothur is stored in a randomly numbered log file.
    """

    # TODO: check that logfile name does not already exist
    random.seed()
    rn = random.randint(10000,99999)
    logfile = "mothur.ipython.%d.logfile" % rn
    mothur_command = "set.logfile(name=%s); " % logfile + mothurbatch

    try:
        sub.call(['mothur',  '#%s' % mothur_command])
    except OSError as e:
        if e.errno == os.errno.ENOENT:
            try:
                sub.call(['./mothur',  "#%s" % mothur_command])
            except OSError as e:
                print('Can\'t open mothur: %s' % e.args[1])  # "mothur not in path"
        else:
            print('Something went wrong while opening mothur. Here\'s what I know: %s' % e)
    except:
        print('uh oh, something went really wrong.')

    return logfile


def _parse_output(output):
    """Parse mothur logfile to extract current files.

    Arguments:
        - output:   file name of logfile containing mothur output
    """

    headers = {'Current input directory saved by mothur:': 'input',
               'Current output directory saved by mothur:': 'output',
               'Current default directory saved by mothur:': 'tempdefault'}

    current_files = {}
    dirs = {}
    with open(output, 'r') as log:
        lines = (line for line in log.readlines())
        for line in lines:
            if 'Current files saved by mothur:' in line:
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
            for k, v in headers.items():
                if k in line:
                    mothur_dir = line.split(' ')[-1].split('\n')[0]
                    dirs[v] = mothur_dir

    return current_files, dirs


def _display_output(commands, logfile):
    """Print contents of logfile to the notebook.

    Arguments:
        - commands:   list of mothur commands
        - logfile:    path of the output log file generated by mothur
    """

    with open(logfile, 'r') as log:
        count = 0
        lines = log.readlines()
        first_command = commands[0]
        for idx, line in enumerate(lines):
            if first_command in line:
                for l in lines[idx:]:
                    if 'get.current' in l:
                        break
                    if count > 1000:
                        return 'output exceeded 1000 lines. See logfile %s for complete output.' % logfile
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
