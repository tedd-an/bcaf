import logging
import os
import subprocess
import time
import re
from typing import List, Dict, Tuple

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

def pr_get_sid(pr_title):
    """
    Parse PR title prefix and get PatchWork Series ID
    PR Title Prefix = "[PW_S_ID:<series_id>] XXXXX"
    """

    try:
        sid = re.search(r'^\[PW_SID:([0-9]+)\]', pr_title).group(1)
    except AttributeError:
        log_error(f"Unable to find the series_id from title {pr_title}")
        sid = None

    return sid

def cmd_run(cmd: List[str], shell: bool = False, add_env: Dict[str, str] = None,
            cwd: str = None, pass_fds=()) -> Tuple[str, str, str]:
    log_info(f"------------- CMD_RUN -------------")
    log_info(f"CMD: {cmd}")

    stdout = ""

    # Update ENV
    env = os.environ.copy()
    if add_env:
        env.update(add_env)

    start_time = time.time()

    proc = subprocess.Popen(cmd, shell=shell, env=env, cwd=cwd,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            bufsize=1, universal_newlines=True,
                            pass_fds=pass_fds)
    log_debug(f"PROC args: {proc.args}")

    # Print the stdout in realtime
    for line in proc.stdout:
        log_debug("> " + line.rstrip('\n'))
        stdout += line

    # STDOUT returned by proc.communicate() is empty because it was all consumed
    # by the above read.
    _stdout, stderr = proc.communicate()
    proc.stdout.close()
    proc.stderr.close()

    stderr = "\n" + stderr
    if stderr[-1] == "\n":
        stderr = stderr[:-1]

    log_info(f'RET: {proc.returncode}')
    # No need to print STDOUT here again. It is already printed above
    # log_debug(f'STDOUT:{stdout}')
    # Print STDOUT only if ret != 0
    if proc.returncode:
        log_debug(f'STDERR:{stderr}')

    if proc.returncode != 0:
        if stderr and stderr[:-1] == "\n":
            stderr = stderr[:-1]

    elapsed = time.time() - start_time

    log_info(f"------------- CMD_RUN END ({elapsed:.2f} s) -------------")
    return proc.returncode, stdout, stderr

def patch_file_list(diff):
    """Read the patch diff and get the list of files in the patch.
    This function returns the tuple with (file_list, new_file_list)
    """
    file_list = []
    new_file_list = []
    # Check input parameter
    if not diff or len(diff) == 0:
        log_error("WARNING: Patch diff is empty")
        return (file_list, new_file_list)
    lines = diff.split('\n')
    # Using iter() method so instead of normal string iteration.
    # In case of new file is added, it needs to read the next time to get the
    # name of new file added.
    iter_lines = iter(lines)
    for line in iter_lines:
        try:
            # Use --- (before) instead of +++ (after)
            if re.search(r'^\-\-\- ', line):
                # For new file, it should be /dev/null.
                log_debug(f"Found the file name...{line}")
                if line.find('dev/null') >= 0:
                    log_debug("Detect new file. Add it to new_file_list")
                    # Need to check the next line to get new file name
                    next_line = next(iter_lines)
                    new_file_list.append(next_line[next_line.find('/')+1:])
                    continue
                # Existing file. Trim '--- /'
                log_debug("Detect file. Add it to file_list")
                file_list.append(line[line.find('/')+1:])
        except StopIteration:
            # End of iteration or no next line. Nothing to do.
            pass
    log_debug(f"files found in patch diff: {file_list}")
    log_debug(f"new files found in patch diff: {new_file_list}")
    return (file_list, new_file_list)

