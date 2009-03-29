# Remember when editing issues to always perform work on the issue file first,
# and then the index.  This way the issue file is the canonical storage medium,
# and the index is just that.  All code will make sure to use the same version
# stored in the issue file when updating the index.
from __future__ import with_statement
import yaml
from mercurial import hg, commands, ui, util
from os import path
NEW_TICKET_TAG='YAMLTrak-new-ticket'

def issues(repositories=[], dbfolder='issues', status=['open']):
    """Return the list of issues with the given statuses in dictionary form"""
    issues = {}
    for repo in repositories:
        try:
            with open(path.join(repo, dbfolder, 'issues.yaml')) as indexfile:
                issues[path.basename(repo)] = dict(issue for issue in yaml.load(indexfile.read()).iteritems() if issue[0] != 'skeleton' and issue[1].get('status', 'open') == 'open')
        except IOError:
            # Not all listed repositories have an issue tracking database
            pass
    for issuedb in issues:
        for issue in issues[issuedb].itervalues():
            # A proper version of this would figure out the actual time value.
            # We'll take a shortcut and look at the word.
            try:
                timescale = issue['estimate'].split()[1].rstrip('s')
                if timescale.lower() == 'hour' or timescale.lower() == 'minute':
                    scale = 'short'
                elif timescale.lower() == 'day':
                    scale = 'medium'
                else:
                    scale = 'long'
            except IndexError:
                scale = 'unplanned'
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
    added = {}
    removed = {}
    changed = {}
    while x < len(revxkeys) or y < len(revykeys):
        if x == len(revxkeys):
            # Exhausted source keys, the rest are added properties
            added[revykeys[y]] = revy[revykeys[y]]
        elif y == len(revykeys):
            # Exhausted dest keys, the rest are removed properties
            removed[revxkeys[x]] = revx[revxkeys[x]]
        elif revxkeys[x] < revykeys[y]:
            # This particular key exists in the source, and not the dest
            removed[revxkeys[x]] = revx[revxkeys[x]]
            x += 1
        elif revxkeys[x] > revykeys[y]:
            # This particular key exists in the dest, and not the source
            added[revykeys[y]] = revy[revykeys[y]]
            y += 1
        else:
            # Both versions have this key, we'll look for changes.
            if revx[revxkeys[x]] != revy[revykeys[y]]:
                changed[revxkeys[x]] = (revx[revxkeys[x]], revy[revykeys[y]])
            x += 1
            y += 1
    if not added and not removed and not changed:
        return False
    return added, removed, changed

            
def edit_issue(repository=None, dbfolder='issues', issue=None, id=None):
    """Modify the copy of the issue on disk, both in it's file, and the index."""
    if not issue or not id:
        return
    try:
        with open(path.join(repository, dbfolder, id), 'w') as issuefile:
            issuefile.write(yaml.safe_dump(issue, default_flow_style=False))
    except IOError:
        return false

    try:
        with open(path.join(repository, dbfolder, 'issues.yaml'), 'r') as indexfile:
            index = yaml.load(indexfile.read())

        # We only write out the properties listed in the skeleton to the index.
        indexissue = {}
        for key in index['skeleton']:
            if key in issue:
                indexissue[key] = issue[key]
        index[id] = indexissue

        with open(path.join(repository, dbfolder, 'issues.yaml'), 'w') as indexfile:
            indexfile.write(yaml.safe_dump(index, default_flow_style=False))
    except IOError:
        return false

def issue(repository=None, dbfolder='issues', id=None, detail=True):
    # Use revision to walk backwards intelligently.
    # Change this to only accept one repository and to return a history
    issue = None
    try:
        with open(path.join(repository, dbfolder, id)) as issuefile:
            issue = [{'data':yaml.safe_load(issuefile.read())}]
        if not detail:
            return issue
        myui = ui.ui()
        repo = hg.repository(myui, repository)
        try:
            filectxt = repo['tip'][path.join(dbfolder, id)]
        except LookupError:
            # This issue hasn't been committed yet
            return issue
        filerevid = filectxt.filerev()

        # By default, we're working with the context of tip.  Update to the
        # context from the latest revision.
        filectxt = filectxt.filectx(filerevid)
        oldrev = issue[0]['data']

        while True:
            try:
                newrev = yaml.safe_load(filectxt.data())
            except yaml.loader.ScannerError:
                # We have to protect from invalid ticket data in the repository
                filerevid = filectxt.filerev() - 1
                if filerevid < 0:
                    break
                filectxt = filectxt.filectx(filerevid)

            issue[-1]['diff'] = issuediff(newrev, oldrev)
            issue.append({'data': newrev,
                          'user': filectxt.user(),
                          'date': util.datestr(filectxt.date()),
                          'files': filectxt.files(),
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
        return

    return issue

def _hex_node(node_binary):
    """Convert a binary node string into a 40-digit hex string"""
    return ''.join('%0.2x' % ord(letter) for letter in node_binary)

def add(repository, issue, dbfolder='issues', status=['open']):
    if 'status' not in issue:
        issue['status'] = 'open'
    if 'comment' not in issue:
        issue['comment'] = 'Opening ticket'
    myui = ui.ui()
    repo = hg.repository(myui, repository)
    # This can fail in an empty repository.  Handle this
    commands.tag(myui, repo, NEW_TICKET_TAG, force=True, message='TICKETPREP: %s' % issue['title'])
    context = repo['tip']
    ticketid = _hex_node(context.node())
    try:
        with open(path.join(repository, dbfolder, ticketid), 'w') as issuefile:
            issuefile.write(yaml.safe_dump(issue, default_flow_style=False))
        commands.add(myui, repo, path.join(repository, dbfolder, ticketid))
    except IOError:
        return false
    try:
        with open(path.join(repository, dbfolder, 'issues.yaml'), 'r') as indexfile:
            issues = yaml.load(indexfile.read())
        with open(path.join(repository, dbfolder, 'issues.yaml'), 'w') as indexfile:
            issues[ticketid] = issue
            indexfile.write(yaml.safe_dump(issues, default_flow_style=False))
    except IOError:
        return false

def close(repository, id, dbfolder='issues'):
    """Sets the status of the issue on disk to close, both in it's file, and the index."""
    if not id:
        return false
    try:
        with open(path.join(repository, dbfolder, id)) as issuefile:
            issue = yaml.load(issuefile.read())
        issue['status'] = 'closed'
        with open(path.join(repository, dbfolder, id), 'w') as issuefile:
            issuefile.write(yaml.safe_dump(issue, default_flow_style=False))
    except IOError:
        return false

    # For the index pass, we always make sure to use the data in the full
    # issue. This helps to prevent problems of synchronization from the
    # non-normalized database.
    try:
        with open(path.join(repository, dbfolder, 'issues.yaml'), 'r') as indexfile:
            index = yaml.load(indexfile.read())

        # We only write out the properties listed in the skeleton to the index.
        indexissue = {}
        for key in index['skeleton']:
            if key in issue:
                indexissue[key] = issue[key]
        index[id] = indexissue

        with open(path.join(repository, dbfolder, 'issues.yaml'), 'w') as indexfile:
            indexfile.write(yaml.safe_dump(index, default_flow_style=False))
    except IOError:
        return false

def purge(repository, ticketid, dbfolder='issues', status=['open']):
    # This just deletes the ticket, we should keep them around temporarily and call it fixed.
    return True
    myui = ui.ui()
    repo = hg.repository(myui, repository)
    commands.remove(myui, repo, path.join(repository, dbfolder, ticketid))
    try:
        with open(path.join(repository, dbfolder, 'issues.yaml'), 'r') as indexfile:
            issues = yaml.load(indexfile.read())
        with open(path.join(repository, dbfolder, 'issues.yaml'), 'w') as indexfile:
            del issues[ticketid]
            indexfile.write(yaml.safe_dump(issues, default_flow_style=False))
    except IOError:
        return false
