yagh: Yet Another (set of) Git to Hg bridge(s)
==============================================

I want to use Git to interact with upstream Mercurial repositories. Surely I thought someone else must have already hashed this out. So I looked into what tools were available.

As I describe [at Stack Overflow](http://stackoverflow.com/a/11178693/272427), I found three approaches to this that looked lightweight and initially appealing. Two of the approaches rely on the [**hg-git extension**](http://hg-git.github.com/) for Mercurial; the other approach relies on `hg-fast-export` from the [**fast-export project**](http://repo.or.cz/w/fast-export.git). Here they are (not in order of when they first appeared):


  1. [git-hg-again](https://github.com/abourget/git-hg-again) uses `hg-git` and is inspired by a [2010 blog post by Travis Cline](http://traviscline.com/blog/2010/04/27/using-hg-git-to-work-in-git-and-push-to-hg/). This method uses the toplevel directory as a working directory for both Mercurial and Git at the same time. It creates a Mercurial bookmark that it keeps in synch with the tip of the `default` (unnamed) branch in the Mercurial repository; and it updates a local Git branch from that bookmark. 

  2. [git-remote-hg](https://github.com/rfk/git-remote-hg) also uses `hg-git`, and additionally makes use of the `git-remote-helpers` protocol. This method uses the toplevel directory only as a working directory for Git; it keeps its Mercurial repository bare. It also maintains a second bare Git repository to make synching between Git and Mercurial safer and more idiomatically Gitlike.

  3. The [git-hg](https://github.com/cosmin/git-hg) script (formerly maintained [here](https://github.com/offbytwo/git-hg)) uses `hg-fast-export`. Like method 2, this also maintains a bare Mercurial repository and an additional bare Git repository.

    For pulling, this tool ignores Mercurial bookmarks and instead imports every named Mercurial branch into a Git branch, and the `default` (unnamed) Mercurial branch into `master`.

    Some commentary discusses this tool as being hg->git only, but it claims to have merged in git->hg push support on 7 Dec 2011. As I discuss on the Backends page, though, the way this tool tries to implement push support doesn't seem to be workable.


*Don't confuse `hg-git` with `git-hg`!* The first is a Mercurial extension that's a backend to some of these tools, the second is a frontend script that doesn't make any use of the first.

I wasn't sure which of these tools would work best, so I tried out all three. None of them are yet packaged or documented in a friendly way, but they're not very complicated either. The underlying machinery they make use of (the `hg-git` extension, the `git-remote-helpers` protocol, and the `hg-fast-export` script) are what do the heavy lifting.

I saw some ways to usefully tweak the different frontends---in some cases, these tweaks were necessary to get them to run on the FreeBSD machine I'm currently using---and I also thought it'd help evaluate them to make their behind-the-scenes layout more like each other's. This github repo holds the results. I also included a Makefile that will let you install any of the three. I encourage you to try them out and decide for yourself what works best.

Details on installing and using (the yagh versions of) these tools are below.

You might also like to read the accompanying [Backends page](https://github.com/dubiousjim/yagh/blob/master/Backends.md), which gives the different backend choices a work-out and figures out what works best. The [Frontends page](https://github.com/dubiousjim/yagh/blob/master/Frontends.md) then discuss the design choices behind why these frontends work as they do here.


## Installation ##

I think these different Git/Hg bridges can work under Windows, too, but I don't know much about that, and will continue on the assumption you're trying to install to some Unix-like system.

You'll need to have Git and Mercurial already installed. I'll leave that to you.

If you plan to use either `git-hg-again` or `git-remote-hg`, you'll need to have the `hg-git` Mercurial extension installed. Perhaps your distribution already packages this. If not, you might install it by typing `easy_install hg-git`. Or see the [hg-git homepage](http://hg-git.github.com/) for more information.

Concerning the installation of `hg-git`, you may see references to including some of the following in your `~/.hgrc`:

    [extensions]
    hggit = 
    bookmarks =

The `bookmarks` line isn't necessary anymore; that's been built into the Mercurial core since version 1.8, released 1 March 2011. The `hggit` line can be included in your `~/.hgrc` if you like; but the versions of these tools that are distributed with yagh will also specify that in the individual repositories, so you really don't need to bother with it.

To use the version of `git-remote-hg` that I'm supplying here, the upstream Mercurial server you're interacting with needs to support bookmarks. So it either needs to be version `>=` 1.8, or it needs to have the older `bookmarks` extension enabled.

Finally, type *one of* the following:

    gmake && sudo gmake install-git-hg-again
    gmake && sudo gmake install-git-remote-hg
    gmake && sudo gmake install-git-hg

(If you don't like using `sudo`, I expect you'll know what to do instead.) I say `gmake` to make it clear that you need to use GNU Make. On some systems, that's only installed under the name `make`.

This will install yagh's version of the chosen system. Only one such can be enabled at a time. If you want to evaluate a different system, just request its installation, and the previous one will automatically be disabled.

If you want to uninstall all this stuff, type:

    sudo gmake uninstall


## How do the versions distributed here differ from their upstream originals? ##

See [the git logs](https://github.com/dubiousjim/yagh/commits/master). I will inform the upstream authors of the changes that seemed useful, and will try to keep track of other changes they make to the originals. I'll be glad to hear about cases where any of these tools break.


## How does one use these tools? ##

That depends on which tool you're using. I've tried to make the versions packaged here behave as close to each other as possible, but they're still not exactly the same.

*Note that these instructions apply to these tools as configured in yagh, which differ in several ways from how the original authors distribute them.*

### Using git-remote-hg ###

To clone from an upstream Mercurial repository:

    git clone hg::url [localdir]

Bookmarks and branches in the Mercurial repository will be visible in Git as remote tracking branches of the form:

    hg/default
    hg/branch1
    hg/bookmark1

To keep up to date:

    git fetch [hg]
    git pull [--rebase] [hg]
    git push

These are just the plain `git fetch` and so on commands. You can omit the `hg` if you're in a branch that tracks part of the upstream Mercurial repository. Your `master` branch is initially set up to do so.

To push "new branches" into the Mercurial repository, do this:

    git push hg git_branchname:hg_branchname
    git branch --set-upstream git_branchname hg/hg_branchname

If you want the branch to be named the same on both ends, you can just use `branchname` instead of `branchname:branchname`. (But you still need to call `git branch --set-upstream ...`) Note that what these commands will do is push a new Mercurial *bookmark* upstream; when you push and pull, that bookmark will be kept in synch with the head of your Git branch.

All of your Git commits will belong to the `default` branch in Mercurial, even if they're on a Git branch that you based on a named Mercurial branch. This means that you may be pushing multiple unmerged heads upstream, one for each of the Git branches you push changes on. Hopefully the maintainers and other users of the upstream repository will be OK with that.

Our frontend will try to keep the `hg/default` branch (which your `master` branch pulls from) in synch with the Mercurial commits that no other Git branch/Mercurial bookmark is tracking.

If you want to delete a Mercurial branch, you can try this:

    git push hg :hg_branchname_to_delete

Note though that this will only delete the "branches" that are implemented as Mercurial bookmarks. Those that correspond to named branches in the Mercurial repository will be automatically re-created in your `hg` Git remote the next time you pull. If you want to ignore them, just don't base any local Git branches on them.

This tool permits the use of *multiple* Mercurial remotes for a given Git repository. Just specify the ones after the first by:

    git remote add [-t branch] [--tags] remotename hg::url

Then you can `git fetch remotename` and so on as usual.

Global tags from Mercurial upstream will be pulled into Git annotated tags, but won't be pushed back in the other direction. Additionally, no attempt is made to coordinate `.gitignore` and `.hgignore`.


### Using git-hg ###

To clone from an upstream Mercurial repository:

    git hg clone [--force] url [localdir]

The `--force` will be needed if the repository has multiple heads on a branch.

Branches from the Mercurial repository will be visible in Git as remote tracking branches of the form:

    hg/default
    hg/branch1

To checkout a new local branch following one of the remote branches, use:

    git hg checkout [--force] branch1

This will create a new branch named `branch1` in your working Git repository, that tracks the remote `hg/branch1` branch which is synchronized with upstream Mercurial. If there already exists a local branch `branch1`, the command will fail. After `branch1` has been created, it can be checked out again later using the ordinary `git checkout`. When checked out, it can be brought up-to-date with the Mercurial upstream using:

    git hg pull [--force] [--rebase]

or you can use:

    git hg fetch [--force]

and `git merge` or `git rebase` by hand. The same commands are used to bring your `master` branch up-to-date.

This tool doesn't provide good push support.


### Using git-hg-again ###

To clone from an upstream Mercurial repository:

    git hg clone url [localdir]

This will create a local Git branch `default`, that your `master` branch will track and be based on. You can also commit directly to `default`.

To keep up to date afterwards:

    git hg fetch
    git hg pull [--rebase]
    git hg push


## Mercurial for Git Users ##

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
