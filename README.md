yagh: Yet Another set of Git to Hg interfaces
=============================================

I want to use Git to interact with upstream Mercurial repositories. Surely I thought someone else must have already hashed this out. So I looked into what tools were available.

As I posted in [this Stack Overflow question](http://stackoverflow.com/a/11178693/272427), I found three approaches to this that looked lightweight and initially appealing. Two of the approaches rely on the [**hg-git extension**](http://hg-git.github.com/) for Mercurial; the other approach relies on `hg-fast-export` from the [**fast-export project**](http://repo.or.cz/w/fast-export.git). Here they are (not in order of when they first appeared):


  1. [git-hg-again](https://github.com/abourget/git-hg-again) uses `hg-git` and is inspired by a [2010 blog post by Travis Cline](http://traviscline.com/blog/2010/04/27/using-hg-git-to-work-in-git-and-push-to-hg/). This method uses the toplevel directory as a working directory for both Mercurial and Git at the same time. It creates a Mercurial bookmark that it keeps in synch with the tip of the `default` (unnamed) branch in the Mercurial repository; and it updates a local Git branch from that bookmark. 

  2. [git-remote-hg](https://github.com/rfk/git-remote-hg) also uses `hg-git`, and additionally makes use of the `git-remote-helpers` protocol. This method uses the toplevel directory only for a Git working directory; it keeps its Mercurial repository bare. It also maintains a second bare Git repository to make synching between Git and Mercurial safer and more idiomatically Gitlike.

  3. The [git-hg](https://github.com/cosmin/git-hg) script (formerly maintained [here](https://github.com/offbytwo/git-hg)) uses hg-fast-export. Like method 2, this also keeps a bare Mercurial repository and an additional bare Git repository. Some commentary discusses this tool as being hg->git only, but it claims to have merged in git->hg push support on 7 Dec 2011. As we'll discuss below, though, the way this tool tries to implement push support doesn't seem to be workable. On the pull side, it ignores Mercurial bookmarks and instead imports every named Mercurial branch into a Git branch, and the `default` (unnamed) Mercurial branch into `master`.

*Don't confuse `hg-git` with `git-hg`!* The first is a Mercurial extension that's a backend to some of these tools, the second is a frontend script that doesn't make any use of the first.

I wasn't sure which of these tools would work best, so I tried out all three. None of them are yet packaged or documented in a friendly way, but they're not complicated either. The underlying machinery they make use of (the `hg-git` extension, the `git-remote-helpers` protocol, and the `hg-fast-export` script) are what do the heavy lifting.

I saw some ways to usefully tweak the different frontends---in some cases, these tweaks were necessary to get them to run on the FreeBSD machine I'm currently using---and I also thought it'd help evaluate them to tweak them to make their behind-the-scenes layout more like each other's. This github repo holds the results. I also included a Makefile that will let you install any of the three. I encourage you to try them out and decide for yourself what works best.

Details on installing and using (the yagh versions of) these tools are below.

You might also like to read the accompanying Evaluation.md page, which gives the different backend and frontend choices a work-out and figures out what works best.


## Installation ##

I think these different Git-Hg bridges can work under Windows, too, but I don't know much about that, and will continue on the assumption you're trying to install to some Unix-like system.

You'll need to have Git and Mercurial already installed. I'll leave that to you.

If you plan to use either git-hg-again or git-remote-hg, you'll need to have the Hg-Git Mercurial extension installed. Perhaps your distribution already packages this. If not, you might install it by typing `easy_install hg-git`. Or see the 
[hg-git homepage](http://hg-git.github.com/) for more information. You may see references to including some of the following in your `~/.hgrc`:

    [extensions]
    hggit = 
    bookmarks =

The `bookmarks` line isn't necessary anymore; that's been built into Mercurial since version 1.8, released 2011-03-01. The `hggit` line can be included in your `~/.hgrc` if you like; but the versions of these tools that are distributed here will also specify that in the individual repositories, so you really don't need to bother with it.

Finally, type *one of* the following:

    gmake && sudo gmake install-git-hg-again
    gmake && sudo gmake install-git-remote-hg
    gmake && sudo gmake install-git-hg

(If you don't like using `sudo`, I expect you'll know what to do instead.) I say `gmake` to make it clear that you need to use GNU Make. On some systems, that's only installed under the name `make`.

This will install our version of the chosen system. Only one such can be enabled at a time. If you want to evaluate a different one, just give the command to install the new one, and the previous one will automatically be disabled.

If you want to uninstall all this stuff, type:

    sudo gmake uninstall


## How do the versions distributed here differ from their upstream originals? ##

See [the git logs](https://github.com/dubiousjim/yagh/commits/master). I will inform the upstream authors of the changes that seemed useful, and will try to keep track of other changes they make to the originals. I'll be glad to hear about cases where any of these tools break.


## How does one use these tools? How do they work? ##

That depends on which tool you're using. I've tried to make the versions packaged here behave as close to each other as possible, but they're still not exactly the same.

*Note that these instructions apply to these tools as configured in yagh, which differ in several ways from how the original authors distribute the tools.*


WORKING ON THESE INSTRUCTIONS...

