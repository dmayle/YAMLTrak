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
import os
import textwrap
from termcolor import colored
from yamltrak.argparse import ArgumentParser
from yamltrak import IssueDB, NoRepository, NoIssueDB

def guess_issue_id(issuedb):
    related = issuedb.related(detail=True)

    if len(related) > 1:
        print colored('Too many linked issues found, please specify one.', None, attrs=['reverse'])
        for issueid in related:
            print colored(textwrap.fill('Issue: %s' % issueid,
                initial_indent='    ', subsequent_indent='    '), None, attrs=[])
            print colored(textwrap.fill(related[issueid].get('title', '').upper(),
                initial_indent='    ', subsequent_indent='    '), None, attrs=[])

        import sys
        sys.exit(1)

    issueid = related.keys()[0]
    # Prompt user?
    print "Found only one issue."
    print colored(textwrap.fill('Issue: %s' % issueid,
        initial_indent='    ', subsequent_indent='    '), None, attrs=[])
    print colored(textwrap.fill(related[issueid].get('title', '').upper(),
        initial_indent='    ', subsequent_indent='    '), None, attrs=[])
    verification = raw_input("Do you want to use this issue? (Y/[N]) ")
    if verification.lower() in ['y', 'yes', 'yeah', 'oui', 'uh-huh', 'sure', 'why not?', 'meh']:
        return issueid

    print 'Aborting'
    import sys
    sys.exit(1)

def unpack_new(issuedb, args):
    # We should be able to avoid this somehow by using an object dictionary.
    skeleton_new = issuedb.skeleton_new
    issue = {}
    for field in skeleton_new:
        issue[field] = getattr(args, field, None)
        if issue[field] is None:
            issue[field] = skeleton_new[field]

    newid = issuedb.new(issue=issue)
    print 'Added new issue: %s' % newid

def unpack_list(issuedb, args):
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

def unpack_edit(issuedb, args):
    if not args.id:
        args.id = guess_issue_id(issuedb)
    skeleton = issuedb.skeleton
    issue = issuedb.issue(id=args.id, detail=False)[0]['data']
    newissue = {}
    for field in skeleton:
        newissue[field] = getattr(args, field, None) or issue.get(field, skeleton[field])
    issuedb.edit(id=args.id, issue=newissue)

def unpack_show(issuedb, args):
    if not args.id:
        args.id = guess_issue_id(issuedb)

    issuedata = issuedb.issue(id=args.id, detail=args.detail)
    if not issuedata or not issuedata[0].get('data'):
        print 'No such issue found'
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


def unpack_related(issuedb, args):
    relatedissues = issuedb.related(filenames=args.files, detail=True)

    for issueid, issue in relatedissues.iteritems():
        print colored(textwrap.fill('Issue: %s' % issueid,
            initial_indent='    ', subsequent_indent='    '), None, attrs=[])
        print colored(textwrap.fill(issue.get('title', '').upper(),
            initial_indent='    ', subsequent_indent='    '), None, attrs=[])

def unpack_dbinit(issuedb, args):
    try:
        issuedb = IssueDB(args.repository, dbinit=True)
    except NoRepository:
        # This means that there was no repository here.
        print 'Unable to find a repository.'
        import sys
        sys.exit(1)
    except NoIssueDB:
        # Whoops
        print 'Error initializing issued database'
        import sys
        sys.exit(1)
    print 'Initialized issue database'

def unpack_close(issuedb, args):
    if not args.id:
        args.id = guess_issue_id(issuedb)
    issuedb.close(args.id, args.comment)

def unpack_purge(issuedb, args):
    pass

def unpack_burndown(issuedb, args):
    pass

def main():
    """Parse the command line options and react to them."""
    try:
        issuedb = IssueDB(os.getcwd())
    except NoRepository:
        # This means that there was no repository here.
        print 'Unable to find a repository.'
        import sys
        sys.exit(1)
    except NoIssueDB:
        # This means no issue database was found.  We give the option to
        # initialize one.
        parser = ArgumentParser(prog='yt', description='YAMLTrak is a distributed version controlled issue tracker.')
        subparsers = parser.add_subparsers(help=None, dest='command')
        parser_dbinit = subparsers.add_parser('dbinit',
            help="Initialize the issue database.")
        parser_dbinit.set_defaults(func=unpack_dbinit)
        args = parser.parse_args()
        # We don't have a valid database, so we call with none.
        args.repository = os.getcwd()
        args.func(None, args)
        return

    skeleton = issuedb.skeleton
    skeleton_new = issuedb.skeleton_new

    parser = ArgumentParser(prog='yt', description='YAMLTrak is a distributed version controlled issue tracker.')
    # parser.add_argument('-r', '--repository',
    #     help='Use this directory as the repository instead of the current '
    #     'one.')
    # parser.add_argument('-f', '--folder',
    #     help='Look for issues in this folder, instead of the "issues" folder.')

    subparsers = parser.add_subparsers(help=None, dest='command')

    # Adding a new issue
    parser_new = subparsers.add_parser('new', help="Add a new issue.")
    parser_new.set_defaults(func=unpack_new)
    for field, help in skeleton.iteritems():
        if field not in skeleton_new:
            parser_new.add_argument('-' + field[0], '--' + field, help=help)
    for field, help in skeleton_new.iteritems():
        parser_new.add_argument('-' + field[0], '--' + field, required=True, help=skeleton[field])

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
        help='Show a detailed view of the issue')
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
        'issues) will be checked.')

    # Initialize DB
    parser_dbinit = subparsers.add_parser('dbinit',
        help="Initialize the issue database.")
    parser_dbinit.set_defaults(func=unpack_dbinit)

    # Close an issue
    parser_close = subparsers.add_parser('close', help="Close an issue.")
    parser_close.add_argument('-c', '--comment', default=None,
        help='An optional closing comment to set on the ticket.')
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
    args.func(issuedb, args)


if __name__ == '__main__':
    main()
