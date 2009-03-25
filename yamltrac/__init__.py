#
from __future__ import with_statement
import yaml
from mercurial import hg, commands, ui, util
from os import path
NEW_TICKET_TAG='YAMLTrac-new-ticket'

def issues(repositories=[], dbfolder='issues', status=['open']):
    """Return the list of issues with the given statuses in dictionary form"""
    issues = {}
    for repo in repositories:
        try:
            with open(path.join(repo, dbfolder, 'issues.yaml')) as issuesfile:
                issues[path.basename(repo)] = dict(issue for issue in yaml.load(issuesfile.read()).iteritems() if issue[0] != 'skeleton' and issue[1].get('status') == 'open')
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

def issuediff(revx, revy):
    """Perform a simple one-level deep diff of a dictionary"""
    revxkeys = sorted(revx.keys())
    revykeys = sorted(revy.keys())
    x = 0
    y = 0
    added = []
    removed = []
    changed = []
    while x < len(revxkeys) or y < len(revykeys):
        if x == len(revxkeys):
            # Exhausted source keys, the rest are added properties
            added.append({revykeys[y]: revy[revykeys[y]]})
        elif y == len(revykeys):
            # Exhausted dest keys, the rest are removed properties
            removed.append({revxkeys[x]: revx[revxkeys[x]]})
        elif revxkeys[x] < revykeys[y]:
            # This particular key exists in the source, and not the dest
            removed.append({revxkeys[x]: revx[revxkeys[x]]})
            x += 1
        elif revxkeys[x] > revykeys[y]:
            # This particular key exists in the dest, and not the source
            added.append({revykeys[y]: revy[revykeys[y]]})
            y += 1
        else:
            # Both versions have this key, we'll look for changes.
            if revx[revxkeys[x]] != revy[revykeys[y]]:
                changed.append({revykeys[x]: [revx[revxkeys[x]], revy[revykeys[y]]]})
            x += 1
            y += 1
    if not added and not removed and not changed:
        return False
    return added, removed, changed

            
def issue(repositories=[], dbfolder='issues', id=None, status=['open']):
    # Use revision to walk backwards intelligently.
    # Change this to only accept one repository and to return a history
    issue = None
    for repo in repositories:
        try:
            with open(path.join(repo, dbfolder, id)) as issuefile:
                issue = [{'data':yaml.load(issuefile.read())}]
            myui = ui.ui()
            repo = hg.repository(myui, repo)
            filectxt = repo['tip'][path.join(dbfolder, id)]
            filerevid = filectxt.filerev()
            oldrev = issue[0]['data']
            while True:
                newrev = yaml.load(filectxt.data())
                issue.append({'data': newrev,
                              'user': filectxt.user(),
                              'date': util.datestr(filectxt.date()),
                              'files': filectxt.files(),
                              'diff': issuediff(oldrev, newrev),
                              'node': _hex_node(filectxt.node())})
                filerevid = filectxt.filerev() - 1
                if filerevid < 0:
                    break
                filectxt = filectxt.filectx(filerevid)
                oldrev = newrev
        except IOError:
            # Not all listed repositories have an issue tracking database, nor
            # do they contain this particular issue.  This needs to be changed
            # to specify the repo specifically
            pass

    return issue

def _hex_node(node_binary):
    """Convert a binary node string into a 40-digit hex string"""
    return ''.join('%x' % ord(letter) for letter in node_binary)

def add(repository, issue, dbfolder='issues', status=['open']):
    myui = ui.ui()
    repo = hg.repository(myui, repository)
    # This can fail in an empty repository.  Handle this
    commands.tag(myui, repo, NEW_TICKET_TAG, force=True, message='TICKETPREP: %s' % issue['title'])
    context = repo['tip']
    ticketid = _hex_node(context.node())
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
