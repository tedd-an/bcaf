#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import re
import argparse
import tempfile

from github import Github

from libs import init_logger, log_debug, log_error, log_info
from libs import Patchwork, GithubTool, RepoTool, EmailTool

config = None
pw = None
gh = None
temp_root = None
src_repo = None
email = None

def init_config(config_file):

    log_debug(f"Loading config file: {config_file}")
    with open(config_file, 'r') as f:
        config = json.load(f)

    return config

def init_patchwork(pw_config):
    return Patchwork(pw_config['url'], pw_config['project_name'])

def init_github(repo):
    if 'GITHUB_TOKEN' not in os.environ:
        log_error("Set GITHUB_TOKEN environment variable")
        return None

    return GithubTool(repo, os.environ['GITHUB_TOKEN'])

def init_src_repo(src_path):
    return RepoTool("src_dir", src_path)

def init_email(email_config):
    token = None

    if 'EMAIL_TOKEN' in os.environ:
        token = os.environ['EMAIL_TOKEN']

    return EmailTool(token=token, config=email_config)

def pw_series_already_checked(series):
    """
    Check if the first patch in the series is already checked
    """
    patch_1 = pw.get_patch(series['patches'][0]['id'])
    if patch_1['check'] == 'pending':
        return False
    return True

def get_pw_sid(pr_title):
    """
    Parse PR title prefix and get PatchWork Series ID
    PR Title Prefix = "[PW_S_ID:<series_id>] XXXXX"
    """
    try:
        sid = re.search(r'^\[PW_SID:([0-9]+)\]', pr_title).group(1)
    except AttributeError:
        log_error(f"Unable to find the series_id from title {pr_title}")
        return 0
    return int(sid)


def patch_get_new_file_list(patch):
    """
    Parse patch to get the file that is newly added
    """

    file_list = []

    # If patch has no contents, return empty file
    if patch == None:
        log_error("WARNING: No file found in patch")
        return file_list

    # split patch(in string) to list of string by newline
    lines = patch.split('\n')
    iter_lines = iter(lines)
    for line in iter_lines:
        try:
            if re.search(r'^\-\-\- ', line):
                if line.find('dev/null') >= 0:
                    # Detect new file. Read next line to get the filename
                    line2 = next(iter_lines)
                    file_list.append(line2[line2.find('/')+1:])
        except StopIteration:
            # End of iteration or no next line. Nothing to do. Just pass
            pass

    log_debug(f"New file in the patch: {file_list}")

    return file_list

def patch_get_file_list(patch):
    """
    Parse patch to get the file list
    """

    file_list = []

    # If patch has no contents, return empty file
    if patch == None:
        log_error("WARNING: No file found in patch")
        return file_list

    # split patch(in string) to list of string by newline
    lines = patch.split('\n')
    for line in lines:
        # Use --- (before) instead of +++ (after).
        # If new file is added, --- is /dev/null and can be ignored
        # If file is removed, file in --- still exists in the tree
        # The corner case is if the patch adds new files. Even in this case
        # even if new files are ignored, Makefile should be changed as well
        # so it still can be checked.
        if re.search(r'^\-\-\- ', line):
            # For new file, it should be dev/null. Ignore the file.
            if line.find('dev/null') >= 0:
                log_debug("New file is added. Ignore in the file list")
                continue

            # Trim the '--- /'
            file_list.append(line[line.find('/')+1:])

    log_debug(f"files found in the patch: {file_list}")

    return file_list

def series_get_file_list(series, ignore_new_file=False):
    """
    Get the list of files from the patches in the series.
    """

    file_list = []
    new_file_list = []

    for patch in series['patches']:
        full_patch = pw.get_patch(patch['id'])
        file_list += patch_get_file_list(full_patch['diff'])
        if ignore_new_file:
            new_file_list += patch_get_new_file_list(full_patch['diff'])

    if ignore_new_file == False or len(new_file_list) == 0:
        return file_list

    log_debug("Check if new file is in the file list")
    new_list = []
    for filename in file_list:
        if filename in new_file_list:
            log_debug(f"file:{filename} is in new_file_list. Don't count.")
            continue
        new_list.append(filename)

    return new_list

def filter_repo_space(space_details, series, src_dir):
    """
    Check if the series belong to this repository

    if the series[name] has exclude string
        return False
    if the series[name] has include string
        return True
    get file list from the patch in series
    if the file exist
        return True
    else
        return False
    """

    log_debug(f"Check repo space for this series[{series['id']}]")

    # Check Exclude string
    for str in space_details['exclude']:
        if re.search(str, series['name'], re.IGNORECASE):
            log_debug(f"Found EXCLUDE string: {str}")
            return False

    # Check Include string
    for str in space_details['include']:
        if re.search(str, series['name'], re.IGNORECASE):
            log_debug(f"Found INCLUDE string: {str}")
            return True

    # Get file list from the patches in the series
    file_list = series_get_file_list(series, ignore_new_file=True)
    if len(file_list) == 0:
        # Something is not right.
        log_error("ERROR: No files found in the series/patch")
        return False
    log_debug(f"Files in series={file_list}")

    # File exist in source tree?
    for filename in file_list:
        file_path = os.path.join(config['src_dir'], filename)
        if not os.path.exists(file_path):
            log_error(f"File not found: {filename}")
            return False

    # Files exist in the source tree
    print("Files exist in the source tree.")
    return True

EMAIL_MESSAGE = '''This is an automated email and please do not reply to this email.

Dear Submitter,

Thank you for submitting the patches to the linux bluetooth mailing list.
While preparing the CI tests, the patches you submitted couldn't be applied to the current HEAD of the repository.

----- Output -----
{}

Please resolve the issue and submit the patches again.


---
Regards,
Linux Bluetooth

'''

def send_email(series, content):

    receivers = []
    headers = {}

    if not config['email']['enable']:
        log_info("Email is DISABLED. Skip sending email")
        return

    if config['email']['only-maintainers']:
        receivers.extend(config['email']['maintainers'])
    else:
        receivers.append(config['email']['default-to'])
        receivers.append(series['submitter']['email'])
    log_debug(f"Email Receivers: {receivers}")

    email.set_receivers(", ".join(receivers))

    # Get the email msgid from the first patch
    patch_1 = series['patches'][0]
    headers['In-Reply-To'] = patch_1['msgid']
    headers['References'] = patch_1['msgid']
    headers['Reply-To'] = config['email']['default-to']

    # Compose email
    title = f"RE: {series['name']}"
    body = EMAIL_MESSAGE.format(content)

    email.compose(title, body, headers)
    email.send()

def create_pullrequest(series, base, head):
    title = f"[PW_SID:{series['id']}] {series['name']}"

    # Use the commit of the patch for pr body
    patch_1 = pw.get_patch(series['patches'][0]['id'])
    return gh.create_pr(title, patch_1['content'], base, head)

def series_check_patches(series):

    # Save series/patches to the local directory
    series_dir = os.path.join(temp_root, f"{series['id']}")
    if not os.path.exists(series_dir):
        os.makedirs(series_dir)
    log_debug(f"Series PATH: {series_dir}")

    # Reset source branch to base branch
    if src_repo.git_checkout(config['branch']):
        # No need to continue
        log_error(f"ERROR: Failed: git checkout {config['branch']}")
        return False

    # Create branch for series
    if src_repo.git_checkout(f"{series['id']}", create_branch=True):
        log_error(f"ERROR: Failed: git checkout -b {series['id']}")
        return False

    already_checked = pw_series_already_checked(series)
    if already_checked:
        log_info("This series is already checked")

    verdict = True
    content = ""

    # Process the patches in this series
    log_debug("Process the patches in this series")
    for patch in series['patches']:
        log_debug(f"Patch: {patch['id']}: {patch['name']}")
        patch_mbox = pw.get_patch_mbox(patch['id'])
        patch_path = os.path.join(series_dir, f"{patch['id']}.patch")
        with open(patch_path, 'w') as f:
            f.write(patch_mbox)
        log_debug(f"Patch mbox saved to file: {patch_path}")

        # Apply patch
        if src_repo.git_am(patch_path):
            # git am failed. Update patchwork/checks and abort
            verdict = False

            # Update the contents for email body
            content = src_repo.stderr

            src_repo.git_am(abort=True)

            if config['dry_run'] or already_checked:
                log_info("Skip submitting the result to PW")
                break

            pw.post_check(patch['id'], "pre-ci_am", 3, content)
            break

        # git am success
        if config['dry_run'] or already_checked:
            log_info("Skip submitting the result to PW: Success")
        else:
            pw.post_check(patch['id'], "pre-ci_am", 1, "Success")

    if not verdict:
        log_info("PRE-CI AM failed. Notify the submitter")
        if config['dry_run'] or already_checked:
            log_info("Skip sending email")
            return False

        send_email(series, content)

        return False

    if config['dry_run']:
        log_info("Dry-Run: Skip creating PR")
        return True

    # Create Pull Request
    if src_repo.git_push(f"{series['id']}"):
        log_error("Failed to push the source to Github")
        return False

    if not create_pullrequest(series, config['branch'], f"{series['id']}"):
        log_error("Failed to create pull request")
        return False

    return True

def process_series(new_series):

    log_debug("##### Processing Series #####")

    # Process the series
    for series in new_series:
        log_info(f"Series: {series['id']}")

        # If the series subject doesn't have the key-str, ignore it.
        # Sometimes, the name have null value. If that's the case, use the
        # name from the first patch and update to series name
        if series['name'] == None:
            patch_1 = series['patches'][0]
            series['name'] = patch_1['name']
            log_debug(f"updated series name: {series['name']}")

        # Filter the series by include/exclude string
        if not filter_repo_space(config['space_details'][config['space_type']],
                                 series, config['src_dir']):
            log_info(f"Not for this repo: {config['space_type']}")
            continue

        # Check if PR already exist
        if gh.pr_exist_title(f"PW_SID:{series['id']}"):
            log_info("PR exists already")
            continue

        # This series is ready to create PR
        series_check_patches(series)

    log_debug("##### Completed processing Series #####")

def search_sid_in_series(pw_sid, new_series):

    for series in new_series:
        if series['id'] == pw_sid:
            return True
    return False

def cleanup_pullrequest(new_series):

    log_debug("##### Clean Up Pull Request #####")

    prs = gh.get_prs(force=True)
    log_debug(f"Current PR: {prs}")
    for pr in prs:
        log_debug(f"PR: {pr}")
        pw_sid = get_pw_sid(pr.title)
        log_debug(f"PW_SID: {pw_sid}")

        if search_sid_in_series(pw_sid, new_series):
            log_debug("PW_SID found from PR list. Keep PR")
            continue

        log_debug("PW_SID not found from PR list. Close PR")

        if config['dry_run']:
            log_debug("Skip closing Github Pull Request")
            continue

        gh.close_pr(pr.number)

    log_debug("##### Completed Cleaning Up Pull Request #####")

def check_args(args):

    if not os.path.exists(os.path.abspath(args.config)):
        log_error(f"Invalid parameter(config) {args.config}")
        return False

    if not os.path.exists(os.path.abspath(args.repo)):
        log_error(f"Invalid parameter(repo) {args.repo}")
        return False

    if args.space_type != 'kernel' and args.space_type != 'user':
        log_error(f"Invalid parameter(space_type) {args.space_type}")
        return False

    if not os.path.exists(os.path.abspath(args.src_dir)):
        log_error(f"Invalid parameter(src_dir) {args.src_dir}")
        return False

    return True

def parse_args():
    ap = argparse.ArgumentParser(description=
                            "Manage patch series in Patchwork and create PR")
    ap.add_argument('-c', '--config', default='./config.json',
                    help='Configuration file to use')
    ap.add_argument("-r", "--repo", required=True,
                    help="Name of base repo where the PR is pushed. "
                         "Use <OWNER>/<REPO> format. i.e. bluez/bluez")
    ap.add_argument("-b", "--branch", default="workflow",
                    help="Name of branch in base_repo where the PR is pushed. "
                         "Use <BRANCH> format. i.e. workflow")
    ap.add_argument("-t", "--space-type", default="kernel",
                    help="Specify the string to distinguish the repo type: "
                         "kernel or user")
    ap.add_argument('-s', '--src-dir', required=True,
                    help='Source directory')
    ap.add_argument('-d', '--dry-run', action='store_true', default=False,
                    help='Run it without uploading the result')
    return ap.parse_args()

def main():
    global config, pw, gh, temp_root, src_repo, email

    init_logger("Sync_Patchwork", verbose=True)

    args = parse_args()
    if check_args(args):
        sys.exit(1)

    config = init_config(os.path.abspath(args.config))
    if  config == None:
        sys.exit(1)
    config['space_type'] = args.space_type
    config['branch'] = args.branch
    config['dry_run'] = args.dry_run
    config['src_dir'] = args.src_dir

    pw = init_patchwork(config['patchwork'])
    gh = init_github(args.repo)
    if not gh:
        log_error("Failed to init github object")
        sys.exit(1)
    src_repo = init_src_repo(args.src_dir)
    email = init_email(config['email'])

    # Set temp workspace
    temp_root = tempfile.TemporaryDirectory().name
    log_info(f"Temp Root Dir: {temp_root}")

    # Process the series, state 1 = NEW
    new_series = pw.get_series_by_state(1)
    if len(new_series) == 0:
        log_info("No new patches/series found. Done. Exit")
        return

    # Process Series
    process_series(new_series)

    # Cleanup PR
    cleanup_pullrequest(new_series)

    log_debug("----- DONE -----")

if __name__ == "__main__":
    main()