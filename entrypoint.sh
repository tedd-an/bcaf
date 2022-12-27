#!/bin/bash

set -e

echo "Environment Variables:"
echo "   Workflow:   $GITHUB_WORKFLOW"
echo "   Action:     $GITHUB_ACTION"
echo "   Actor:      $GITHUB_ACTOR"
echo "   Repository: $GITHUB_REPOSITORY"
echo "   Event-name: $GITHUB_EVENT_NAME"
echo "   Event-path: $GITHUB_EVENT_PATH"
echo "   Workspace:  $GITHUB_WORKSPACE"
echo "   SHA:        $GITHUB_SHA"
echo "   REF:        $GITHUB_REF"
echo "   HEAD-REF:   $GITHUB_HEAD_REF"
echo "   BASE-REF:   $GITHUB_BASE_REF"
echo "   PWD:        $(pwd)"

TASK=$1
BASE_DIR=$2
UPSTREAM_REPO=$3
UPSTREAM_BRANCH=$4
ORIGIN_BRANCH=$5
WORKFLOW=$6
SPACE=$7

echo "Input Parameters:"
echo "   TASK:             $TASK"
echo "   BASE_DIR          $BASE_DIR"
echo "   UPSTREAM_REPO:    $UPSTREAM_REPO"
echo "   UPSTREAM_BRANCH:  $UPSTREAM_BRANCH"
echo "   ORIGIN_BRANCH:    $ORIGIN_BRANCH"
echo "   WORKFLOW:         $WORKFLOW"
echo "   SPACE:            $SPACE"

# Setup GIT config
function set_git_safe_dir {
    if [ -z "$1" ]; then
        echo "set_git_safe_dir: Invalid parameter"
        exit 1
    fi

    echo "Add repo to safe.directory: $1"
    echo "$ git config --global --add safe.directory $1"
    git config --global --add safe.directory $1
}

# Setup GIT Remote URL with github token
function update_github_token {
    if [ -z "$1" ]; then
        echo "update_github_token: Invalid parameter"
        exit 1
    fi
    echo "Update repo origin with github token"
    echo "$ git remote set-url origin https://x-access-token:$GITHUB_TOKEN@github.com/$1"
    git remote set-url origin "https://x-access-token:$GITHUB_TOKEN@github.com/$1"
}

# Clone ELL
function clone_ell {
    # remove if already exist
    DEST_DIR=$1
    rm -rf $DEST_DIR
    git clone --depth=1 https://git.kernel.org/pub/scm/libs/ell/ell $DEST_DIR
    cd $DEST_DIR
    git log -1 --format='%H'
}

# Clone BlueZ
function clone_bluez {
    # remove if already exist
    DEST_DIR=$1
    rm -rf $DEST_DIR
    git clone --depth=1 https://git.kernel.org/pub/scm/bluetooth/bluez $DEST_DIR
    cd $DEST_DIR
    git log -1 --format='%H'
}

# Check Github Token
function check_github_token {
    if [ -z "$GITHUB_TOKEN" ]; then
        echo "Set GITHUB_TOKEN environment variable"
        exit 1
    fi
}

function check_patchwork_token {
    if [ -z "$PATCHWORK_TOKEN" ]; then
        echo "Set PATCHWORK_TOKEN environment variable"
        exit 1
    fi
}

function check_email_token {
    if [ -z "$EMAIL_TOKEN" ]; then
        echo "Set EMAIL_TOKEN environment variable"
        exit 1
    fi
}

git config --global user.name "$GITHUB_ACTOR"
git config --global user.email "$GITHUB_ACTOR@users.noreply.github.com"

# Dispatch the task
case $TASK in
    sync|Sync|SYNC)
        echo "Task: Sync Repo"
            # requires GITHUB_TOKEN
            check_github_token
            set_git_safe_dir $GITHUB_WORKSPACE
            # calling sync_repo
            # param: upstream_repo
            # param: upstream_branch
            # param: origin_branch
            # param: workflow
            /sync_repo.sh $UPSTREAM_REPO $UPSTREAM_BRANCH $ORIGIN_BRANCH $WORKFLOW
        ;;
    cleanup|Cleanup|CLENAUP)
        echo "Task: Clean Up PR"
            # requires GITHUB_TOKEN
            check_github_token
            /cleanup_pr.py -d $GITHUB_REPOSITORY
        ;;
    patchwork|Patchwork|PATCHWORK)
        echo "Task: Sync Patchwork"
            # required tokens
            check_github_token
            check_email_token
            check_patchwork_token
            set_git_safe_dir $GITHUB_WORKSPACE
            update_github_token $GITHUB_REPOSITORY
            # calling sync_patchwork.py
            /sync_patchwork.py -d -c /config.json -b $WORKFLOW -s $GITHUB_WORKSPACE $SPACE $GITHUB_REPOSITORY
        ;;
    ci|CI|Ci)
        echo "Task: CI"
            check_github_token
            check_email_token
            check_patchwork_token

            # Get PR number from GITHUB_REF (refs/pull/#/merge)
            PR=${GITHUB_REF#"refs/pull/"}
            PR=${PR%"/merge"}
            echo "Target PR: $PR"

            # For CI, assume that source is cloned under src
            set_git_safe_dir $GITHUB_WORKSPACE/$BASE_DIR/src

            clone_ell $GITHUB_WORKSPACE/$BASE_DIR/ell
            set_git_safe_dir $GITHUB_WORKSPACE/$BASE_DIR/ell

            if [ $SPACE == "kernel" ]; then
                clone_bluez $GITHUB_WORKSPACE/$BASE_DIR/bluez
                set_git_safe_dir $GITHUB_WORKSPACE/$BASE_DIR/bluez
                /ci.py -c /config.json -z $GITHUB_WORKSPACE/$BASE_DIR/bluez    \
                                       -e $GITHUB_WORKSPACE/$BASE_DIR/ell      \
                                       -k $GITHUB_WORKSPACE/$BASE_DIR/src      \
                                       -d kernel $GITHUB_REPOSITORY $PR
            elif [ $SPACE == "user" ]; then
                /ci.py -c /config.json -z $GITHUB_WORKSPACE/$BASE_DIR/src      \
                                       -e $GITHUB_WORKSPACE/$BASE_DIR/ell      \
                                       -d user $GITHUB_REPOSITORY $PR
            else
                echo "Unknown SPACE: $SPACE"
                exit 1
            fi
        ;;
    *)
        echo "Unknown TASK: $TASK"
        eixt 1
        ;;
esac


