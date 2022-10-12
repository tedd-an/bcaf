from github import Github

import libs

class GithubTool:
    def __init__(self, repo, pr, token=None):
        self._repo = Github(token).get_repo(repo)
        self._pr = self._repo.get_pull(pr)
        self._pr_commits = self._pr.get_commits()
