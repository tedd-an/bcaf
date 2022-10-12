import logging
import os
import subprocess
import time
from typing import List

# Global logging object
logger = None

def init_logger(name, verbose=False):
    global logger

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if verbose:
        logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s:%(levelname)-8s:%(message)s')
    ch.setFormatter(formatter)

    logger.addHandler(ch)

    logger.info("Logger initialized: level=%s",
                logging.getLevelName(logger.getEffectiveLevel()))

def log_info(msg):
    if logger is not None:
        logger.info(msg)

def log_error(msg):
    if logger is not None:
        logger.error(msg)

def log_debug(msg):
    if logger is not None:
        logger.debug(msg)


class CmdError(Exception):
    def __init__(self, cmd, retcode, stdout, stderr):
        super().__init__(cmd, retcode, stdout, stderr)

        self.cmd = cmd
        self.retcode = retcode
        self.stdout = stdout
        self.stderr = stderr

def cmd_run(cmd: List[str], shell=False, add_env=None, cwd=None, pass_fds=()):
    env = os.environ.copy()
    if add_env:
        env.update(add_env)

    start_time = time.time()

    proc = subprocess.Popen(cmd, shell=shell, env=env, cwd=cwd,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            pass_fds=pass_fds)

    log_info(f'CMD: {proc.args}')

    stdout, stderr = proc.communicate()
    stdout = stdout.decode("utf-8", "ignore")
    stderr = stderr.decode("utf-8", "ignore")
    proc.stdout.close()
    proc.stderr.close()

    stderr = "\n" + stderr
    if stderr[-1] == "\n":
        stderr = stderr[:-1]

    log_info(f'RET: {proc.returncode}')
    log_debug(f'STDOUT: {stdout}')
    log_debug(f'STDERR: {stderr}')

    elapsed_time = time.time() - start_time
    log_debug(f'Elapsed Execution Time: {elapsed_time:.2f}')

    if proc.returncode != 0:
        if stderr and stderr[:-1] == "\n":
            stderr = stderr[:-1]
        raise CmdError("Command Failed: %s" % (str(proc.args), ), proc.returncode, stdout, stderr)

    return stdout, stderr
