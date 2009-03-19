#
from __future__ import with_statement
import yaml
from mercurial import hg, commands, ui
from os import path
NEW_TICKET_TAG='YAMLTrac-new-ticket'

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
    # Change this to only accept one repository and to return a history
    issue = None
    for repo in repositories:
        try:
            with open(path.join(repo, dbfolder, id)) as issuefile:
                issue = yaml.load(issuefile.read())
        except IOError:
            # Not all listed repositories have an issue tracking database
            pass
    return issue

def add(repository, issue, dbfolder='issues', status=['open']):
    myui = ui.ui()
    repo = hg.repository(myui, repository)
    # This can fail in an empty repository.  Handle this
    commands.tag(myui, repo, NEW_TICKET_TAG, force=True, message='TICKETPREP: %s' % issue['title'])
    context = repo['tip']
    ticketid = ''.join('%x' % ord(letter) for letter in context.node())
    try:
        with open(path.join(repository, dbfolder, ticketid), 'w') as issuesfile:
            issuesfile.write(yaml.safe_dump(issue, default_flow_style=False))
        commands.add(myui, repo, path.join(repository, dbfolder, ticketid))
    except IOError:
        return false
    try:
        with open(path.join(repository, dbfolder, 'issues.yaml'), 'r') as issuesfile:
            issues = yaml.load(issuesfile.read())
        with open(path.join(repository, dbfolder, 'issues.yaml'), 'w') as issuesfile:
            issues[ticketid] = issue
            issuesfile.write(yaml.safe_dump(issues, default_flow_style=False))
    except IOError:
        return false

def close(repository, ticketid, dbfolder='issues', status=['open']):
    # This just deletes the ticket, we should keep them around temporarily and call it fixed.
    myui = ui.ui()
    repo = hg.repository(myui, repository)
    commands.remove(myui, repo, path.join(repository, dbfolder, ticketid))
    try:
        with open(path.join(repository, dbfolder, 'issues.yaml'), 'r') as issuesfile:
            issues = yaml.load(issuesfile.read())
        with open(path.join(repository, dbfolder, 'issues.yaml'), 'w') as issuesfile:
            del issues[ticketid]
            issuesfile.write(yaml.safe_dump(issues, default_flow_style=False))
    except IOError:
        return false
