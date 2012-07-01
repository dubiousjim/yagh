#!/usr/bin/env python


"""

git_remote_hg:  access hg repositories as git remotes
=====================================================

Are you a git junkie but need to work on projects hosted in mercurial repos?
Are you too stubborn, lazy or maladjusted to learn another VCS tool?  I
know I am.  But fear not!  This script will let you interact with mercurial
repositories as if they were ordinary git remotes.

Git allows pluggable remote repository protocols via helper scripts.  If you
have a script named "git-remote-XXX" then git will use it to interact with
remote repositories whose URLs are of the form XXX::some-url-here.  So you
can imagine what a script named git-remote-hg will do.

Yes, this script provides a remote repository implementation that communicates
with mercurial.  Install it and you can do::

    $ git clone hg::https://hg.example.com/some-mercurial-repo
    $ cd some-mercurial-repo
    $ # hackety hackety hack
    $ git commit -a
    $ git push

Tada!  Your commits from git will show up in the remote mercurial repo, and
none of your co-workers will be any the wiser.

All the hard work of interoperating between git and mercurial is done by the
awesome hg-git module.  All the hard work of speaking the git-remote-helper
protocol is done by git's own http-protocol handlers.  This script just hacks
them together to make it all work a little easier.

For each remote mercurial repository, you actually get *two* additional
repositories hidden inside your local git repo:

    * .git/hgremotes/[URL]:           a local hg clone of the remote repo
    * .git/hgremotes/[URL]/.hg/git:   a bare git repo managed by hg-git

When you "git push" from your local git repo into the remote mercurial repo,
here is what git-remote-hg will do for you:

    * use git-remote-http to push into .git/hgremotes/[URL]/.hg/git
    * call "hg gimport" to import changes into .git/hgremotes/[URL]
    * call "hg push" to push them up to the remote repo

Likewise, when you "git pull" from the remote mercurial repo into your local
git repo, here is what happens under the hood:

    * call "hg pull" to pull changes from the remote repo
    * call "hg gexport" to export them into .git/hgremotes/[URL]/.hg/git
    * use git-remote-http to pull them into your local repo

Ugly?  Sure.  Hacky?  You bet.  But it seems to work remarkably well.

"""

__ver_major__ = 0
__ver_minor__ = 1
__ver_patch__ = 1
__ver_sub__ = ""
__version__ = "%d.%d.%d%s" % (__ver_major__,__ver_minor__,__ver_patch__,__ver_sub__)


import sys
import os
import subprocess
import threading
import socket
import time
import urllib
import wsgiref.simple_server
from textwrap import dedent

class RemoteHGError(RuntimeError):
    pass


def main(argv=None, git_dir=None):
    """Main entry-point for the git-remote-hg script.

    This function can be called to act as a git-remote-helper script that
    will communicate with a remote mercurial repository.  It basically does
    the following:

        * ensure there's a local hg checkout in .git/hgremotes/[URL]
        * ensure that it has a matching hg-git repo for import/export
        * update the hg-git repo from the remote mercurial repo
        * start a background thread running git-http-backend to communicate
          with the hg-git repo
        * shell out to hg-remote-http to push/pull into the hg-git repo
        * send any changes from the hg-git repo back to the remote

    Simple, right?
    """
    if argv is None:
        argv = sys.argv
    env = os.environ
    if git_dir is None:
        git_dir = env.get("GIT_DIR", None)
    if git_dir is None:
        git_dir = os.getcwd()
        if os.path.exists(os.path.join(git_dir, ".git")):
            git_dir = os.path.join(git_dir, ".git")

    #  AFAICT, we always get the hg repo url as the second argument.
    hg_url = argv[2]

    #  Grab the local hg-git checkout, creating it if necessary.
    hg_checkout = HgGitCheckout(git_dir, hg_url)

    #  Start git-http-backend to push/pull into the hg-git checkout.
    backend = GitHttpBackend(hg_checkout.git_repo_dir)
    t = backend.start()
    try:
        #  Wait for the server to come up.
        while backend.repo_url is None:
           time.sleep(0.1)

        #  Grab any updates from the remote repo.
        #  Do it unconditionally for now, so we don't have to interpret
        #  the incoming hg-remote-helper stream to determine push/pull.
        #  This is also a good idea because it helps us locally detect
        #  any merge conflicts when trying to `git push`.
        hg_checkout.pull()

        #  Use git-remote-http to send all commands to the HTTP server.
        #  This will push any incoming changes into the hg-git checkout.
        cmd = ("git", "remote-http", backend.repo_url, )
        retcode = subprocess.call(cmd, env=os.environ)
        #  TODO: what are valid return codes?  Seems to be almost always 1.
        if retcode not in (0, 1):
            msg = "git-remote-http failed with error code %d" % (retcode,)
            raise RemoteHGError(msg)

        if "GIT_PREFIX" in env:
            #  FIXME: We don't interpret the incoming hg-remote-helper stream to determine push/pull.
            if env.get("GIT_REFLOG_ACTION", "push") == "pull":
                pass
            else:
                #  If git-remote-http worked OK, push any changes up to the remote URL.
                hg_checkout.push()
        else:
            # cloning
            # check whether we need to complete any initialization
            hg_checkout.finish_initialization()

    finally:
        #  Make sure we tear down the HTTP server before quitting.
        backend.stop()
        t.join()


class HgGitCheckout(object):
    """Class managing a local hg-git checkout.

    Given the path of a local git repository and the URL of a remote hg
    repository, this class manages a hidden hg-git checkout that can be
    used to shuffle changes between the two.
    """

    def __init__(self, git_dir, hg_url):
        self.hg_url = hg_url
        self.hg_name = hg_name = urllib.quote(hg_url, safe="")
        self.hg_repo_dir = os.path.join(git_dir, "hgremotes", hg_name)
        self.git_repo_dir = os.path.join(self.hg_repo_dir, ".hg", "git")
        if not os.path.exists(os.path.join(git_dir, "hgremotes")):
            self.git_dir = git_dir
        else:
            self.git_dir = False
        if not os.path.exists(self.hg_repo_dir):
            self.initialize_hg_repo()

    def _get(self, *cmd, **kwds):
        """Run a hg command, capturing and returning output."""
        silent = kwds.pop("silent", False)
        returncodes = kwds.pop("returncodes", (0,))
        kwds["stdout"] = subprocess.PIPE
        kwds["stderr"] = subprocess.STDOUT
        p = subprocess.Popen(cmd, **kwds)
        (out, err) = p.communicate()
        if err or p.returncode not in returncodes:
            if err:
                print>>sys.stderr, "hg: " + err.strip()
            msg = "%s %s failed with error code %d" % (cmd[0], cmd[1], p.returncode)
            raise RemoteHGError(msg)
        return out.splitlines()

    def _do(self, *cmd, **kwds):
        """Run a hg command, capturing and printing output to stderr."""
        silent = kwds.pop("silent", False)
        returncodes = kwds.pop("returncodes", (0,))
        kwds["stdout"] = subprocess.PIPE
        kwds["stderr"] = subprocess.STDOUT
        p = subprocess.Popen(cmd, **kwds)
        output = p.stdout.readline()
        while output:
            if not silent:
                print>>sys.stderr, "hg: " + output.strip()
            output = p.stdout.readline()
        if p.wait() not in returncodes:
            msg = "%s %s failed with error code %d" % (cmd[0], cmd[1], p.returncode)
            raise RemoteHGError(msg)

    def pull(self):
        """Grab any changes from the remote repository."""
        hg_repo_dir = self.hg_repo_dir
        in_marks = ["-B"+b.split()[0] for b in
                self._get("hg", "incoming", "-Bq", cwd=hg_repo_dir, returncodes=(0,1))]
        default_old = int(self._get("hg", "identify", "-nr", "default", cwd=hg_repo_dir)[0])
        # hg pulling with in_marks
        self._do("hg", "pull", *in_marks, cwd=hg_repo_dir)
        for branch in self._get("hg", "branches", "--active", "-q", cwd=hg_repo_dir):
            if branch <> "default":
                self._do("hg", "bookmark", "-fr", branch, branch+"_branchtracker", cwd=hg_repo_dir)
        # advance default?
        default_new = int(self._get("hg", "identify", "-nr", "default", cwd=hg_repo_dir)[0])
        if default_new > default_old:
            self._do("hg", "bookmark", "-fr", "default", "default_branchtracker", cwd=hg_repo_dir)
        self._do("hg", "gexport", cwd=hg_repo_dir)

    def push(self):
        """Push any changes into the remote repository."""
        hg_repo_dir = self.hg_repo_dir
        hg_marks = set(b[:-14] if b.endswith("_branchtracker") else b for b in
                self._get("hg", "bookmarks", "-q", cwd=hg_repo_dir))
        git_branches = set(b[2:] for b in
                self._get("git", "--git-dir=.", "branch", cwd=self.git_repo_dir))
        deleted = hg_marks - git_branches
        for b in deleted:
            self._do("hg", "bookmark", "-d", b, cwd=hg_repo_dir)
        # created = git_branches - hg_marks
        self._do("hg", "gimport", cwd=hg_repo_dir)
        # we advance default unless another bookmark points to tip
        if not self._get("hg", "log", "-r", "default", "--template={bookmarks}", cwd=hg_repo_dir):
            self._do("hg", "bookmark", "-fr", "default", "default_branchtracker", cwd=hg_repo_dir)
        out_marks = [b.split()[0] for b in
            self._get("hg", "outgoing", "-Bq", cwd=hg_repo_dir, returncodes=(0,1))]
        out_marks = ["-B"+b for b in out_marks if not b.endswith('_branchtracker')]
        if deleted:
            in_marks = set(b.split()[0] for b in
                    self._get("hg", "incoming", "-Bq", cwd=hg_repo_dir, returncodes=(0,1)))
            out_marks += ["-B"+b for b in deleted if b in in_marks]
        # we have to push -f whenever we've created new heads
        self._do("hg", "push", "-f", *out_marks, cwd=hg_repo_dir)

    def initialize_hg_repo(self):
        hg_repo_dir = self.hg_repo_dir
        if not os.path.isdir(os.path.dirname(hg_repo_dir)):
            os.makedirs(os.path.dirname(hg_repo_dir))
        # have to clone without -U to create working dir
        self._do("hg", "clone", self.hg_url, hg_repo_dir)
        self._do("hg", "update", "null", cwd=hg_repo_dir, silent=True)
        with open(os.path.join(hg_repo_dir, "README.txt"), "wt") as f:
            f.write(dedent("""
            This is a bare mercurial checkout created by git-remote-hg.
            Don't mess with it unless you know what you're doing.
            """))
        with open(os.path.join(hg_repo_dir, ".hg", "hgrc"), "at") as f:
            f.write(dedent("""
            [extensions]
            hggit = 
            [git]
            branch_bookmark_suffix = _branchtracker
            """))
            for branch in self._get("hg", "branches", "--active", "-q", cwd=hg_repo_dir):
                # this handles the default branch too
                self._do("hg", "bookmark", "-r", branch, branch+"_branchtracker", cwd=hg_repo_dir)
        self._do("hg", "gexport", cwd=hg_repo_dir)
        with open(os.path.join(self.git_repo_dir, "HEAD"), "wt") as f:
            f.write("ref: refs/heads/default\n")

    def finish_initialization(self):
        git_dir = self.git_dir
        if git_dir:
            self._do("git", "branch", "-m", "default", "master", cwd=git_dir)
            self._do("git", "remote", "rename", "origin", "hg", cwd=git_dir)
            with open(os.path.join(git_dir, "config"), "at") as f:
                f.write(dedent("""
                [push]
                default = upstream
                """))

class SilentWSGIRequestHandler(wsgiref.simple_server.WSGIRequestHandler):
    """WSGIRequestHandler that doesn't print to stderr for each request."""
    def log_message(self, format, *args):
        pass


class GitHttpBackend(object):
    """Run git-http-backend in a background thread.

    This helper class lets us run the git-http-backend server in a background
    thread, bound to a local tcp port.  The main thread can then interact
    with it as needed.
    """

    def __init__(self, git_dir):
        self.git_dir = os.path.abspath(git_dir)
        self.git_project_root = os.path.dirname(self.git_dir)
        self.git_project_name = os.path.basename(self.git_dir)
        self.server = None
        self.server_url = None
        self.repo_url = None

    def __call__(self, environ, start_response):
        """WSGI handler.

        This simply sends all requests out to git-http-backend via
        standard CGI protocol.  It's nasty and inefficient but good
        enough for local use.
        """
        cgienv = os.environ.copy()
        for (k,v) in environ.iteritems():
            if isinstance(v, str):
                cgienv[k] = v
        cgienv["GIT_PROJECT_ROOT"] = self.git_project_root
        cgienv["GIT_HTTP_EXPORT_ALL"] = "ON"
        cgienv["REMOTE_USER"] = "rfk"
        cmd = ("git", "http-backend", )
        p = subprocess.Popen(cmd, env=cgienv, cwd=self.git_dir,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        if environ.get("CONTENT_LENGTH",None):
            data = environ["wsgi.input"].read(int(environ["CONTENT_LENGTH"]))
            p.stdin.write(data)
        p.stdin.close()
        headers = []
        header = p.stdout.readline()
        while header.strip():
            headers.append(header.split(":", 1))
            header = p.stdout.readline()
        headers = [(k.strip(), v.strip()) for (k,v) in headers]
        start_response("200 OK", headers)
        return [p.stdout.read()]

    def _make_server(self, addr, port):
        make = wsgiref.simple_server.make_server
        return make(addr, port, self, handler_class=SilentWSGIRequestHandler)
                                                 
    def run(self):
        """Run the git-http-backend server."""
        port = 8091
        while True:
            try:
                self.server = self._make_server("127.0.0.1", port)
                break
            except socket.error:
                port += 1
        self.server_url = "http://127.0.0.1:%d/" % (port,)
        self.repo_url = self.server_url + self.git_project_name
        self.server.serve_forever()

    def start(self):
        """Run the git-http-backend server in a new thread."""
        t = threading.Thread(target=self.run)
        t.start()
        return t

    def stop(self):
        """Stop the git-http-backend server."""
        self.server.shutdown()


if __name__ == "__main__":
    import sys
    try:
        res = main()
    except RemoteHGError, msg:
        print>>sys.stderr, msg
        print>>sys.stderr
        res = 1
    except KeyboardInterrupt:
        res = 1
    sys.exit(res)
