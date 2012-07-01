Designing the Frontends
=======================

In the accompanying [Backends page](https://github.com/dubiousjim/yagh/blob/master/Frontends.md), we discussed why the `hg-git` Mercurial extension looks to be the best way to shuffle commits back-and-forth between Git and Hg. Here we'll discuss what would be the nicest frontend tool to wrap that up in, from the perspective of a Git user.

On the [README page](https://github.com/dubiousjim/yagh/blob/master/README.md), I describe three existing Git/Hg frontends. Two of these, [git-hg-again](https://github.com/abourget/git-hg-again) and [git-remote-hg](https://github.com/rfk/git-remote-hg), are wrappers around `hg-git`. They make different design choices.

The `git-hg-again` tool installs both the `.git` and `.hg` directories inside a single working directory. It has `hg-git` writing directly from one of these to the other, using the `hg gimport` and `hg gexport` commands. And the way one invokes the tool is with commands like:

    git hg clone url [dir]
    git hg fetch
    git hg pull
    git hg push

The `git-remote-hg` tool also uses the `hg gimport` and `hg gexport` commands. In light of our earlier discussion, though, it doesn't look to me like there's any reason these tools need to limit themselves to those commands, to the exclusion of `hg pull` and `hg push`.

In other respects, the `git-remote-hg` tool makes different choices than `git-hg-again`. These differences are driven by its choice to exploit the `git-remote-helpers` protocol. When initially cloning an upstream Mercurial repository, one specifies its url like this:

    git clone hg::https://code.google.com/p/yagh-test/

(Just plain `git clone` here, not `git hg clone`.) Git sees that the url begins with `hg` and it looks for a `git-remote-hg` program to handle it. That's the hook that the `git-remote-hg` tool uses to introduce its magic. Afterwards, one can just use ordinary Git commands like:

    git fetch
    git pull
    git push

and Git will keep invoking the  `git-remote-hg` helper because it remembers the url of the upstream repository to be something of the form `hg::...`.

The way that `git-remote-hg` does things behind the scenes is also different than `git-hg-again`. First, it keeps the `.hg` folder hidden away out of sight (inside the `.git` folder). Second, it also maintains a *second* `.git` folder, this time one with no working directory, also kept hidden away out of sight. This does mean that you'll have three copies of all your repository data (in addition to the working tree) instead of just two. But it also has a number of advantages. For one, it enables us to expose the Mercurial database to the working Git repository just like regular remote Git repository, where you can have remote tracking branches and so on. Relatedly, it helps you to separate the working branches you don't want to synchronize with the Mercurial upstream from the branches you do want to keep synchronized. The hidden Git repository contains only branches that are kept synchronized with Mercurial. Finally, this separation of a working Git repository from the directly synchronized one means we don't have to worry about Mercurial ever pushing into a branch that the Git user has checked out. The Git repository that Mercurial pushes into never has any checkouts.

So on balance, it looks to me, as it did to the authors of these tools, that the second Git repository makes up for its weight in helping provide a more robust bridge...as well as one that's more idiomatically Gitlike and friendly to use.

As distributed, these tools make various different naming choices. But I'm going to start over and impose a consistent set of names on all of them (the two mentioned here as well as the version of `git-hg` that yagh installs).

Recall the test Mercurial repository we were working with in the Backends discussion:



                                           +-- r17 "latest" <= tip
           all this is                    /
             branch3 ==>     +- r13 <- r14 <-- r16 mark3
                            /             \
    "inactive" branch2 => r12              +-- r15 "head1"
              ends here  /
                       r11 mark2
                       /
    r0 <- r1 <- r2 <- r3 <- r4 <- r5 <- r6 <- r7 <- r8 <= default branch
         tag1              tag2          \   mark1
                                          r9
                                           \
                                            r10 <= branch1


We can list the branches and bookmarks that come from upstream like this:

    Mercurial   Mercurial
    Branches    Bookmarks
    --------    ---------
    default
    branch1
    branch2
    branch3
                mark1
                mark2
                mark3

In our local clone of the Mercurial repository, we will create these additional bookmarks, and keep them synchronized with the tipmost heads of the corresponding branches.

    Mercurial   Mercurial
    Branches    Bookmarks
    --------    ---------
    default     default_branchtracker
    branch1     branch1_branchtracker
    branch2
    branch3     branch3_branchtracker
                mark1
                mark2
                mark3

We don't create a bookmark for branch2 because it's an "inactive" or "non-topological" branch. All of its commits will already be exported as part of branch3.

These bookmarks will be synchronized to branches in our hidden Git repository:

    Mercurial   Mercurial              Hidden Git
    Branches    Bookmarks              Branches
    --------    ---------              -----------
    default     default_branchtracker  default
    branch1     branch1_branchtracker  branch1
    branch2
    branch3     branch3_branchtracker  branch3
                mark1                  mark1
                mark2                  mark2
                mark3                  mark3

And that will be exposed to our working Git repository as a remote named "hg", so the working Git repository will have read-only remote tracking branches named like this:

    Mercurial   Mercurial              Hidden Git   Working Remote-Tracking
    Branches    Bookmarks              Branches     Git Branches
    --------    ---------              -----------  -----------------------
    default     default_branchtracker  default      hg/default
    branch1     branch1_branchtracker  branch1      hg/branch1
    branch2
    branch3     branch3_branchtracker  branch3      hg/branch3
                mark1                  mark1        hg/mark1
                mark2                  mark2        hg/mark2
                mark3                  mark3        hg/mark3


Additionally, the global tags from upstream will be visible in our clone, and will be synchronized with the hidden and working Git repositories. At the moment, though, we will only expose this in the hg->git direction. We won't work out a scheme for migrating new Git (annotated) tags into new Mercurial (global) tags. One of the difficulties there is that on the Git side, creating a new tag doesn't require any new commits, but in Mercurial it does.

Neither will we do anything special to coordinate the `.gitignore` and `.hgignore` files. If these are checked in and pushed to the hidden Git repository, they'll be tracked in Mercurial and Git like any other file. You can synchronize them by hand when needed.

Finally, the `hg-git` extension will also create a set of `default/*` tags that it maintains in our local Mercurial repository. We'll just ignore these. The end-user should ideally not need to go poking around in that Mercurial repository on her own, and these tags won't be pushed upstream.


That will be our design for `git-remote-hg`. For `git-hg`, we can implement something similar, where we get:

    Mercurial   Mercurial              Working Remote-Tracking
    Branches    Bookmarks              Git Branches
    --------    ---------              ------------
    default                            hg/default
    branch1                            hg/branch1
    branch2
    branch3                            hg/branch3
                mark1
                mark2
                mark3

One difference here is that we'll only be implementing *pulling* from Mercurial into Git with this tool. Secondly, bookmarks aren't imported; only Mercurial branches and tags. In the same way we've configured `git-remote-hg`, this tool also makes use of a second, hidden Git repository, which is exposed to the working Git repository as a remote named "hg".

To fetch or pull from those branches, one uses the following commands:

    git hg clone [--force] url [dir]
    git hg fetch [--force]
    git hg pull [--force] [--rebase]
    git hg checkout [--force] branchname

An example of using the last command would be:

    git hg checkout branch2

This will create a new branch named `branch2` in the working Git repository, that tracks the remote `hg/branch2` branch which is synchronized with the upstream Mercurial. If there already exists a local branch `branch2`, the command will fail. After `branch2` has been created, it can be checked out again later using the ordinary `git checkout`. When checked out, it can be brought up-to-date with the Mercurial upstream using:

    git hg pull [--force] [--rebase]



For the `git-hg-again` tool, we'll follow its existing basic design. I'll just add a few refinements.

Note that although this tool creates a Git branch `hg/default`, that is a *local* Git branch that you can read and write to, not a remote tracking branch for some remote `hg`. When you're using this tool, there *is no* remote `hg` repository. We just use the name `hg/default` for memorability.

This tool will create a Mercurial bookmark that it will keep in synch with the tip of the default branch. If there are other Mercurial bookmarks imported from upstream, these will be converted to Git branches too, since this tool is just relying on the standard operations of the `hg-git` extension. If you have to deal with any such complications, you're probably better off using the `git-remote-hg` tool, which is less brittle. In many cases, you could probably get `git-hg-again` to work, but you'll need to know what you're doing. I think `git-remote-hg` is a bit more idiot-proof, and permits you to get away with thinking about Mercurial less. This is all a matter of degree, though.

I'll summarize the changes I made to `git-hg-again` some other time; for now, just see the yagh gitlog


