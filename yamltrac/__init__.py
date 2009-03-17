#
from __future__ import with_statement
import yaml
from os import path

def issues(repositories=[], dbfolder='issues', status=['open']):
    """Return the list of issues with the given statuses in dictionary form"""
    issues = {}
    for repo in repositories:
        try:
            with open(path.join(repo, dbfolder, 'issues.yaml')) as issuesfile:
                issues[path.basename(repo)] = dict(issue for issue in yaml.load(issuesfile.read()).iteritems() if issue[0] != 'skeleton')
        except IOError:
            # Not all listed repositories have an issue tracking database
            pass
    for issuedb in issues:
        for issue in issues[issuedb].itervalues():
            # A proper version of this would figure out the actual time value.
            # We'll take a shortcut and look at the word.
            try:
                timescale = issue['estimate'].split()[1].rstrip('s')
                if timescale.lower() == 'hour':
                    scale = 'short'
                elif timescale.lower() == 'day':
                    scale = 'medium'
                else:
                    scale = 'long'
            except AttributeError:
                scale = 'unplanned'

            issue['estimate'] = {'scale':scale, 'text':issue['estimate']}
    return issues

def issue(repositories=[], dbfolder='issues', id=None, status=['open']):
    issue = None
    for repo in repositories:
        try:
            with open(path.join(repo, dbfolder, id)) as issuefile:
                issue = yaml.load(issuefile.read())
        except IOError:
            # Not all listed repositories have an issue tracking database
            pass
    return issue
