#!/usr/bin/python
# -=- encoding: utf-8 -=-

"""Git-hg is a bi-directional interface to Mercurial, like git-svn, but for Hg.

  git hg clone hg://blah/repository [localdir]
  git hg push
  git hg fetch
  git hg pull


Refs:
  Bi-directional support is less robust: https://github.com/offbytwo/git-hg
  Hard to remember: http://traviscline.com/blog/2010/04/27/using-hg-git-to-work-in-git-and-push-to-hg/

"""

import os
import sys

# TODO: when running a command, ensure the Hg bookmark plugin is active and
#       installed

def clone(url, *localdir):
    """This makes an hg clone and makes that appear as a Git repository."""
    if localdir:
        subdir = localdir[0]
    else:
        subdir = os.path.basename(url) or os.path.basename(url[:-1])
    q = os.system("hg clone -U %s %s" % (url,subdir))
    if not q:
        q = os.system("""
cd %s && \
hg update && \
hg bookmark hg/default -r default && \
echo "^\\.git" >> .hg/hgignore && \
echo "[git]
intree = true
exportbranch = refs/head/hg/default
[ui]
ignore = .hg/hgignore" >> .hg/hgrc && \
hg gexport && \
echo '.hg' >> .git/info/exclude && \
git branch --track master hg/default && \
git config core.bare false && \
git reset --hard
""" % subdir)
    return q

def push():
    """Pushes back to the Hg repository.

    Like ``git push``, but up to the remote Mercurial repo.

    """
    q = os.system("hg gimport")
    if not q:
        q = os.system("hg bookmark -f hg/default -r default")
        if not q:
            q = os.system("hg gexport")
    if not q:
        res = raw_input("Import Git commits into Hg local repo. Push back to the Hg remote? ")
        if res.lower() in ('y', 'yes', '1', 'true'):
            q = os.system("hg push")
    return q

def fetch():
    """Update the local branches with what is up on the remote Mercurial repo.

    Equivalent to ``git fetch`` in Git.

    This updates the Git branches to point to the Mercurial ones.

    """
    q = os.system("hg pull")
    if not q:
        q = os.system("hg bookmark -f hg/default -r default")
        if not q:
            q = os.system("hg gexport")
    return q

def pull():
    """Fetch and merge the remote changes to the Hg repo.

    Equivalent to ``git pull`` in Git.

    """
    q = fetch()
    if not q:
        q = os.system("git merge hg/default")
    return q


if __name__ == '__main__':
    map = {'clone': clone,
           'fetch': fetch,
           'pull': pull,
           'push': push}
    if sys.argv[1] in map:
        map[sys.argv[1]](*(sys.argv[2:]))
