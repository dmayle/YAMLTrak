# Copyright 2009 Douglas Mayle

# This file is part of YAMLTrak.

# YAMLTrak is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.

# YAMLTrak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public License
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
import exceptions
NEW_ISSUE_TAG='YAMLTrak-new-issue'
SKELETON = {
    'title': 'A title for the issue',
    'description': 'A detailed description of this issue.',
    'estimate': 'A time estimate for completion',
    'status': 'open, closed',
    'group': 'unfiled',
    'priority': 'high, normal, low',
    'comment': 'The current comment on this issue.'}
SKELETON_ADD = {
    'title': 'A title for the issue',
    'description': 'A detailed description of this issue.',
    'estimate': 'A time estimate for completion'}
INDEX = {'skeleton': {
    'title': 'A title for the issue',
    'description': 'A detailed description of this issue.',
    'estimate': 'A time estimate for completion',
    'status': 'open, closed',
    'group': 'unfiled',
    'priority': 'high, normal, low'}}

def issues(repositories=[], dbfolder='issues', status='open'):
    """Return the list of issues with the given statuses in dictionary form"""
    issues = {}
    for repository in repositories:
        try:
            issuedb = IssueDB(repository, dbfolder=dbfolder)
        except NoRepository:
            # No repo found
            return None
        except NoIssueDB:
            # No issue database
            return None

        issues[path.basename(issuedb.root)] = issuedb.issues(status)

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
    try:
        issuedb = IssueDB(repository, dbfolder=dbfolder)
    except NoRepository:
        # No repo found
        return None
    except NoIssueDB:
        # No issue database
        return None

    return issuedb.edit(issue=issue, id=id)

def issue(repository=None, dbfolder='issues', id=None, detail=True):
    try:
        issuedb = IssueDB(repository, dbfolder=dbfolder)
    except NoRepository:
        # No repo found
        return None
    except NoIssueDB:
        # No issue database
        return None

    return issuedb.issue(id, detail=detail)


def relatedissues(repository=None, dbfolder='issues', filename=None, ids=None):
    try:
        issuedb = IssueDB(repository, dbfolder=dbfolder)
    except NoRepository:
        # No repo found
        return []
    except NoIssueDB:
        # No issue database
        return []

    return issuedb.related([filename], ids=ids)

def _hex_node(node_binary):
    """Convert a binary node string into a 40-digit hex string"""
    return ''.join('%0.2x' % ord(letter) for letter in node_binary)

def add(repository, issue, dbfolder='issues', status=['open']):
    """Add an issue to the database"""
    try:
        issuedb = IssueDB(repository, dbfolder=dbfolder)
    except NoRepository:
        # No repo found
        return None
    except NoIssueDB:
        # No issue database
        return None

    return issuedb.add(issue=issue, status=status)

def init(repository, dbfolder='issues'):
    try:
        issuedb = IssueDB(repository, dbfolder=dbfolder, init=True)
    except NoRepository:
        # No repo found
        return None
    except NoIssueDB:
        # No issue database
        return None

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

def purge(repository, issueid, dbfolder='issues', status=['open']):
    # This just deletes the issue, we should keep them around temporarily and call it fixed.
    return True
    myui = ui.ui()
    repo = hg.repository(myui, repository)
    hgcommands.remove(myui, repo, path.join(repository, dbfolder, issueid))
    try:
        with open(path.join(repository, dbfolder, 'issues.yaml'), 'r') as indexfile:
            issues = yaml.load(indexfile.read())
        with open(path.join(repository, dbfolder, 'issues.yaml'), 'w') as indexfile:
            del issues[issueid]
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
                # We have to protect from invalid issue data in the repository
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

class NoRepository(Exception):
    """Exception raised when the folder given isn't inside a DVCS."""
    def __init__(self, repository):
        self.repository = repository
    def __str__(self):
        return 'No repository found at: %s' % self.repository

class NoIssueDB(Exception):
    """\
    Exception raised when the repository given doesn't contain an issue
    database.
    """
    def __init__(self, repository):
        self.repository = repository
    def __str__(self):
        return 'No issue database found in: %s' % self.repository


class IssueDB(object):
    """\
    An object that represents an issue database.  This provides a simpler means
    of accessing the YAMLTrak API than constantly passing in all of the
    parameters. In addition, it caches some of the work performed so that
    multiple operations run faster.
    """
    def __init__(self, folder, dbfolder='issues', indexfile='issues.yaml', init=False):
        self.dbfolder = dbfolder
        self.__indexfile = indexfile
        self.__skeletonfile = 'skeleton'
        self.__skeleton_addfile = 'skeleton_add'

        # If we ever do a lookup on the skeleton, we'll cache it for speed.
        self._skeleton = None
        self._skeleton_add = None
        self.ui = ui.ui()

        self.repo = self.__find_repo(folder)
        self.root = self.repo.root

        # We've got a valid repository, let's look for an issue database.
        if not path.exists(self._indexfile) or not path.exists(self._skeletonfile):
            if init and self._init():
                return
            raise NoIssueDB(self.root)
        # Look for the old name
        if not path.exists(self._skeleton_addfile):
            self.__skeleton_addfile = 'newticket'
        if not path.exists(self._skeleton_addfile):
            if init and self._init():
                return
            raise NoIssueDB(self.root)

    def __find_repo(self, folder):
        checkrepo = folder
        while checkrepo:
            if path.exists(path.join(checkrepo, '.hg')):
                try:
                    return hg.repository(self.ui, checkrepo)
                except (RepoError, util.Abort):
                    raise NoRepository(folder)
            root, tail = path.split(folder)
            if root == checkrepo:
                raise NoRepository(folder)
            checkrepo = root

    def _init(self):
        """\
        Internal method for initializing the database.  It's not much use on
        the outside, since you can't get an IssueDB object with an
        uninitialized DB.
        """
        try:
            makedirs(path.join(self.root, self.dbfolder))
        except OSError:
            pass
        with open(self._skeletonfile, 'w') as skeletonfile:
            skeletonfile.write(yaml.dump(SKELETON, default_flow_style=False))
        with open(self._skeleton_addfile, 'w') as skeletonfile:
            skeletonfile.write(yaml.dump(SKELETON_ADD, default_flow_style=False))
        with open(self._indexfile, 'w') as skeletonfile:
            skeletonfile.write(yaml.dump(INDEX, default_flow_style=False))
        hgcommands.add(self.ui, self.repo, self._skeletonfile)
        hgcommands.add(self.ui, self.repo, self._skeleton_addfile)
        hgcommands.add(self.ui, self.repo, self.indexfile)
        return true

    @property
    def _indexfile(self):
        """Helper that returns the full path of the issues index file."""
        return path.join(self.root, self.dbfolder, self.__indexfile)

    @property
    def _skeletonfile(self):
        """Helper that returns the full path of the issues skeleton file."""
        return path.join(self.root, self.dbfolder, self.__skeletonfile)

    @property
    def _skeleton_addfile(self):
        """Helper that returns the full path of the issues add skeleton file."""
        return path.join(self.root, self.dbfolder, self.__skeleton_addfile)

    def related(self, filenames, ids=[]):
        # Use revision to walk backwards intelligently.
        # Change this to only accept one repository and to return a history
        issues = []

        # Lookup into the status lists returned by repo.status()
        # ['modified', 'added', 'removed', 'deleted', 'unknown', 'ignored', 'clean']
        statuses = self.repo.status()
        modified, added = statuses[:2]

        for id in ids:
            if path.join(self.dbfolder, id) in added or path.join(self.dbfolder, id) in modified:
                # We consider all uncommitted issues to be related, since they
                # would become related on commit.
                issues.append(id)
                continue

            try:
                filectxt = self.repo['tip'][path.join(self.dbfolder, id)]
            except LookupError:
                # This issue hasn't been committed yet
                continue
            filerevid = filectxt.filerev()

            # By default, we're working with the context of tip.  Update to the
            # context from the latest revision.
            filectxt = filectxt.filectx(filerevid)

            try:
                while True:
                    for filename in filenames:
                        if filename in filectxt.files():
                            issues.append(id)
                            raise StopIteration

                    filerevid = filectxt.filerev() - 1
                    if filerevid < 0:
                        break
                    filectxt = filectxt.filectx(filerevid)
            except StopIteration:
                pass

        return issues

    def issues(self, status='open'):
        """\
        Return a list of issues in the database with the given status.
        """
        issuedb = {}
        try:
            with open(self._indexfile) as indexfile:
                issuedb = dict(issue for issue in yaml.load(indexfile.read()).iteritems() if issue[0] != 'skeleton' and status in issue[1].get('status', '').lower())
        except IOError:
            # Not all listed repositories have an issue tracking database
            return issuedb
        for issue in issuedb.itervalues():
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
        return issuedb

    def issue(self, id, detail=True):
        """\
        Return detailed information about the issue requested.  If detail is
        set to True, then return a issue history as well, including changesets,
        associating files, the committing user, changeset node, and date.
        """

        # Use revision to walk backwards intelligently.
        # Change this to only accept one repository and to return a history
        issue = None
        try:
            with open(path.join(self.root, self.dbfolder, id)) as issuefile:
                issue = [{'data':yaml.safe_load(issuefile.read())}]

            if not detail:
                return issue

            try:
                filectxt = self.repo['tip'][path.join(self.dbfolder, id)]
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
                    # We have to protect from invalid issue data in the repository
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

    @property
    def skeleton(self):
        """\
        Return the issue database skeleton, with a list of fields and default
        values.
        """
        if self._skeleton:
            return self._skeleton
        self._skeleton = self.issue(self.__skeletonfile, detail=False)
        if self._skeleton:
            self._skeleton = self._skeleton[0]['data']
        return self._skeleton

    @property
    def skeleton_add(self):
        """\
        Return the issue database add skeleton, with a list of fields and
        default values.
        """
        if self._skeleton_add:
            return self._skeleton_add
        self._skeleton_add = self.issue(self.__skeleton_addfile, detail=False)
        if self._skeleton_add:
            self._skeleton_add = self._skeleton_add[0]['data']
        return self._skeleton_add

    def add(self, issue, status='open'):
        """\
        Add an issue to the issue database.  Returns an issueid if successful.
        All fields are filtered by those in the add issue skeleton.
        """
        addissue = {}
        for field, default in self.skeleton_add.iteritems():
            addissue[field] = issue.get(field, default)

        if 'status' not in addissue:
            addissue['status'] = status
        if 'comment' not in addissue:
            addissue['comment'] = 'Opening issue'

        # This can fail in an empty repository.  Handle this
        hgcommands.tag(self.ui, self.repo, NEW_ISSUE_TAG, force=True, message='ISSUEPREP: %s' % addissue.get('title', 'No issue title'))
        context = self.repo['tip']
        issueid = _hex_node(context.node())
        try:
            with open(path.join(self.root, self.dbfolder, issueid), 'w') as issuefile:
                issuefile.write(yaml.safe_dump(addissue, default_flow_style=False))
            hgcommands.add(self.ui, self.repo, path.join(self.root, self.dbfolder, issueid))
        except IOError:
            return false

        # Poor man's code reuse.  Since I haven't yet factored out the index
        # updating, I'll just call edit without any values.
        return self.edit(id=issueid, issue={}) and issueid

    def edit(self, id=None, issue=None):
        """\
        Save the issue with the given id.  The issue must already exist in the
        database.  Because we already filter using the skeleton, you can don't
        have to worry that any unwanted fields will show up.
        """
        if issue is None or not id:
            return

        # We use the skeleton to filter any edits. We also leave any values
        # from the original issue intact.
        oldissue = self.issue(id=id, detail=False)[0]['data']
        saveissue = {}
        for field, default in self.skeleton.iteritems():
            saveissue[field] = issue.get(field, oldissue.get(field, default))
            if saveissue[field] is None:
                # I don't like null values in the database.
                saveissue[field] = ''

        try:
            with open(path.join(self.root, self.dbfolder, id), 'w') as issuefile:
                issuefile.write(yaml.safe_dump(saveissue, default_flow_style=False))
        except IOError:
            return false

        try:
            # This is done pretty often, as well.  Abstract this out.
            with open(self._indexfile, 'r') as indexfile:
                index = yaml.load(indexfile.read())

            # We only write out the properties listed in the skeleton to the index.
            indexissue = {}
            for field in index['skeleton']:
                if field in saveissue:
                    indexissue[field] = saveissue[field]
            index[id] = indexissue

            with open(path.join(self.root, self.dbfolder, 'issues.yaml'), 'w') as indexfile:
                indexfile.write(yaml.safe_dump(index, default_flow_style=False))
        except IOError:
            return false
        return True
