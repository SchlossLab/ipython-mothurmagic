# mothurmagic.py
from __future__ import print_function
import json
import os
import subprocess as sub
import random
from IPython.core.magic import Magics, magics_class, line_magic, cell_magic, line_cell_magic, Configurable
try:
    from traitlets import Bool
except ImportError:
    from IPython.utils.traitlets import Bool


class MothurMagicError(Exception):
    pass

@magics_class
class MothurMagic(Magics, Configurable):
    """Runs mothur commands from the Jupyter notebook environment.

    Provides the %%mothur magic."""

    save_to_file = Bool(False, config=True, help='Save mothur variables to file to enable persistence across notebook sessions.')

    def __init__(self, shell):
        Magics.__init__(self, shell=shell)
        Configurable.__init__(self, config=shell.config)


    @cell_magic('mothur')
    def mothur(self, line, cell):
        """Run mothur command.
        
        Usage:
        
            %%mothur 
            help()

        """

        # Save notebooks variables so we have access to them
        self.local_ns = self.shell.user_ns.copy()

        # If mothur_variables not in local namespace create entry.
        # If save_to_file is True attempt to load from file before creating new entry.
        if 'mothur_variables' not in self.local_ns:
            if self.save_to_file:
                try:
                    with open('mothur.variables.json', 'r') as in_handle:
                        mothur_variables = json.load(in_handle)
                        print('Mothur variables loaded from file.\n')
                except IOError as e:
                    # file doesn't exist or can't be read so create new user_ns entry for current
                    #TODO differentiate permission error from file does not exist error etc.
                    print('[ERROR] Couldn\'t load mothur_variables variables from file: %s.'
                          '\nIgnore this warning if this is your first time running this notebook.' % e.args[1])
                    mothur_variables = dict()
                    mothur_variables['current'], mothur_variables['dirs'] = {}, {}
            else:
                mothur_variables = dict()
                mothur_variables['current'], mothur_variables['dirs'] = {}, {}
            self.local_ns['mothur_variables'] = mothur_variables

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
        if self.save_to_file:
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

    mothur_current = namespace['mothur_variables']

    new_commands = [command for command in commands]
    current_files = ', '.join(['%s=%s' % (k, v) for k, v in mothur_current['current'].items()])
    current_dirs = ', '.join(['%s=%s' % (k, v) for k, v in mothur_current['dirs'].items()])

    new_commands.insert(0, 'set.current(%s)' % current_files)
    if mothur_current['dirs']:
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
        lines = log.readlines()

        # find first instance of set.current in the logfile
        start_idx = next(idx for idx, line in enumerate(lines) if ('mothur > %s' % commands[0]) in line)

        # find length of file
        # TODO: do this more efficiently
        file_len = len(lines[start_idx:])

        # find last instance of get.current in the logfile
        # TODO: do this more efficiently
        last_idx = next(idx for idx, line in enumerate(lines[:start_idx:-1]) if 'get.current' in line)
        output_end = (file_len - last_idx) - 1

        for idx, line in enumerate(lines[start_idx:]):
            if idx > 1000 or idx >= output_end:
                break
            print(line.strip())

    return


def load_ipython_extension(ipython):
    # The `ipython` argument is the currently active `InteractiveShell`
    # instance, which can be used in any way. This allows you to register
    # new magics or aliases, for example.
    ipython.register_magics(MothurMagic)
