# Copyright 2009 Douglas Mayle

# This file is part of YAMLTrak.

# YAMLTrak is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# YAMLTrak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with YAMLTrak.  If not, see <http://www.gnu.org/licenses/>.

# Remember when editing issues to always perform work on the issue file first,
# and then the index.  This way the issue file is the canonical storage medium,
# and the index is just that.  All code will make sure to use the same version
# stored in the issue file when updating the index.
from __future__ import with_statement
import yaml
from mercurial import hg, commands as hgcommands, ui, util
from mercurial.error import RepoError
from os import path, makedirs
from time import time
NEW_TICKET_TAG='YAMLTrak-new-ticket'

def issues(repositories=[], dbfolder='issues', status='open'):
    """Return the list of issues with the given statuses in dictionary form"""
    issues = {}
    for repo in repositories:
        try:
            with open(path.join(repo, dbfolder, 'issues.yaml')) as indexfile:
                issues[path.basename(repo)] = dict(issue for issue in yaml.load(indexfile.read()).iteritems() if issue[0] != 'skeleton' and status in issue[1].get('status', '').lower())
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
            try:
                priority = issue['priority'].lower()
                if 'high' in priority:
                    priority = 'high'
                elif 'normal' in priority:
                    priority = 'normal'
                elif 'low' in priority:
                    priority = 'low'
                else:
                    # Don't want any slipping through the cracks.
                    priority = 'high'

            except KeyError:
                priority = 'high'
            except IndexError:
                priority = 'high'
            except AttributeError:
                priority = 'high'

            issue['estimate'] = {'scale':scale, 'text':issue.get('estimate') is None and '' or issue['estimate']}
            issue['priority'] = priority
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
    try:
        issuedb = IssueDB(repository, dbfolder=dbfolder)
    except LookupException:
        # No repo found
        return None
    except Exception:
        # No issue database
        return None

    return issuedb.issue(id, detail=detail)


def relatedissues(repository=None, dbfolder='issues', filename=None, ids=None):
    # Use revision to walk backwards intelligently.
    # Change this to only accept one repository and to return a history
    issues = []
    myui = ui.ui()
    repo = hg.repository(myui, repository)

    # Lookup into the status lists returned by repo.status()
    # ['modified', 'added', 'removed', 'deleted', 'unknown', 'ignored', 'clean']
    statuses = repo.status()
    modified, added = statuses[:2]

    for id in ids:
        if path.join(dbfolder, id) in added or path.join(dbfolder, id) in modified:
            # We consider all uncommitted issues to be related, since they
            # would become related on commit.
            issues.append(id)
            continue

        try:
            filectxt = repo['tip'][path.join(dbfolder, id)]
        except LookupError:
            # This issue hasn't been committed yet
            continue
        filerevid = filectxt.filerev()

        # By default, we're working with the context of tip.  Update to the
        # context from the latest revision.
        filectxt = filectxt.filectx(filerevid)

        while True:
            if filename in filectxt.files():
                issues.append(id)
                break

            filerevid = filectxt.filerev() - 1
            if filerevid < 0:
                break
            filectxt = filectxt.filectx(filerevid)

    return issues

def _hex_node(node_binary):
    """Convert a binary node string into a 40-digit hex string"""
    return ''.join('%0.2x' % ord(letter) for letter in node_binary)

def add(repository, issue, dbfolder='issues', status=['open']):
    """Add an issue to the database"""
    if 'status' not in issue:
        issue['status'] = 'open'
    if 'comment' not in issue:
        issue['comment'] = 'Opening ticket'
    myui = ui.ui()
    repo = hg.repository(myui, repository)
    # This can fail in an empty repository.  Handle this
    hgcommands.tag(myui, repo, NEW_TICKET_TAG, force=True, message='TICKETPREP: %s' % issue['title'])
    context = repo['tip']
    ticketid = _hex_node(context.node())
    try:
        with open(path.join(repository, dbfolder, ticketid), 'w') as issuefile:
            issuefile.write(yaml.safe_dump(issue, default_flow_style=False))
        hgcommands.add(myui, repo, path.join(repository, dbfolder, ticketid))
    except IOError:
        return false
    try:
        with open(path.join(repository, dbfolder, 'issues.yaml'), 'r') as indexfile:
            issues = yaml.load(indexfile.read())
        with open(path.join(repository, dbfolder, 'issues.yaml'), 'w') as indexfile:
            issues[ticketid] = issue
            indexfile.write(yaml.safe_dump(issues, default_flow_style=False))
        return ticketid
    except IOError:
        return false

def init(repository, dbfolder='issues'):
    try:
        makedirs(path.join(repository, dbfolder))
    except OSError:
        pass
    SKELETON = {
        'title': 'A title for the ticket',
        'description': 'A detailed description of this ticket.',
        'estimate': 'A time estimate for completion',
        'status': 'open, closed',
        'group': 'unfiled',
        'priority': 'high, normal, low',
        'comment': 'The current comment on this ticket.'}
    NEWTICKET = {
        'title': 'A title for the ticket',
        'description': 'A detailed description of this ticket.',
        'estimate': 'A time estimate for completion'}
    INDEX = {'skeleton': {
        'title': 'A title for the ticket',
        'description': 'A detailed description of this ticket.',
        'estimate': 'A time estimate for completion',
        'status': 'open, closed',
        'group': 'unfiled',
        'priority': 'high, normal, low'}}
    with open(path.join(repository, dbfolder, 'skeleton'), 'w') as skeletonfile:
        skeletonfile.write(yaml.dump(SKELETON, default_flow_style=False))
    with open(path.join(repository, dbfolder, 'newticket'), 'w') as skeletonfile:
        skeletonfile.write(yaml.dump(NEWTICKET, default_flow_style=False))
    with open(path.join(repository, dbfolder, 'issues.yaml'), 'w') as skeletonfile:
        skeletonfile.write(yaml.dump(INDEX, default_flow_style=False))
    myui = ui.ui()
    repo = hg.repository(myui, repository)
    hgcommands.add(myui, repo, path.join(repository, dbfolder, 'skeleton'))
    hgcommands.add(myui, repo, path.join(repository, dbfolder, 'newticket'))
    hgcommands.add(myui, repo, path.join(repository, dbfolder, 'issues.yaml'))

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
    hgcommands.remove(myui, repo, path.join(repository, dbfolder, ticketid))
    try:
        with open(path.join(repository, dbfolder, 'issues.yaml'), 'r') as indexfile:
            issues = yaml.load(indexfile.read())
        with open(path.join(repository, dbfolder, 'issues.yaml'), 'w') as indexfile:
            del issues[ticketid]
            indexfile.write(yaml.safe_dump(issues, default_flow_style=False))
    except IOError:
        return false

def _group_estimate(issues, groupname):
    hours = 0
    minutes = 0
    for issueid, issue in issues.iteritems():
        if issue.get('group', 'unfiled') != groupname:
            continue
        if 'open' not in issue.get('status','').lower():
            continue
        estimate = issue.get('estimate', '')
        try:
            timeamount, timescale = estimate.split()[:2]
            timescale = timescale.lower().rstrip('s')
            if timescale == 'minute':
                minutes += int(timeamount)
            elif timescale == 'hour':
                hours += int(timeamount)
            elif timescale == 'day':
                hours += 24 * int(timeamount)
            elif timescale == 'week':
                hours += 7 * 24 * int(timeamount)
            else:
                # We don't currently handle amounts larger than weeks.
                continue
        except ValueError:
            continue
        except IndexError:
            continue
        except AttributeError:
            continue
    return hours + (minutes // 60)

def burndown(repository, groupname, dbfolder='issues'):
    checkpoints = []
    found = False
    try:
        with open(path.join(repository, dbfolder, 'issues.yaml')) as indexfile:
            issues = yaml.load(indexfile.read())
        estimate = _group_estimate(issues, groupname)
        if estimate > 0:
            found = True
        checkpoints.append([time()*1000, estimate])
        myui = ui.ui()
        repo = hg.repository(myui, repository)
        try:
            filectxt = repo['tip'][path.join(dbfolder, 'issues.yaml')]
        except LookupError:
            # The index hasn't been committed yet
            return checkpoints
        filerevid = filectxt.filerev()

        # By default, we're working with the context of tip.  Update to the
        # context from the latest revision.
        filectxt = filectxt.filectx(filerevid)

        while True:
            try:
                issues = yaml.safe_load(filectxt.data())
            except yaml.loader.ScannerError:
                # We have to protect from invalid ticket data in the repository
                filerevid = filectxt.filerev() - 1
                if filerevid < 0:
                    break
                filectxt = filectxt.filectx(filerevid)
                continue

            estimate = _group_estimate(issues, groupname)
            if estimate > 0:
                found = True
            elif found:
                # We had good data, and now it's disappeared, we have no need
                # to keep going back.
                return checkpoints
            checkpoints.append([filectxt.date()[0]*1000, estimate])

            filerevid = filectxt.filerev() - 1
            if filerevid < 0:
                break
            filectxt = filectxt.filectx(filerevid)
    except IOError:
        # Not all listed repositories have an issue tracking database, nor
        # do they contain this particular issue.  This needs to be changed
        # to specify the repo specifically
        return []

    return checkpoints

class IssuesDB(object):
    """\
    An object that represents an issue database.  This provides a simpler means
    of accessing the YAMLTrak API than constantly passing in all of the
    parameters. In addition, it caches some of the work performed so that
    multiple operations run faster.
    """
    def __init__(self, folder, dbfolder='issues'):
        self.dbfolder = dbfolder

        # If we ever do a lookup on the skeleton, we'll cache it for speed.
        self.skeleton = None
        self.newticket = None
        self.ui = ui.ui()
        try:
            self.repo = hg.repository(self.ui, folder)
        except (RepoError, util.Abort):
            # I'm feeling lazy, so I think I'm gonna do this recursively with a
            # maxdepth. For each subdirectory of the current, check to see if it's
            # a repo.
            raise LookupException
        self.root = self.repo.root

    def root(self):
        return self.root

    def issue(self, id, detail=True):
        """\
        Return detailed information about the issue requested.  If detail is
        set to True, then return a ticket history as well, including
        changesets, associating files, the committing user, changeset node, and
        date.
        """

        # I suspect that we may have need of an issue skeleton many times while
        # using this object, so I'll cache it if it's retreived.  The same is
        # true of the newticket filter.
        if 'skeleton' == id and self.skeleton and not detail:
            return skeleton

        if 'newticket' == id and self.newticket and not detail:
            return newticket

        # Use revision to walk backwards intelligently.
        # Change this to only accept one repository and to return a history
        issue = None
        try:
            with open(path.join(self.root, self.dbfolder, id)) as issuefile:
                issue = [{'data':yaml.safe_load(issuefile.read())}]

            # Cache the magic tickets
            if 'skeleton' == id:
                self.skeleton = issue
            elif 'newticket' == id:
                self.newticket = issue

            if not detail:
                return issue

            try:
                filectxt = self.repo['tip'][path.join(dbfolder, id)]
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
                    continue

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
