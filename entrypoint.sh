#!/bin/bash

set -echo

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

echo "Input Parameters:"
echo "   TASK:             $TASK"
echo "   UPSTREAM_REPO:    $UPSTREAM_REPO"
echo "   UPSTREAM_BRANCH:  $UPSTREAM_BRANCH"
echo "   ORIGIN_BRANCH:    $ORIGIN_BRANCH"
echo "   WORKFLOW:         $WORKFLOW"

# Check Github Token
function check_github_token {
    if [ -z "$GITHUB_TOKEN" ]; then
        echo "Set GITHUB_TOKEN environment variable"
        exit 1
    fi
}

# Dispatch the task
case $TASK in
    sync|Sync|SYNC)
        echo "Task: Sync Repo"
            # requires GITHUB_TOKEN
            check_github_token
            # calling sync_repo
            # param: upstream_repo
            # param: upstream_branch
            # param: origin_branch
            # param: workflow
            ./sync_repo.sh $UPSTREAM_REPO $UPSTREAM_BRANCH $ORIGIN_BRANCH $WORKFLOW
        ;;
    *)
        echo "Unknown TASK: $TASK"
        ;;
esac

