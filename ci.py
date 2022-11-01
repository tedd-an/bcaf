#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import re
import argparse
import tempfile

from libs import init_logger, log_debug, log_error, log_info, pr_get_sid
from libs import Patchwork, GithubTool, RepoTool, EmailTool

import ci

config = None
pw = None
gh = None
src_repo = None
email = None

def init_config(config_file):

    config = None

    log_debug(f"Loading config file: {config_file}")
    with open(os.path.abspath(config_file), 'r') as f:
        config = json.load(f)

    return config

def init_patchwork(pw_config):
    try:
        ret = Patchwork(pw_config['url'], pw_config['project_name'])
    except ValueError as e:
        log_error("Failed to initialize Patchwork class")
        return None

    log_debug("Initialized Patchwork object")
    return ret

def init_github(repo):
    if 'GITHUB_TOKEN' not in os.environ:
        log_error("Set GITHUB_TOKEN environment variable")
        return None

    try:
        ret = GithubTool(repo, os.environ['GITHUB_TOKEN'])
    except:
        log_error("Failed to initialize GithubTool class")
        return None

    log_debug("Initialized GithubTool object")

    return ret

def init_src_repo(src_dir):
    try:
        log_debug(f"SRC: {src_dir}")
        ret = RepoTool("src_dir", src_dir)
    except:
        log_error("Failed to initialize RepoTool class")
        return None

    log_debug("Initialized RepoTool object")

    return ret

def init_email(email_config):
    token = None

    if 'EMAIL_TOKEN' in os.environ:
        token = os.environ['EMAIL_TOKEN']

    return EmailTool(token=token, config=email_config)

def check_args(args):

    if not os.path.exists(os.path.abspath(args.config)):
        log_error(f"Invalid parameter(config) {args.config}")
        return False

    if not os.path.exists(os.path.abspath(args.bluez_dir)):
        log_error(f"Invalid parameter(src_dir) {args.bluez_dir}")
        return False

    if not os.path.exists(os.path.abspath(args.ell_dir)):
        log_error(f"Invalid parameter(ell_dir) {args.ell_dir}")
        return False

    if args.space == 'kernel':
        # requires kernel_dir
        if not args.kernel_dir:
            log_error("Missing required parameter: kernel_dir")
            return False

        if not os.path.exists(os.path.abspath(args.kernel_dir)):
            log_error(f"Invalid parameter(kernel_dir) {args.kernel_dir}")
            return False

    return True

def parse_args():
    ap = argparse.ArgumentParser(description="Run CI tests")
    ap.add_argument('-c', '--config', default='./config.json',
                    help='Configuration file to use. default=./config.json')
    ap.add_argument('-b', '--branch', default='workflow',
                    help='Name of branch in base_repo where the PR is pushed. '
                         'Use <BRANCH> format. default: workflow')
    ap.add_argument('-z', '--bluez-dir', required=True,
                    help='BlueZ source directory.')
    ap.add_argument('-e', '--ell-dir', required=True,
                    help='ELL source directory.')
    ap.add_argument('-k', '--kernel-dir', default=None,
                    help='Kernel source directory')
    ap.add_argument('-d', '--dry-run', action='store_true', default=False,
                    help='Run it without uploading the result. default=False')

    # Positional parameter
    ap.add_argument('space', choices=['user', 'kernel'],
                    help="user or kernel space")
    ap.add_argument("repo",
                    help="Name of Github repository. i.e. bluez/bluez")
    ap.add_argument('pr_num', type=int,
                    help='Pull request number')
    return ap.parse_args()

# Email Message Templates

EMAIL_MESSAGE = '''This is automated email and please do not reply to this email!

Dear submitter,

Thank you for submitting the patches to the linux bluetooth mailing list.
This is a CI test results with your patch series:
PW Link:{pw_link}

---Test result---

{content}

---
Regards,
Linux Bluetooth

'''

def github_pr_post_result(test):

    pr = gh.get_pr(config['pr_num'], force=True)

    comment = f"**{test.name}**\n"
    comment += f"Desc: {test.desc}\n"
    comment += f"Duration: {test.elapsed:.2f} seconds\n"
    comment += f"**Result: {test.status}**\n"

    if test.output:
        comment += f"Output:\n```\n{test.output}\n```"

    return gh.pr_post_comment(pr, comment)

def is_maintainers_only(email_config):
    if 'only-maintainers' in email_config and email_config['only-maintainers']:
        return True
    return False

def get_receivers(email_config, submitter):
    log_debug("Get the list of email receivers")

    receivers = []
    if is_maintainers_only(email_config):
        # Send only to the maintainers
        receivers.extend(email_config['maintainers'])
    else:
        # Send to default-to and submitter
        receivers.append(email_config['default-to'])
        receivers.append(submitter)

    return receivers

def send_email(content):
    headers = {}
    email_config = config['email']

    pr = gh.get_pr(config['pr_num'], force=True)
    series_id = pr_get_sid(pr.title)
    series = pw.get_series(series_id)
    patch_1 = series['patches'][0]
    body = EMAIL_MESSAGE.format(pw_link=series['web_url'], content=content)

    headers['In-Reply-To'] = patch_1['msgid']
    headers['References'] = patch_1['msgid']

    if not is_maintainers_only(email_config):
        headers['Reply-To'] = email_config['default-to']

    receivers = get_receivers(email_config, series['submitter']['email'])
    email.set_receivers(receivers)
    email.compose("RE: " + series['name'], body, headers)

    if config['dry_run']:
        log_info("Dry-Run is set. Skip sending email")
        return

    log_info("Sending Email...")
    email.send()

def report_ci(test_list):
    """Generate the CI result and send email"""
    results = ""
    summary = "Test Summary:\n"

    line = "{name:<30}{result:<10}{elapsed:.2f} seconds\n"
    fail_msg = "Test: {name} - {result}\nDesc: {desc}\nOutput:\n{output}\n"

    for test in test_list:
        if test.verdict == ci.Verdict.PASS:
            # No need to add result of passed tests to simplify the email
            summary += line.format(name=test.name, result='PASS',
                                   elapsed=test.elapsed())
            continue

        # Rest of the verdicts use same output format
        results += "##############################\n"
        results += fail_msg.format(name=test.name, result=test.verdict.name,
                                   desc=test.desc, output=test.output)
        summary += line.format(name=test.name, result=test.verdict.name,
                               elapsed=test.elapsed())

    if results != "":
        results = "Details\n" + results

    # Sending email
    send_email(summary + '\n' + results)

def create_test_list_user():
    # Setup CI tests
    # AR: Maybe read the test from config?
    #
    # These are the list of tests:
    test_list = []
    pr = gh.get_pr(config['pr_num'], force=True)
    series = pw.get_series(pr_get_sid(pr.title))
    dry_run = config['dry_run']

    ########################################
    # Test List
    ########################################

    # CheckPatch
    test_list.append(ci.CheckPatch(pw, series, src_repo.path(), dry_run=dry_run))

    # GitLint
    test_list.append(ci.GitLint(pw, series, src_repo.path(), dry_run=dry_run))

    # BuildELL
    test_list.append(ci.BuildEll(pw, series, config['ell_dir'], dry_run=dry_run))

    # Build BlueZ
    test_list.append(ci.BuildBluez(pw, series, src_repo.path(), dry_run=dry_run))

    # Make Check
    test_list.append(ci.MakeCheck(pw, series, src_repo.path(), dry_run=dry_run))

    # Make distcheck
    test_list.append(ci.MakeDistcheck(pw, series, src_repo.path(), dry_run))

    # Make check w/ Valgrind
    test_list.append(ci.CheckValgrind(pw, series, src_repo.path(), dry_run))

    # Make with Exteranl ELL
    test_list.append(ci.MakeExtEll(pw, series, src_repo.path(), dry_run))

    # Incremental Build
    test_list.append(ci.IncrementalBuild(pw, series, "user", src_repo.path(), dry_run))

    # Run ScanBuild
    test_list.append(ci.ScanBuild(pw, series, src_repo.path(), dry_run))

    return test_list

def create_test_list_kernel():
    # Setup CI tests for kernel test
    # AR: Maybe read the test from config?
    #
    # These are the list of tests:
    test_list = []
    pr = gh.get_pr(config['pr_num'], force=True)
    series = pw.get_series(pr_get_sid(pr.title))
    dry_run = config['dry_run']
    ci_config = config['space_details']['kernel']['ci']

    ########################################
    # Test List
    ########################################

    # CheckPatch
    # If available, need to apply "ignore" flag
    # checkaptch_pl = os.path.join(src_repo.path(), 'scripts', 'checkpatch.pl')
    # test_list.append(ci.CheckPatch(pw, series, src_repo.path(), dry_run=dry_run,
    #                  checkpatch_pl=checkaptch_pl,
    #                  ignore=ci_config['CheckPatch']['ignore']))
    # # GitLint
    # test_list.append(ci.GitLint(pw, series, src_repo.path(), dry_run=dry_run))

    # # SubjectPrefix
    # test_list.append(ci.SubjectPrefix(pw, series, src_repo.path(), dry_run))

    # # BuildKernel
    # # Get the config from the bluez source tree
    ci_config = os.path.join(config['bluez_dir'], "doc", "ci.config")
    # test_list.append(ci.BuildKernel(pw, series, src_repo.path(),
    #                  config=ci_config, dry_run=dry_run))

    # # BuildKernel32
    # test_list.append(ci.BuildKernel32(pw, series, src_repo.path(),
    #                  config=ci_config, dry_run=dry_run))

    # # TestRunnerSetup
    # tester_config = os.path.join(config['bluez_dir'], "doc", "tester.config")
    # test_list.append(ci.TestRunnerSetup(pw, series, src_repo.path(),
    #                  bluez_src_dir=config['bluez_dir'],
    #                  tester_config=tester_config, dry_run=dry_run))

    # # TestRunner-*
    # testrunner_list = ci_config['TestRunner']['tester-list']
    # for runner in testrunner_list:
    #     log_debug(f"Add {runner} instance to test_list")
    #     test_list.append(ci.TestRunner(runner, pw, series,
    #                      bluez_src_dir=config['bluez_dir'],
    #                      src_dir=src_repo.path(),
    #                      dry_run=dry_run))

    # # Incremental Build
    test_list.append(ci.IncrementalBuild(pw, series, "kernel", src_repo.path(),
                                         config=ci_config, dry_run=dry_run))

    return test_list

def run_ci(space):

    num_fails = 0

    test_list = []
    if space == 'user':
        test_list = create_test_list_user()
    else:
        test_list = create_test_list_kernel()

    log_info(f"Test list is created: {len(test_list)}")
    log_debug("+--------------------------+")
    log_debug("|          Run CI          |")
    log_debug("+--------------------------+")
    for test in test_list:
        log_info("##############################")
        log_info(f"## CI: {test.name}")
        log_info("##############################")

        try:
            test.run()
        except ci.EndTest as e:
            log_error(f"Test Ended(Failure): {test.name}:{test.verdict.name}")
        except Exception as e:
            log_error(f"Test Ended(Exception): {test.name}: {e.__class__}")
        finally:
            test.post_run()

        if test.verdict != ci.Verdict.PASS:
            num_fails += 1

        if config['dry_run']:
            log_info("Skip submitting result to Github: dry_run=True")
            continue

        log_debug("Submit the result to github")
        # AR: Submit the result to GH
        if not github_pr_post_result(test):
            log_error("Failed to submit the result to Github")

    log_info(f"Total number of failed test: {num_fails}")
    log_debug("+--------------------------+")
    log_debug("|        ReportCI          |")
    log_debug("+--------------------------+")
    report_ci(test_list)

    return num_fails

def main():
    global config, pw, gh, src_repo, email

    init_logger("Bluez_CI", verbose=True)

    args = parse_args()
    if not check_args(args):
        sys.exit(1)

    config = init_config(os.path.abspath(args.config))
    if not config:
        sys.exit(1)

    # Save the input arguments to config.
    config['branch'] = args.branch
    config['dry_run'] = args.dry_run
    config['bluez_dir'] = args.bluez_dir
    config['ell_dir'] = args.ell_dir
    config['kernel_dir'] = args.kernel_dir
    config['pr_num'] = args.pr_num
    config['space'] = args.space

    pw = init_patchwork(config['patchwork'])
    if not pw:
        sys.exit(1)

    gh = init_github(args.repo)
    if not gh:
        sys.exit(1)

    if args.space == "user":
        main_src = args.bluez_dir
    elif args.space == "kernel":
        main_src = args.kernel_dir
    else:
        log_error(f"Invalid parameter(space) {args.space}")
        sys.exit(1)

    src_repo = init_src_repo(main_src)
    if not src_repo:
        sys.exit(1)

    email = init_email(config['email'])

    # Setup Source for the test that needs to access the base like incremental
    # build.
    # It needs to fetch the extra patches: # of commit in PR + 1
    pr = gh.get_pr(args.pr_num, force=True)

    cmd = ['fetch', f'--depth={pr.commits+1}']
    if src_repo.git(cmd):
        log_error("Failed to fetch commits in the patches")
        sys.exit(1)

    num_fails = run_ci(args.space)

    log_debug("----- DONE -----")

    sys.exit(num_fails)

if __name__ == "__main__":
    main()