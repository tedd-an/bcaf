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
UPSTREAM_REPO=$2
UPSTREAM_BRANCH=$3
ORIGIN_BRANCH=$4
WORKFLOW=$5
SPACE=$6

echo "Input Parameters:"
echo "   TASK:             $TASK"
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
    patchwork|Patchwork|PATCHWORK)
        echo "Task: Sync Patchwork"
            # required tokens
            check_github_token
            check_email_token
            check_patchwork_token
            set_git_safe_dir $GITHUB_WORKSPACE
            update_github_token $GITHUB_REPOSITORY
            # calling sync_patchwork.py
            /sync_patchwork -c /config.json -b $WORKFLOW -r $UPSTREAM_REPO -t $SPACE -s $GITHUB_WORKSPACE
        ;;
    *)
        echo "Unknown TASK: $TASK"
        ;;
esac


