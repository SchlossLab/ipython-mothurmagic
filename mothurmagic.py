# mothurmagic.py
import os
import subprocess as sub
import random
from IPython.core.magic import (Magics, magics_class, line_magic, cell_magic, line_cell_magic)
from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring
from IPython.display import display_pretty

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
        mothurbatch = "; ".join(commands)
        random.seed()
        rn = random.randint(10000,99999)
        logfile = "mothur.ipython.%d.logfile" % rn
        mothurbatch = "set.logfile(name=%s); " % logfile + mothurbatch


        try:
            sub.call(['mothur',  "#%s" % mothurbatch])
        except OSError as e:
            if e.errno == os.errno.ENOENT:
                try:
                    sub.call(['./mothur',  "#%s" % mothurbatch])
                except OSError as e:
                    return "Can't open mothur: " + e[1] #"mothur not in path"
            else:
                return "Something went wrong while opening mothur. Here's what I know: " + e 
        except: 
            return "uh oh, something went really wrong."
            
        with open(logfile, 'r') as log:
            lines = log.readlines()
            for idx, line in enumerate(lines):
                if line.startswith("mothur >") and not line.startswith("mothur > set.logfile"):
                    for l in lines[idx:]:
                        print l.strip()
                    break
        


def load_ipython_extension(ipython):
    # The `ipython` argument is the currently active `InteractiveShell`
    # instance, which can be used in any way. This allows you to register
    # new magics or aliases, for example.
    ipython.register_magics(Mothur)

