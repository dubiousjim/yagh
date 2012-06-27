yagh: bi-directional Git to Mercurial interfaces
================================================

I was looking at the state of play in Git-Hg bridges. I've gotten used to Git, and hoped to be able to at least read, but preferably also push to, Mercurial repos while using mostly Git idioms.

As I posted in [this Stack Overflow question](http://stackoverflow.com/a/11178693/272427), I found three approaches to this problem that looked lightweight and initially appealing. Two of the approaches rely on the [**hg-git extension**](http://hg-git.github.com/) for Mercurial; the other approach relies on hg-fast-export from the [**fast-export project**](http://repo.or.cz/w/fast-export.git). Here they are (not in order of when they first appeared):

  1. [git-hg-again](https://github.com/abourget/git-hg-again) uses hg-git and is inspired by a [2010 blog post by Travis Cline](http://traviscline.com/blog/2010/04/27/using-hg-git-to-work-in-git-and-push-to-hg/). This method uses the toplevel directory as a working directory for both Mercurial and Git at the same time. It creates a Mercurial bookmark "default" that tracks the "default" named branch, and updates a local Git branch from that bookmark. 

  2. [git-remote-hg](https://github.com/rfk/git-remote-hg) also uses hg-git, and additionally makes use of the git-remote-XXX protocols. This method uses the toplevel directory only for a Git working directory; it keeps its Mercurial repository bare. It also maintains a second bare Git repository to make synching between Git and Mercurial safer and more idiomatically gitlike.

  3. The [git-hg](https://github.com/cosmin/git-hg) script (formerly maintained [here](https://github.com/offbytwo/git-hg)) uses hg-fast-export. Like method 2, this also keeps a bare Mercurial repository and an additional bare Git repository. Some commentary discusses this tool as being hg->git only, but it has had bidirectional support now for a while. As we'll discuss below, though, I've found the bidirectional support from the other methods to be better aligned with how I was expecting these tools to work.

I wasn't sure which of these strategies would work best, so I tried out all three. None of them are naive-user-friendly, but they're not that complicated either once you take the time to study them. The different backend engines (the hg-git Mercurial extension, the git-remote-XXX protocol, and the hg-fast-export script) are doing the heavy lifting; these are just different frontends for them.

I saw some ways to usefully tweak the different frontends---in some cases, these tweaks were necessary to get them to run on the FreeBSD machine I'm using right now---and I also thought it'd help evaluate them to tweak them to make their behind-the-scenes layout more like each other's. This github repo holds the results. I've also included a Makefile that will let you install any of the three. I encourage you to try them out and decide for yourself what works best. I'll be glad to hear about cases where these tools break. Until I've definitively made up my mind which of these tools to use, I'll try to keep them in synch with upstream changes.


Installation
------------

I think these different Git-Hg bridges can work under Windows, too, but I don't know much about that, and will continue on the assumption you're trying to install to some Unix-like system.

You'll need to have Git and Mercurial already installed. I'll leave that to you.

Next, you'll need to install either the Hg-Git Mercurial extension, or the hg-* scripts from the fast-export project, or both. If your distribution already packages some of these, you might install them using your package manager. Or you might install the Hg-Git extension by typing `easy_install hg-git`. But you don't need to do 
 any of this manually, if you don't want to. The Makefile will try to install the needed backend components itself if it sees they aren't present.

If you do install the Hg-Git Mercurial extension yourself, you may see references to including some of the following in your `~/.hgrc`:

    [extensions]
    hggit = 
    bookmarks =

The `bookmarks` line isn't necessary anymore; that's been built into Mercurial since version 1.8, released 2011-03-01. The `hggit` line can be included in your `~/.hgrc` if you like; but the versions of these tools that are distributed here will also specify that in the individual repositories, so you really don't need to bother with it.

Finally, type *one of* the following:

    sudo gmake install git-hg-again
    sudo gmake install git-remote-hg
    sudo gmake install git-hg

(If you don't like using `sudo`, I expect you'll know what to do instead.) I say `gmake` to make it clear that you need to use GNU Make. On some systems, that's only installed under the name `make`.

This will install our version of the chosen system. Only one such can be installed at a time; so if you want to evaluate a different one, you'll need to:

    sudo gmake uninstall

and then `install` the new one.


How do the versions distributed here differ from their upstream originals?
--------------------------------------------------------------------------

See [the git logs](https://github.com/dubiousjim/yagh/commits/master). I will also suggest various of these changes to the upstream authors, and will try to keep track of those and other changes they make.


How do I use these tools?
-------------------------

That depends on which tool you're using. I've tried to make the versions packaged here behave as close to each other as possible, but they're still not exactly the same.

TODO: Fill in more details...

TODO: Supply Makefile



Mercurial for Git Users
-----------------------

Here are some useful comparisons/translation manuals between Git and Mercurial, in some cases targetted at users who already know Git:

  * [Mercurial for Git users](http://mercurial.selenic.com/wiki/GitConcepts)
  * [Git and Mercurial - Compare and Contrast](http://stackoverflow.com/questions/1598759/git-and-mercurial-compare-and-contrast)
  * [What is the difference between Mercurial and Git](http://stackoverflow.com/questions/35837/what-is-the-difference-between-mercurial-and-git)
  * [Mercurial and Git: a technical comparison](http://alblue.bandlem.com/2011/03/mercurial-and-git-technical-comparison.html)
  * [Git hg rosetta stone](https://github.com/sympy/sympy/wiki/Git-hg-rosetta-stone)
  * [Homebrew Coding: Mercurial](http://quirkygba.blogspot.com/2009/04/mercurial.html)
  * [Francisoud's Blog: Git vs Mercurial (hg)](http://francisoud.blogspot.com/2010/07/git-vs-mercurial.html)
  * [Git vs Mercurial](http://www.wikivs.com/wiki/Git_vs_Mercurial)


--  
Dubiousjim  
dubiousjim@gmail.com  
https://github.com/dubiousjim  

