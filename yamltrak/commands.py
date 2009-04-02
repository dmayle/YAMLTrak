import yamltrak

def main():
    """Parse the command line options and react to them."""
    from optparse import OptionParser

    actions = {'add': yamltrak.add, 'close': yamltrak.close}
    #def add(repository, issue, dbfolder='issues', status=['open']):

    parser = OptionParser()
    for key, value in actions.iteritems():
        parser.add_option('-'+key[0], '--'+key, action="callback",
                          help=value.__doc__, callback=value)

    options, arguments = parser.parse_args() 


if __name__ == '__main__':
    main()
