#
from __future__ import with_statement
import yaml

def issues(repositories=[], status=['open']):
    """Return the list of issues with the given statuses in dictionary form"""
    issues = {}
    for repo in repositories:
        try:
            with open(repo) as issuesfile:
                issues.update(dict(issue for issue in yaml.load(issuesfile.read()).iteritems() if issue[0] != 'skeleton'))
        except IOError:
            # Not all listed repositories have an issue tracking database
            pass
    for issue in issues.itervalues():
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
