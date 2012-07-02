#!/usr/bin/python
# -=- encoding: utf-8 -=-

"""Git-hg is a bi-directional interface to Mercurial, like git-svn, but for Hg.

  git hg clone hg://blah/repository [localdir]
  git hg fetch
  git hg pull [--rebase]
  git hg push


Refs:
  Bi-directional support is less robust: https://github.com/offbytwo/git-hg
  Hard to remember: http://traviscline.com/blog/2010/04/27/using-hg-git-to-work-in-git-and-push-to-hg/

"""

import os
import sys

# TODO: when running a command, ensure the Hg bookmark plugin is active and
#       installed

def clone(url, *args):
    """This makes an hg clone and makes that appear as a Git repository."""
    if len(args) > 1:
        print >>sys.stderr, "git hg clone: don't understand arguments '%s'" % (" ".join(args[1:]),)
        return 1
    if args:
        subdir = args[0]
    else:
        subdir = os.path.basename(url) or os.path.basename(url[:-1])
    q = os.system("hg clone -U %s %s" % (url,subdir))
    if not q:
        q = os.system("""
cd %s && \
hg bookmark default_branchtracker -r default && \
echo "^\\.git" >> .hg/hgignore && \
echo "[extensions]
hggit =
[git]
intree = true
branch_bookmark_suffix = _branchtracker
[ui]
ignore = .hg/hgignore" >> .hg/hgrc && \
hg gexport && \
echo '.hg' >> .git/info/exclude && \
git branch --track master default && \
git config core.bare false && \
git reset --hard
""" % subdir)
    return q

def push(*args):
    """Pushes back to the Hg repository.

    Like ``git push``, but up to the remote Mercurial repo.

    """
    if args:
        print >>sys.stderr, "git hg push: don't understand arguments '%s'" % (" ".join(args),)
        return 1
    q = os.system("hg gimport")
    if not q:
        q = os.system("hg bookmark -f default_branchtracker -r default")
        if not q:
            q = os.system("hg gexport")
    if not q:
        res = raw_input("Imported Git commits into Hg local clone. Push back to the Hg remote? ")
        if res.lower() in ('y', 'yes', '1', 'true'):
            q = os.system("hg push")
    return q

def fetch(*args):
    """Update the local branches with what is up on the remote Mercurial repo.

    Equivalent to ``git fetch`` in Git.

    This updates the Git branches to point to the Mercurial ones.

    """
    if args:
        print >>sys.stderr, "git hg fetch: don't understand arguments '%s'" % (" ".join(args),)
        return 1
    q = os.system("hg pull")
    if not q:
        q = os.system("hg bookmark -f default_branchtracker -r default")
        if not q:
            q = os.system("hg gexport")
    return q

def pull(*args):
    """Fetch and merge the remote changes to the Hg repo.

    Equivalent to ``git pull`` in Git.

    """
    if args and args != ('--rebase',):
        print >>sys.stderr, "git hg pull: don't understand arguments '%s'" % (" ".join(args),)
        return 1
    q = fetch()
    if not q:
        if args:
            q = os.system("git rebase default")
        else:
            q = os.system("git merge default")
    return q


if __name__ == '__main__':
    map = {'clone': clone,
           'fetch': fetch,
           'pull': pull,
           'push': push}
    if sys.argv[1] in map:
        map[sys.argv[1]](*(sys.argv[2:]))
