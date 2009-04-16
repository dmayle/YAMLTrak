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
import textwrap
from termcolor import colored
from mercurial import hg, ui
import os
from argparse import ArgumentParser
from yamltrak import IssueDB, edit_issue

def guess_ticket_id(repository):
    try:
        issues = issues([repository])[os.path.basename(repository)]
    except KeyError:
        # There is no issue database, or maybe just no open issues...
        print 'No open issues found'
        import sys
        sys.exit(1)

    # Use repo.status to get this list
    myui = ui.ui()
    repo = hg.repository(myui, repository)
    modified, added = repo.status()[:2]
    files = modified + added
    found = {}
    for filename in files:
        relatedissues = relatedissues(repository, filename=filename, ids=issues.keys())
        for issueid in relatedissues:
            found[issueid] = issues[issueid].get('title', '')

    if len(found.keys()) > 1:
        color = None
        print colored('Too many linked issues found, please specify one.', color, attrs=['reverse'])
        for issueid in found:
            print colored(textwrap.fill('Issue: %s' % issueid,
                initial_indent='    ', subsequent_indent='    '), color, attrs=[])
            print colored(textwrap.fill(found[issueid].upper(),
                initial_indent='    ', subsequent_indent='    '), color, attrs=[])

        import sys
        sys.exit(1)
    return found.keys()[0]

def unpack_add(issuedb, repository, args):
    skeleton = issuedb.skeleton[0]['data']
    issue = {}
    for field in skeleton:
        issue[field] = getattr(args, field, None) or skeleton[field]
    newid = add(repository, issue=issue)
    print 'Added ticket: %s' % newid

def unpack_list(issuedb, repository, args):
    issues = issuedb.issues(status=args.status)
    for id, issue in issues.iteritems():
        # Try to use color for clearer output
        color = None
        if 'high' in issue.get('priority',''):
            color = 'red'
        elif 'normal' in issue.get('priority',''):
            pass
        elif 'low' in issue.get('priority',''):
            color = 'blue'
        else:
            color = 'red'

        # We'll use status indicators on indent for estimate
        if 'long' in issue.get('estimate', {}).get('scale').lower():
            indent = '>>>>'
        elif 'medium' in issue.get('estimate', {}).get('scale').lower():
            indent = '> > '
        elif 'short' in issue.get('estimate', {}).get('scale').lower():
            indent = '>   '
        else:
            indent = '===='

        print colored('Issue: %s' % id, color, attrs=['reverse'])
        print colored(textwrap.fill(issue.get('title', '').upper(),
            initial_indent=indent, subsequent_indent=indent), color, attrs=[])
        # print colored(textwrap.fill(issue.get('description',''),
        #     initial_indent=indent, subsequent_indent=indent), color)
        print colored(textwrap.fill(issue.get('estimate',{}).get('text',''),
            initial_indent=indent, subsequent_indent=indent), color)

def unpack_edit(issuedb, repository, args):
    if not args.id:
        args.id = guess_ticket_id(repository)
    skeleton = issuedb.skeleton[0]['data']
    issue = issuedb.issue(id=args.id, detail=False)[0]['data']
    newissue = {}
    for field in skeleton:
        newissue[field] = getattr(args, field, None) or issue.get(field, skeleton[field])
    edit_issue(repository, id=args.id, issue=newissue)

def unpack_show(issuedb, repository, args):
    if not args.id:
        args.id = guess_ticket_id(repository)

    issuedata = issuedb.issue(id=args.id, detail=args.detail)
    if not issuedata or not issuedata[0].get('data'):
        print 'No such ticket found'
        return
    issue = issuedata[0]['data']
    print '\nIssue: %s' % args.id
    if 'title' in issue:
        print textwrap.fill(issue.get('title', '').upper(), initial_indent='', subsequent_indent='')
    if 'description' in issue:
        print textwrap.fill(issue['description'], initial_indent='', subsequent_indent='')
    print ''

    for field in sorted(issue.keys()):
        if field in ['title', 'description']:
            continue
        print textwrap.fill('%s: %s' % (field.upper(), issue[field]), initial_indent='', subsequent_indent='  ')

    if issue.get('diff'):
        for changeset in issue['diff'][0].iteritems():
            print 'Added: %s - %s' % (changeset[0].upper(), changeset[1])
        for changeset in issue['diff'][1].iteritems():
            print 'Removed: %s' % changeset[0].upper()
        for changeset in issue['diff'][2].iteritems():
            print 'Changed: %s - %s' % (changeset[0].upper(), changeset[1][1])
    else:
        # No uncommitted changes
        pass

    for version in issuedata[1:]:
        print '\nChangeset: %s' % version['node']
        print 'Committed by: %s on %s' % (version['user'], version['date'])
        print 'Linked files:'
        for filename in version['files']:
            print '    %s' % filename
        if version.get('diff'):
            for changeset in version['diff'][0].iteritems():
                print 'Added: %s - %s' % (changeset[0].upper(), changeset[1])
            for changeset in version['diff'][1].iteritems():
                print 'Removed: %s' % changeset[0].upper()
            for changeset in version['diff'][2].iteritems():
                print 'Changed: %s - %s' % (changeset[0].upper(), changeset[1][1])


def unpack_related(issuedb, repository, args):
    try:
        issues = issues([repository])[os.path.basename(repository)]
    except KeyError:
        # There is no issue database, or maybe just no open issues...
        print 'No open issues found'
        return
    if not args.files:
        # Use repo.status to get this list
        myui = ui.ui()
        repo = hg.repository(myui, repository)
        modified, added = repo.status()[:2]
        args.files = modified + added
    for filename in args.files:
        relatedissues = relatedissues(repository, filename=filename, ids=issues.keys())
        color = None
        print colored('File: %s' % filename, color, attrs=['reverse'])
        for issueid in relatedissues:
            print colored(textwrap.fill('Issue: %s' % issueid,
                initial_indent='    ', subsequent_indent='    '), color, attrs=[])
            print colored(textwrap.fill(issues[issueid].get('title', '').upper(),
                initial_indent='    ', subsequent_indent='    '), color, attrs=[])

def unpack_init(issuedb, repository, args):
    init(repository)
    print 'Initialized repository'

def unpack_close(issuedb, repository, args):
    if not args.id:
        args.id = guess_ticket_id(repository)
    skeleton = issuedb.skeleton[0]['data']
    issue = issuedb.issue(id=args.id, detail=False)[0]['data']
    newissue = {}
    for field in skeleton:
        newissue[field] = issue.get(field, skeleton[field])
    newissue['status'] = 'closed'
    edit_issue(repository, id=args.id, issue=newissue)
    pass

def unpack_purge(issuedb, repository, args):
    pass

def unpack_burndown(issuedb, repository, args):
    pass

def main():
    """Parse the command line options and react to them."""
    # We need to attempt to initialize a repo, and if it works, use the repo
    # root instead of 'here'
    here = os.getcwd()
    try:
        issuedb = IssueDB(os.getcwd())
    except LookupError:
        # This means that there was no repository here.
        print 'Unable to find a repository.'
        import sys
        sys.exit(1)
    except NameError:
        # This means no issue database was found.  We give the option to
        # initialize one.
        parser = ArgumentParser(prog='yt', description='YAMLTrak is a distributed version controlled issue tracker.')
        subparsers = parser.add_subparsers(help=None, dest='command')
        parser_init = subparsers.add_parser('init', help="Initialize issue "
                                            "database.")
        parser_init.set_defaults(func=unpack_init)
        args = parser.parse_args()
        args.func(issuedb, issuedb.root, args)
        return

    skeleton = issuedb.skeleton
    addskeleton = issuedb.addskeleton

    skeleton = skeleton[0]['data']
    if addskeleton:
        addskeleton = addskeleton[0]['data']
    else:
        addskeleton = {}

    parser = ArgumentParser(prog='yt', description='YAMLTrak is a distributed version controlled issue tracker.')
    # parser.add_argument('-r', '--repository',
    #     help='Use this directory as the repository instead of the current '
    #     'one.')
    # parser.add_argument('-f', '--folder',
    #     help='Look for issues in this folder, instead of the "issues" folder.')

    subparsers = parser.add_subparsers(help=None, dest='command')

    # Adding an issue
    parser_add = subparsers.add_parser('add', help="Add an issue.")
    parser_add.set_defaults(func=unpack_add)
    for field, help in skeleton.iteritems():
        if field not in addskeleton:
            parser_add.add_argument('-' + field[0], '--' + field, help=help)
    for field, help in addskeleton.iteritems():
        parser_add.add_argument('-' + field[0], '--' + field, required=True, help=skeleton[field])
    #parser_add.add_argument(

    # Editing an issue
    parser_edit = subparsers.add_parser('edit', help="Edit an issue.")
    parser_edit.set_defaults(func=unpack_edit)
    for field, help in skeleton.iteritems():
        parser_edit.add_argument('-' + field[0], '--' + field, help=help)
    parser_edit.add_argument('id', nargs='?', help='The issue id to edit.')

    # List all issues
    parser_list = subparsers.add_parser('list', help="List all issues.")
    parser_list.set_defaults(func=unpack_list)
    parser_list.add_argument('-s', '--status', default='open',
        help='List all issues with this stats.  Defaults to open issues.')

    # Show an issue
    parser_show = subparsers.add_parser('show', help="Show the details for an "
                                        "issue.")
    parser_show.set_defaults(func=unpack_show)
    parser_show.add_argument('-d', '--detail', default=False, action='store_true',
        help='Show a detailed view of the ticket')
    parser_show.add_argument('id', nargs='?',
        help='The issue id to show the details for.')

    # Get issues related to a file
    parser_related = subparsers.add_parser('related', help="List the issues "
                                           "related to given files.")
    parser_related.set_defaults(func=unpack_related)
    parser_related.add_argument( 'files', metavar='file', type=str, nargs='*',
        default=[],
        help='List the open issues related to these files.  If no files are '
        'supplied, and the list of currently uncommitted files (excluding '
        'tickets) will be checked.')

    # Initialize DV
    parser_init = subparsers.add_parser('init', help="Initialize issue "
                                        "database.")
    parser_init.set_defaults(func=unpack_init)

    # Close an issue
    parser_close = subparsers.add_parser('close', help="Close an issue.")
    parser_close.set_defaults(func=unpack_close)
    parser_close.add_argument('id', nargs='?',
        help='The issue id to close.')

    # Purge an issue
    # parser_purge = subparsers.add_parser('purge', help="Purge an issue.")
    # parser_purge.set_defaults(func=unpack_purge)

    # ASCII Burndown chart.
    # parser_burn = subparsers.add_parser('burn', help="Show a burndown chart "
    #                                     "for a group of issues.")
    # parser_burn.set_defaults(func=unpack_burndown)
    args = parser.parse_args()
    args.func(issuedb, issuedb.root, args)


if __name__ == '__main__':
    main()
