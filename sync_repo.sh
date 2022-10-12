#!/bin/sh

set -e

# Synchronize the current repo with upstream repo
#
# The source should be in $GITHUB_WORKSPACE

# Input Parameters:
UPSTREAM_REPO=$1
UPSTREAM_BRANCH=$2
ORIGIN_BRANCH=$3
WORKFLOW_BRANCH=$4

echo ">>> Setup repo <<<"
echo "    git checkout $ORIGIN_BRANCH"
git checkout $ORIGIN_BRANCH
echo "    git remote set-url origin $GITHUB_REPOSITORY"
git remote set-url origin "https://$GITHUB_ACTOR:$GITHUB_TOKEN@github.com/$GITHUB_REPOSITORY"
echo "    git remote add upstream $UPSTREAM_REPO"
git remote add upstream "$UPSTREAM_REPO"
echo "    git fetch upstream $UPSTREAM_BRANCH"
git fetch upstream $UPSTREAM_BRANCH

echo ">>> Check Origin and Upstream"
ORIGIN_HEAD=$(git log -1 --format=%H origin/master)
echo "    ORIGIN_HEAD: $ORIGIN_HEAD"
UPSTREAM_HEAD=$(git log -1 --format=%H upstream/master)
echo "    UPSTREAM_HEAD: $UPSTREAM_HEAD"

if [ "$ORIGIN_HEAD" = "$UPSTREAM_HEAD" ]; then
    echo "    Repos are already synched. Eixt..."
    exit 0
fi
echo "    Repos are NOT synced. Need to merge..."

echo ">>> Sync origin with upstream"
echo "    git remote set-branches origin *"
git remote set-branches origin '*'
echo "    git fetch origin --unshallow"
git fetch origin --unshallow
echo "    git pull --tags --rebase upstream master"
git pull --tags --rebase upstream master
echo "    git push --force origin master"
git push --force origin master

echo ">>> Cherry-pick workflow commit"
WORKFLOW_SHA=$(git log -1 --format=%H origin/$WORKFLOW_BRANCH)
echo "    workflow commit: $WORKFLOW_SHA"
echo "    git checkout -b $WORKFLOW_BRANCH origin/master"
git checkout -b $WORKFLOW_BRANCH origin/master
echo "    git branch"
git branch
echo "    git cherry-pick $WORKFLOW_SHA"
git cherry-pick $WORKFLOW_SHA
echo "    git push --force origin $WORKFLOW_BRANCH"
git push --force origin $WORKFLOW_BRANCH

echo ">>>> Done Exit"
exit 0