Evaluation
==========

The Backend Candidates
----------------------

As mentioned above, there are a couple of different backend methods one can use to drive a Git/Hg bridge, and then some additional choices one can make about packaging those backends for day-to-day use. (In git-speak, what "porcelain" to install on top of them.)

Before we sort out our frontend choices, though, we've got to settle which backend engines work best. Here are the options.

1. `git fast-import` is a component in the standard Git distribution that imports text-serialized repositories. There is another component `git fast-export` that serializes Git repositories to the needed format; but what we need is a way to serialize *Mercurial* repositories into that format. Someone has in fact made that; it's available as the `hg-fast-export` scripts (`hg-fast-export.py`, `hg-fast-export.sh`, and `hg2git.py`) that are in the [fast-export project](http://repo.or.cz/w/fast-export.git). (That project also has some `hg-reset` scripts that I don't yet understand; and also some scripts for interacting with Subversion.)

    So these `hg-fast-export` scripts provide a way to serialize a Mercurial repository, and we can pipe the result into `git fast-import`. That's one way to go from hg->git. It's what the `git-hg` script uses.


2. How about the reverse direction, from git->hg? One way to do this is with the [convert extension](http://mercurial.selenic.com/wiki/ConvertExtension) for Mercurial (see also [here](http://www.selenic.com/mercurial/hg.1.html#convert)). This again is what the `git-hg` script uses. The `convert` extension already comes with the standard Mercurial distribution, though it's not enabled by default. No problem, though: whatever frontend porcelain we build can just explicitly enable it for the Mercurial repos we use.
    
    This extension is able to keep track of conversions that it has already made into a Mercurial repository, so that later conversions can be incremental. However, as we'll see below, there are severe limits to how well this works when we combine it with hg->git exports going in the other direction.


3. A different Mercurial extension is [hg-git](http://hg-git.github.com/). This *isn't* part of the standard Mercurial distribution, but needs to be installed separately. As with the `convert` extension, our frontend porcelain can take care of enabling this extension in the repositories where we're going to use it, so the user doesn't need to make it enabled globally. She just needs to have it installed.

    The documentation for the `hg-git`  extension describes three different modes of operation. The first involves cloning a Mercurial repository from an existing upstream Git repository. That doesn't fit our needs; it's instead what someone has to do who wants to *use Mercurial to interact with Git-based projects.* We're interested in the reverse. The second mode described involves starting with a Mercurial repository, spawning a Git repository off of *it*, and then interacting with that Git repository just as in the first method. This is a method we could use. We will call it our method 3. It would permit going in both directions: both pulling from Mercurial into Git and pushing back.

    The documentation for `hg-git` says that this method can't be used with *local* Git repositories because the [Dulwich Python Git library](http://www.samba.org/~jelmer/dulwich/) they rely on ["doesn't support local repositories yet"](https://bitbucket.org/durin42/hg-git/). They say you have to speak to the Git repository over a network (though it could simply be a network connection to localhost). They wrote that on 6 April 2010. But on my machine, I'm not encountering any such limitations. It looks like in recent versions of Dulwich, using a local Git repository, specified by a plain old pathname, works fine. It's not easy to tell when this started working; the Dulwich changelog doesn't obviously refer to it. From their git log, I'm guessing they started to add it around 2 April 2010.

4. I said that the documentation for `hg-git` describes three modes of operation. The last of these provides a different way we could use the extension. This involves, not `push`ing and `pull`ing to a Git repository that may be (but needn't be) remote, but rather `gexport`ing and `gimport`ing to a local Git repository. The default behavior is to `gexport` and `gimport` to a *bare* Git repository *hidden in the `.hg` folder*, but in fact we can arrange for that repository to be located anywhere and it needn't be left bare. One of the existing frontends has this Git repository sharing its working directory with the local Mercurial repository.


There are details to work out about which parts of the Mercurial repository we're going to synch to Git: the tip of the default branch for sure, but what about other named branches? what about bookmarks from upstream? what about tags? And what parts of Git are we going to synch to Mercurial: which branches and how will they be identified in the Hg repository? and again, what about tags?

But as we muddle over those questions, let's start exploring what constraints these different backends impose. That may affect the decisions we make about what gets synched with what.


I created a test Mercurial repository that you can clone from <https://code.google.com/p/yagh-test/>. This is a small repository displaying a variety of features: it has several named branches, one of them "inactive" and another with multiple heads. There are also some bookmarks already in the upstream repository, and some committed tags. Here is how it looks on my machine, you may see different revision numbers. (I did myself, after cloning it a few times.)

<pre> 
                    + all this is branch3  +-- r17 "latest" <= tip
                    |                     /
                    \==>     +- r13 <- r14 <-- r16 mark3
                            /             \
               branch2 => r12              +-- r15 "head1"
              ends here  /
                       r11 mark2
                       /
    r0 <- r1 <- r2 <- r3 <- r4 <- r5 <- r6 <- r7 <- r8 <= default branch
         tag1              tag2          \   mark1
                                          r9
                                           \
                                            r10 <= branch1
</pre> 

The tags, bookmarks, and branches are as labeled. The "latest" and "head1" labels aren't any of those; they're just what the commit messages on r15 and r17 say.

Testing Method 1
----------------

Okay, let's see how well method 1 works.

    ~/repo $ hg clone https://code.google.com/p/yagh-test/ yagh-test1
    requesting all changes
    adding changesets
    adding manifests
    adding file changes
    added 18 changesets with 18 changes to 2 files (+4 heads)
    updating to branch default
    2 files updated, 0 files merged, 0 files removed, 0 files unresolved

    ~/repo $ git init --bare test1.git && cd test1.git && rm hooks/*.sample
    Initialized empty Git repository in /usr/home/jim/repo/test1.git/

Those sample hooks would just distract us later.

    ~/repo/test1.git $ /usr/local/libexec/yagh/hg-fast-export.sh -r ~/repo/yagh-test1
    Error: repository has at least one unnamed head: hg r16
    git-fast-import statistics:
    ---------------------------------------------------------------------
    Alloc'd objects:       5000
    ...[output pruned]...
    ---------------------------------------------------------------------

    ~/repo/test1.git $ find .
    .
    ./refs
    ./refs/heads
    ./refs/tags
    ./hg2git-heads
    ./hg2git-marks
    ./info
    ./info/exclude
    ./branches
    ./objects
    ./objects/info
    ./objects/pack
    ./description
    ./config
    ./HEAD
    ./hooks

Uh-oh, looks like nothing got imported. That's because the `hg-fast-export` scripts didn't like the unnamed-and-untagged heads in our repository. (It identified r16 as one such, but r15 is as well. The "latest" head on branch3 *is* tagged, as "tip".) The only way to proceed here is to give these scripts the `--force` flag. Then things work ok, but we'll be missing out on some sanity checks. If you know your upstream repository will almost never have multiple heads on a single branch, then you won't need to `--force` things. Note that it's not enough that the heads be bookmarked: here the script complained about r16 even though that is bookmarked as "mark3".

    $ cd ~/repo/yagh-test1 && hg log -r16
    changeset:   16:f409556ae260
    branch:      branch3
    bookmark:    mark3
    parent:      12:c740be107432
    user:        Jim Pryor <dubiousjim@gmail.com>
    date:        Fri Jun 29 19:46:19 2012 -0400
    summary:     to be marked3

Ok, let's supply the `--force` and keep going. I'll supply two other flags to the `hg-fast-export` scripts as well, which may be useful to know:

    $ cd ~/repo/test1.git && /usr/local/libexec/yagh/hg-fast-export.sh --force -o origin2 -M master2 -r ~/repo/yagh-test1

The `-M master2` flag lets you specify what branch on the Git-side the Mercurial "default" branch should be exported to. This defaults to "master", but depending on your Git habits, it might be cognitively more natural to put it someplace else you'll be less likely to try to directly modify. The `-o origin2` flag permits you to specify a prefix for all the Git-side branches these scripts export to (including any branch specified with `-M`). We'll see how that works below. Here's the output I got. Notice there are errors for the two unnamed-and-untagged heads on branch3, but the export continues anyway.

    Error: repository has at least one unnamed head: hg r16
    Error: repository has at least one unnamed head: hg r15
    origin2/master2: Exporting full revision 1/18 with 1/0/0 added/changed/removed files
    origin2/master2: Exporting simple delta revision 2/18 with 0/1/0 added/changed/removed files
    origin2/master2: Exporting simple delta revision 3/18 with 1/0/0 added/changed/removed files
    Skip .hgtags
    ...[output pruned]...
    Exporting tag [tag1] at [hg r1] [git :2]
    Exporting tag [tag2] at [hg r4] [git :5]
    Issued 20 commands
    git-fast-import statistics:
    ---------------------------------------------------------------------
    Alloc'd objects:       5000
    ...[output pruned]...
    ---------------------------------------------------------------------

And here's what our Git repository currently looks like:

    ~/repo/test1.git $ find .
    .
    ./hg2git-mapping
    ./HEAD
    ./branches
    ./hg2git-marks
    ./hg2git-heads
    ./description
    ./objects
    ./objects/info
    ./objects/pack
    ./objects/pack/pack-f6ddcc01c237af229c6d99ed746822e4976d3b67.idx
    ./objects/pack/pack-f6ddcc01c237af229c6d99ed746822e4976d3b67.pack
    ./info
    ./info/exclude
    ./config
    ./hg2git-state
    ./refs
    ./refs/tags
    ./refs/tags/tag1
    ./refs/tags/tag2
    ./refs/heads
    ./refs/heads/origin2
    ./refs/heads/origin2/branch2
    ./refs/heads/origin2/master2
    ./refs/heads/origin2/branch1
    ./refs/heads/origin2/branch3
    ./hooks

See how it created the branches as `origin2/master2` and so on? If we left off the `-o origin2` flag they'd just be `master2` and so on. Now, even though these *look like* remote-tracking branches, they're not:

    ~/repo/test1.git $ git branch -r

    ~/repo/test1.git $ git branch
      origin2/branch1
      origin2/branch2
      origin2/branch3
      origin2/master2

But we can interact with them as if they were. Notice we have no `master` branch, so let's create one. We'll set it to track `origin2/master2`:

    ~/repo/test1.git $ git branch --track master origin2/master2
    Branch master set up to track local branch origin2/master2.

I'll point out two nice things about how this all worked. One is that our tags were imported from Mercurial: you can see them in the above file listing, or you can ask Git directly:

    ~/repo/test1.git $ git tag
    tag1
    tag2

The other nice thing is that although we got error messages about the unnamed heads, they were still imported into the Git database. Here's a handy Git alias I have in my `~/.gitconfig`:

    [alias]
    lost-commits = !git fsck --unreachable | grep commit | cut -d\\  -f3 | xargs git log --no-walk

Using that, we can ask:

    ~/repo/test1.git $ git lost-commits --oneline
    f39fb92 to be marked3
    0a861da head1

And there are our two unnamed heads from the Mercurial repository. Git might GC them after a while, though I expect they'd then be reimported again the next time we import records from Mercurial.

Let's try adding another changeset on the Mercurial side and doing the hg->git import again.

    $ cd ../yagh-test1 && hg checkout tip
    2 files updated, 0 files merged, 0 files removed, 0 files unresolved

    ~/repo/yagh-test1 $ hg summary
    parent: 17:aad9ea416809 tip
     latest
    branch: branch3
    commit: (clean)
    update: 2 new changesets, 3 branch heads (merge)

    ~/repo/yagh-test1 $ vim data

    ~/repo/yagh-test1 $ hg commit -m "post-latest"

    ~/repo/yagh-test1 $ hg log -l2
    changeset:   18:218b4ab1e286
    branch:      branch3
    tag:         tip
    user:        Jim Pryor <dubiousjim@gmail.com>
    date:        Fri Jun 29 21:10:38 2012 -0400
    summary:     post-latest

    changeset:   17:aad9ea416809
    branch:      branch3
    parent:      12:c740be107432
    user:        Jim Pryor <dubiousjim@gmail.com>
    date:        Fri Jun 29 19:47:22 2012 -0400
    summary:     latest

    $ cd ~/repo/test1.git

    ~/repo/test1.git $ /usr/local/libexec/yagh/hg-fast-export.sh --force -M master2 -o origin2 -r ~/repo/yagh-test1
    Using last hg repository "/usr/home/jim/repo/yagh-test1"
    Error: repository has at least one unnamed head: hg r16
    Error: repository has at least one unnamed head: hg r15
    origin2/branch3: Exporting simple delta revision 19/19 with 0/1/0 added/changed/removed files
    Exporting tag [tag1] at [hg r1] [git c9afde4116c377eef91f6bcad0236449e9a93c4e]
    Exporting tag [tag2] at [hg r4] [git 5cd422ec2b24b25aa1a390466325f2495b1e8e89]
    Issued 3 commands
    git-fast-import statistics:
    ---------------------------------------------------------------------
    Alloc'd objects:       5000
    ...[output pruned]...
    ---------------------------------------------------------------------

    ~/repo/test1.git $ git log --oneline -2 origin2/branch3
    df0cd1a post-latest
    bcd39c5 latest

Cool, so new commits on the Mercurial side get imported in the way we'd expect.

Besides the need to `--force` if a Mercurial named branch---or the default branch---has multiple heads, the only other downside I see to this *importing* method is that it ignores bookmarks in the Mercurial repository. Depending on how the upstream repositories you want to interact with operate, that may or may not be a problem. The folks behind the `hg-git` extension say that Mercurial bookmarks are conceptually closer to Git branches than Mercurial named branches are. (References to the latter, but not to either of the former, are hard-written into a commit and are difficult to expunge or modify. Also, commits can only belong to one Mercurial named branch at a time.) So they encourage Mercurial/Git integration based on Mercurial bookmarks rather than named branches.

However, if your upstream Mercurial repositories are structured in ways that work well with this import method, then it may suit your needs. I haven't done any performance comparisons versus the `hg-git` methods, but many users do report satisfaction using the [git-hg](https://github.com/cosmin/git-hg) frontend, which as I said is built around this import method.

The fast-export project does [note some limitations](http://repo.or.cz/w/fast-export.git/blob_plain/HEAD:/hg-fast-export.txt) on the `hg-fast-export` scripts:

    hg-fast-export supports multiple branches but only named branches with
    exaclty one head each...

As we saw, their tool complains when a branch has multiple heads. However, `--force`ing the export seemed to work ok. The notes go on:

    Otherwise commits to the tip of these heads
    within branch will get flattened into merge commits.

I didn't observe this behavior in my testing. Maybe the documentation is outdated? Or maybe I didn't understand where to look. The notes continue:

    As each git-fast-import run creates a new pack file, it may be
    required to repack the repository quite often for incremental imports
    (especially when importing a small number of changesets per
    incremental import).

So keep that in mind: if you use this backend method to pull often, you should also arrange for frequent `git-repack`ings.

These things noted, though, this method might still work well for some users who want to pull from Mercurial into Git.


Testing Method 2
----------------

*However* if you also need to push from Git back to Mercurial, then things aren't so rosy. The natural way to do this is to combine the `hg-fast-export` scripts with the Mercurial `convert` extension. (That's what the `git-hg` frontend does. If one were going to install the `hg-git` extension, one could just use that to go in both directions.)

Let's make a change on the Git side and try to push it back to Mercurial. The `test1.git` repository we created is a bare repository, so we can't modify it directly. Let's just clone it and push a change from the clone back to its origin.


    $ cd ~/repo && git clone test1.git test2 && cd test2
    Cloning into 'test2'...
    done.
    
    ~/repo/test2 $ git status
    # On branch master
    nothing to commit (working directory clean)

    ~/repo/test2 $ vim data

    ~/repo/test2 $ git add data

    ~/repo/test2 $ git commit -m "change from git"
    [master 47eab84] change from git
     1 files changed, 1 insertions(+), 0 deletions(-)

    ~/repo/test2 $ git log --oneline -2
    47eab84 change from git
    ae0b1c1 post marked1

    ~/repo/test2 $ git branch -a
    * master
      remotes/origin/HEAD -> origin/master
      remotes/origin/master
      remotes/origin/origin2/branch1
      remotes/origin/origin2/branch2
      remotes/origin/origin2/branch3
      remotes/origin/origin2/master2

    ~/repo/test2 $ git push origin                       
    Total 0 (delta 0), reused 0 (delta 0)
    To /usr/home/jim/repo/test1.git
       ae0b1c1..47eab84  master -> master

    ~/repo/test2 $ git push origin master:origin2/master2
    Counting objects: 5, done.
    Delta compression using up to 2 threads.
    Compressing objects: 100% (2/2), done.
    Writing objects: 100% (3/3), 285 bytes, done.
    Total 3 (delta 1), reused 0 (delta 0)
    Unpacking objects: 100% (3/3), done.
    To /usr/home/jim/repo/test1.git
       ae0b1c1..47eab84  master -> origin2/master2

    ~/repo/test2 $ cd ~/repo/test1.git/

    ~/repo/test1.git $ git log -2 --oneline master         
    47eab84 change from git
    ae0b1c1 post marked1

    ~/repo/test1.git $ git log -2 --oneline origin2/master2
    47eab84 change from git
    ae0b1c1 post marked1

    ~/repo/test1.git $ git show-branch --more=1 master origin2/master2
    * [master] change from git
     ! [origin2/master2] change from git
    --
    *+ [master] change from git
    *+ [master^] post marked1

Ok, so we've made a change and pushed it both to `master` and to our "hg-tracking" branch `origin2/master2`. Ideally we'd have some frontend porcelain that made that more elegant, but this is what we'd expect the end result to be. Now we want to push that change from the "hg-tracking" branch back to our clone of the Mercurial repository. If that succeeds, then our frontend porcelain could arrange for the change to be `hg push`ed back upstream.

The documentation for `convert` [describes a "branchmap" file](http://mercurial.selenic.com/wiki/ConvertExtension#A--branchmap) that lets you explicitly specify which Git branches being imported should go to which Mercurial named branches. So we'll try that out:

    $ cd ~/repo/yagh-test1

    ~/repo/yagh-test1 $ vim branchmap && cat branchmap
    origin2/master2 default
    origin2/branch1 branch1
    origin2/branch2 branch2
    origin2/branch3 branch3

    ~/repo/yagh-test1 $ hg convert --branchmap branchmap ~/repo/test1.git .
    scanning source...
    sorting...
    converting...
    17 initial commit
    16 to be tagged1
    15 Added tag tag1 for changeset d03e4e8a14b0
    14 post tag1
    13 to be marked2
    12 post marked2
    11 branch3 continues
    10 fork here
    9 latest
    8 post-latest
    7 to be tagged2
    6 Added tag tag2 for changeset 54a73ff52ed4
    5 post tag2
    4 to be marked1
    3 post marked1
    2 change from git
    1 side branch1
    0 more on branch1
    updating bookmarks

That looks promising. It imported a lot of revisions, but that's because we had never run it before. The next time we run it, it would start again from the place where it had previously finished converting. Let's see how things look:

    $ $ hg log --style=compact -l 4
    36[tip][origin2/branch1]   7d904ec96fcc   2012-06-29 19:42 -0400   dubiousjim
      more on branch1

    35:31   b172949a7241   2012-06-29 19:42 -0400   dubiousjim
      side branch1

    34[master,origin2/master2]   37b41efc0a9a   2012-06-29 21:36 -0400   dubiousjim
      change from git

    33   acc0091ce7f6   2012-06-29 19:41 -0400   dubiousjim
      post marked1

Yeah, the "change from git" showed up alright, as r34 (umm...r34? ...yeah, hold that thought for a moment). There are the funny remarks about "origin2/branch1" and "master" and so on, and sure enough, we see that the `convert` extension created bookmarks for all of these Git branches:

    $ hg bookmarks
       mark1                     10:1d8979712420
       mark2                     5:e2833a193f93
       mark3                     16:f409556ae260
       master                    34:37b41efc0a9a
       origin2/branch1           36:7d904ec96fcc
       origin2/branch2           24:3c59d8452fea
       origin2/branch3           28:8a3194ee63b3
       origin2/master2           34:37b41efc0a9a

There are those high revision numbers again. What's going on with that? We started off with a repository with 19 changesets (the 0..17 we cloned plus the "post-latest" one we added). Then we added one on the Git side. So we should now have 20 changesets. Instead we have 37. It looks like all of the reachable old Git commits (all the ancestors of the named heads in Mercurial) have been duplicated in the Mercurial repository. This is unacceptable.

Maybe there's some way to clean this all up and get it to work. I don't know. But on the face of it, this method just looks terribly unsuited to play the role of an ongoing Git/Hg bridge. Of course, that's not its intended purpose: it's *meant* for importing Git commits that the destination Mercurial repository had never seen, for example, if we were converting the Git repository into an empty Mercurial repository. But it initially looked like it might do what we need for an ongoing back-and-forth bridge. That's in fact how the `git-hg` tool uses it. But it doesn't work! We can't be polluting our Mercurial repository with all these duplicate commits everytime we push. Not to mention that our Git-created commits are descended in the history from the new copies of the old commits, rather than from the originals, as we intended.

The `convert` extension has a configuration setting `convert.hg.usebranchnames` that defaults to `true`. So far as I can tell, turning that off has no effect if you continue to specify a `--branchmap` file. I tried repeating everything we did before without the `-M` and `-o` flags to `hg-fast-export`, and without the branchmap file, but still end up getting the same duplicated commits when we `convert` the Git repository back into Mercurial.

The `convert` extension comes with a flag `--rev` that permits you to specify what revisions to import *up until*, but we want the opposite: to be able to specify what revisions not to import *before*. The extension's documentation [discusses that](http://mercurial.selenic.com/wiki/ConvertExtension#A--rev), but says you need to do this:

    The second way would be to use the splice map and say "The first commit I'm
    interested in should have 0000000000000000000000000000000000000000 as its
    parent." After the repository conversion, you can then clean the history and
    remove unwanted branches. [This will] still require downloading all
    changes, though.

Perhaps we could do something like that (only using an existing Mercurial changeset as the parent we splice onto, rather than 0000000000000000000000000000000000000000). But wow, that's a lot more work than we were expecting. And no doubt our initial efforts to get that working will be brittle and break in corner cases that didn't occur to us. Perhaps if there were no alternatives, this is what we'd have to do. But given how difficult this all looks, let's turn instead to the `hg-git` methods.

Lesson learned: **the backend method the `git-hg` tool uses to push from Git to Mercurial is not usable.** That tool does declare this functionality "experimental", but in its current implementation it's just broken. It will double your Mercurial repository every time you pull-then-push, and your new Git commits will not be descendents of any commit already in the database. As I hope the above discussion makes clear, this is not something one can fix with tweaks to the `git-hg` frontend; it's a limitation in the backend implementation that `git-hg` is relying on. So don't use `git-hg` to push to Mercurial; if you're going to use it, use it for pulling only.


Hg-git documentation
--------------------

We want next to try out the other methods of pulling and pushing from Mercurial, using the `hg-git` Mercurial extension.

A first difficulty I faced is that the documentation for this extension is [scattered](http://hg-git.github.com/) across [several](http://mercurial.selenic.com/wiki/HgGit) [sites](https://bitbucket.org/durin42/hg-git/); and each of the sites adds useful information. So I'll begin by pulling together the pieces we might use.

One version of the documentation says:

    The Hg-Git plugin can convert commits/changesets losslessly from one system
    to another, so you can push via a Mercurial repository and another Mercurial
    client can pull it. In theory, the changeset IDs should not change, although
    this may not hold true for complex histories.

That sounds good. We don't want duplicated commits with different changeset IDs, like we saw when using the `convert` extension.

Some of the documentation discusses cloning an existing Git repository into Mercurial. That's not what we'll be doing; but some of what they say may be useful anyway (I've fixed some clear mistakes):

    You can clone a Git repository from Hg by running hg clone url. For example, if you were to run

        $ hg clone git://github.com/schacon/hg-git.git

    hg-git would clone the repository down into the directory 'hg-git', then convert it to an Hg repository for you.

    If you want to clone a github repository for later pushing (or any other
    repository you access via ssh), you need to convert the ssh url to a format
    with an explicit protocol prefix. For example, the ssh url with push access

        git@github.com:schacon/hg-git.git

    would read

        git+ssh://git@github.com/schacon/hg-git.git

    (Mind the switch from colon to slash after the host!)

    Your clone command would thus look like this:

        $ hg clone git+ssh://git@github.com/schacon/hg-git.git

One version of the documentation says that when we clone a Git repository into Mercurial:

    This will also create a bookmark for each git branch, and add local tags
    default/<branch name> for each branch. This is similar to origin/<branch name>
    in git.

    When you pull from a git repository in the [paths] section of hgrc, it will
    "fast-forward" the bookmarks if the branches haven't diverged. It will also
    create local tags as above.

and that:

    When pushing to git, the following is done to determine what's pushed :

      * if there are no bookmarks and the remote repository is empty, the tip is pushed as the master branch.
      * for each branch in the remote repository, if there is a bookmark or a tag with the same name that points to a descendent of the head, then push it.
      * if there are bookmarks with no remote branch, a new branch is created. 

    The bookmarks extension is not necessary, one can work using solely local tags, but it's more convenient to use it.

The `hg-git` documentation refers several times to "the bookmarks extension" and discuss how to enable it. But bookmarks have been merged into the core of Mercurial since v1.8, released 1 March 2011.

Other parts of the documentation discuss spawning a new Git repository off of an existing Mercurial one. This sounds useful for our purposes:

    If you are starting from an existing Hg repository, you have to setup a Git
    repository somewhere that you have push access to, add it as default path or
    default-push path in your .hg/hgrc and then run hg push from within your
    project. For example:

        $ cd hg-git # (an Hg repository)
        $ # edit .hg/hgrc and add the target git url in the paths section
        $ hg push

    This will convert all your Hg data into Git objects and push them up to the Git server.

A different version of the documentation presents the process like this:

        $ cd hg-git # (a Mercurial repository)
        $ hg bookmark -r default master # make a bookmark of master for default, so a ref gets created
        $ hg push git+ssh://git@github.com/schacon/hg-git.git
        $ hg push

    This will convert all our Mercurial data into Git objects and push them up
    to the Git server. You can also put that path in the [paths] section of
    .hg/hgrc and then push to it by name.

The version of the documentation we were following first continues:

    Now that you have an Hg repository that can push/pull to/from a Git repository, you can fetch updates with hg pull.

        $ hg pull

    That will pull down any commits that have been pushed to the server in the meantime and give you a new head that you can merge in.

    Hg-Git can also be used to convert a Mercurial repository to Git. As Dulwich doesn't support local repositories yet...

We discussed this comment earlier; it seems to be out-of-date. The docs continue:

    ...the easiest way is to setup up a local SSH server. Then use the
    following commands to convert the repository (it assumes your running this in
    $HOME).

        $ mkdir git-repo; cd git-repo; git init; cd ..
        $ cd hg-repo
        $ hg bookmarks hg
        $ hg push git+ssh://localhost:git-repo

    The hg bookmark is necessary to prevent problems as otherwise hg-git pushes
    to the currently checked out branch confusing Git. This will create a branch
    named hg in the Git repository. To get the changes in master use the following
    command (only necessary in the first run, later just use git merge or rebase).

        $ cd git-repo
        $ git checkout -b master hg

    To import new changesets into the Git repository just rerun the hg push command and then use git merge or git rebase in your Git repository.

Finally, other parts of the documentation add these details:

    hg-git keeps a git repository clone for reading and updating. By default,
    the git clone is the subdirectory git in your local Mercurial repository. If
    you would like this git clone to be at the same level of your Mercurial
    repository instead (named .git), add the following to your hgrc:

        [git]
        intree = True

And:

    hg-git does not convert between Mercurial named branches and git branches
    as the two are conceptually different; instead, it uses Mercurial bookmarks to
    represent the concept of a git branch. Therefore, when translating an hg repo
    over to git, you typically need to create bookmarks to mirror all the named
    branches that you'd like to see transferred over to git. The major caveat with
    this is that you can't use the same name for your bookmark as that of the named
    branch, and furthermore there's no feasible way to rename a branch in
    Mercurial. For the use case where one would like to transfer an hg repo over to
    git, and maintain the same named branches as are present on the hg side, the
    branch_bookmark_suffix might be all that's needed. This presents a string
    "suffix" that will be recognized on each bookmark name, and stripped off as the
    bookmark is translated to a git branch:

        [git]
        branch_bookmark_suffix=_bookmark

    Above, if an hg repo had a named branch called release_6_maintenance, you
    could then link it to a bookmark called release_6_maintenance_bookmark. hg-git
    will then strip off the _bookmark suffix from this bookmark name, and create a
    git branch called release_6_maintenance. When pulling back from git to hg, the
    _bookmark suffix is then applied back, if and only if an hg named branch of
    that name exists. E.g., when changes to the release_6_maintenance branch are
    checked into git, these will be placed into the release_6_maintenance_bookmark
    bookmark on hg. But if a new branch called release_7_maintenance were pulled
    over to hg, and there was not a release_7_maintenance named branch already, the
    bookmark will be named release_7_maintenance with no usage of the suffix.

    The branch_bookmark_suffix option is ... intended for migrating legacy hg
    named branches. Going forward, an hg repo that is to be linked with a git repo
    should only use bookmarks for named branching.

There is one more relevant part of the documentation, discussing `gimport` and `gexport`; but we'll reserve that for later.

Other parts of the documentation discuss installation; we'll defer that until our general installation instructions below.

Ok, here are the tidbits I extract out of all of that:

  * pulling from Git will add local Mercurial tags `default/branchname` for each Git branch
  * *cloning* from Git will create a bookmark for each Git branch
  * pulling from Git will "fast-forward" those bookmarks if the Hg and Git branches haven't diverged

We'll have to check and see whether pulling also creates new bookmarks for Git branches that have no Mercurial correlate. The documentation seems to imply it won't.

For the time being, we'll ignore the issues about Mercurial bookmarks and named branches possibly having the same names.

With regard to pushing:

* pushing to a Git repo with branches will push Mercurial bookmarks and tags to Git branches with the same name, so long as these are fast-forward pushes

Is it only local Mercurial tags that are so handled? That's what the documentation seems to imply. Are global Mercurial tags exported to Git at all? (We'll see below: yes, they are.)

* new Git branches will be created for each Mercurial bookmark that doesn't yet have a matching Git branch

Finally:

* when there are no Mercurial bookmarks, the Mercurial `tip` is pushed into Git `master`

The documentation implies this only happens when the Git repository is empty. But what if we then push a second time: is `tip` no longer pushed? And when there are Mercurial bookmarks, is `tip` just ignored? We'll have to check and see.

Also, one part of the documentation seems to contradict the last item: it says that when there are no Mercurial bookmarks, `hg-git` will push "to the currently checked out branch" in Git, which need not be `master`.


Testing Method 3
----------------

Ok, let's try this out. We'll start over with a new clone of the upstream repository:

    $ cd ~/repo && hg clone https://code.google.com/p/yagh-test/ yagh-test3
    requesting all changes
    adding changesets
    adding manifests
    adding file changes
    added 18 changesets with 18 changes to 2 files (+4 heads)
    updating to branch default
    2 files updated, 0 files merged, 0 files removed, 0 files unresolved

    ~/repo $ git init test3 && vim yagh-test3/.hg/hgrc && cat yagh-test3/.hg/hgrc
    Initialized empty Git repository in /usr/home/jim/repo/test3/.git/
    [paths]
    default = /home/jim/repo/test3

As before, the `*.sample` hooks in the git repository are just going to distract us later, so let's delete them:

    ~/repo $ rm test3/.git/hooks/*.sample

We're going to want some additional copies of this as we proceed, so let's make them now:

    ~/repo $ hg clone yagh-test3 yagh-test4
    updating to branch default
    2 files updated, 0 files merged, 0 files removed, 0 files unresolved

    ~/repo $ cp -a test{3,4} && vim yagh-test4/.hg/hgrc && cat yagh-test4/.hg/hgrc
    [paths]
    default = /home/jim/repo/test4

    ~/repo $ cd yagh-test4 && hg bookmarks
       mark1                     7:1d8979712420
       mark2                     11:e2833a193f93
       mark3                     16:f409556ae260

Let's delete bookmark `mark3` and replace it with a local tag:

    ~/repo/yagh-test4 $ hg bookmark --delete mark3 && hg tag --local -r16 mark3

    ~/repo/yagh-test4 $ hg tags -v
    tip                               17:aad9ea416809
    mark3                             16:f409556ae260 local
    tag2                               4:54a73ff52ed4
    tag1                               1:d03e4e8a14b0

Let's make a filesystem copy of this Mercurial repository, instead of a clone, to carry over the local tag:

    $ cd ~/repo && cp -a yagh-test{4,5}

    ~/repo $ cp -a test{3,5} && vim yagh-test5/.hg/hgrc && cat yagh-test5/.hg/hgrc
    [paths]
    default = /home/jim/repo/test5

    ~/repo $ cd yagh-test5 && hg bookmarks
       mark1                     7:1d8979712420
       mark2                     11:e2833a193f93


In this version we won't have any bookmarks:

    ~/repo/yagh-test5 $ hg bookmark --delete mark1

    ~/repo/yagh-test5 $ hg bookmark --delete mark2

But we still have `mark3` as a local tag:

    ~/repo/yagh-test5 $ hg tags -v
    tip                               17:aad9ea416809
    mark3                             16:f409556ae260 local
    tag2                               4:54a73ff52ed4
    tag1                               1:d03e4e8a14b0

We'll make another copy for later:

    $ cd ~/repo && cp -a yagh-test{5,6}

OK, now let's try pushing these to our fresh Git repositories and see what happens. We'll start by pushing yagh-test5 into test5:

    ~/repo/yagh-test5 $ hg push
    pushing to /usr/home/jim/repo/test5
    exporting hg objects to git
    creating and sending data
    Unpacking objects: 100% (30/30), done.
    abort: git remote error: refs/heads/master failed to update

Whoops. What happened?

    $ cd ~/repo/test5 && find .
    .
    ./.git
    ./.git/description
    ./.git/info
    ./.git/info/exclude
    ./.git/config
    ./.git/refs
    ./.git/refs/tags
    ./.git/refs/tags/tag1
    ./.git/refs/tags/tag2
    ./.git/refs/heads
    ./.git/objects
    ./.git/objects/info
    ./.git/objects/6f
    ./.git/objects/6f/94cdc38665d4de4de49104a18a8ac921689b75
    ...[output pruned]...
    ./.git/HEAD
    ./.git/hooks
    ./.git/branches

It looks like a bunch of Mercurial commits were copied over, but when `hg-git` tried to fast-forward the `master` branch, it failed. That's because this was a fresh Git repository and the `master` ref hadn't yet been created. Let's start over with that reference in place:

    $ cd ~/repo && rm -rf test5 && cp -a test{3,5} && cd test5

    ~repo/test5 $ git commit --allow-empty -m "initial git commit"
    [master (root-commit) 260e7dc] initial git commit

    ~repo/test5 $  ls .git/refs/heads/
    master

    $ cd ~/repo/yagh-test5 && hg push
    pushing to /usr/home/jim/repo/test5
    creating and sending data
    abort: refs/heads/master changed on the server, please pull and merge before pushing

Uh-oh. It looks like `hg-git` is confused because refs/heads/master in our new destination repository isn't where it expected it to be. Let's start over with our fresh copy of `yagh-test5` as well.

    $ cd ~/repo/yagh-test6 && hg push
    pushing to /usr/home/jim/repo/test5
    exporting hg objects to git
    creating and sending data
    Unpacking objects: 100% (15/15), done.
        default::refs/tags/tag2 => GIT:2b9279f9
        default::refs/tags/tag1 => GIT:c9afde41
        default::refs/heads/master => GIT:260e7dc

Ok, that seemed to work. So it looks like, if we want to push from a Mercurial repository without any bookmarks, we should make sure that the `master` ref has been created in the destination Git repository, *before* we do any pushing. Else the push will fail and `hg-git` will get confused about the state of the Git repository.

Let's see how it worked out:

    $ cd ~/repo/test5 && git show-branch -a
    [master] initial git commit

Uh-oh, that doesn't look good. Where's all the stuff we imported in?

    ~/repo/test5 $ git log --oneline
    260e7dc initial git commit

    ~/repo/test5 $ git branch -a
    * master

And yet the tags are there:

    ~/repo/test5 $ git tag -n
    tag1            to be tagged1
    tag2            to be tagged2

    ~/repo/test5 $ git log --oneline tag1     
    c9afde4 to be tagged1
    0293f63 initial commit

And in fact all of our Mercurial commits have been imported:

    ~/repo/test5 $ git log --oneline --date-order $(git rev-list --all)
    260e7dc initial git commit
    2b9279f to be tagged2
    d94575d post tag1
    129b7eb Added tag tag1 for changeset d03e4e8a14b0
    c9afde4 to be tagged1
    0293f63 initial commit

We just can't see them because the `master` ref we created doesn't have any common ancestors with them.

Well, we could fix this by forcing the master ref to point to the latest of the Mercurial commits:

    ~/repo/test5 $ git reset --hard 2b9279f
    HEAD is now at 2b9279f to be tagged2

Then we can leave the "initial git commit" to be GC'd. In hindsight, maybe we could have just cleaned up after the failed `hg push` from yagh-test5 in the same way. And in fact that does bring us to roughly this same point; except in that case, we have a `master` bookmark created on the Mercurial side pointing to the Mercurial `tip`. And that could mess up later pushes, since the `tip` needn't be on the default branch, which is the only branch `hg-git` is pushing over.

Let's go back to the Mercurial repository and see how things stand:

    $ cd ~/repo/yagh-test6 && hg push
    pushing to /usr/home/jim/repo/test5
    creating and sending data
        default::refs/tags/tag2 => GIT:2b9279f9
        default::refs/tags/tag1 => GIT:c9afde41
        default::refs/heads/master => GIT:260e7dc

Pushing a second time works fine. However, how much of our Mercurial tree was pushed?

    $ cd ~/repo/test5 && git log --oneline --date-order
    2b9279f to be tagged2
    d94575d post tag1
    129b7eb Added tag tag1 for changeset d03e4e8a14b0
    c9afde4 to be tagged1
    0293f63 initial commit

    $ cd ~/repo/yagh-test6 && hg log -r 'sort(branch(default),-date)' --template 'r{rev} {node|short} {tags}: {desc}\n'
    r8 9f5b5d581bed : post marked1
    r7 1d8979712420 : to be marked1
    r6 51ace10a7ac3 : post tag2
    r5 0d91ce7d9df4 : Added tag tag2 for changeset 54a73ff52ed4
    r4 54a73ff52ed4 tag2: to be tagged2
    r3 664d889398ea : post tag1
    r2 867f59552a9a : Added tag tag1 for changeset d03e4e8a14b0
    r1 d03e4e8a14b0 tag1: to be tagged1
    r0 faa28ab8d90e : initial commit

It looks like everything past `tag2` wasn't pushed. However, once we we start adding revisions to `default` branch, then its head will be tagged (with `tip`), and perhaps we'd *then* get the rest of it pushed over to Git. Even if that works, though, it's looking like more and more trouble to use `hg-git` without Mercurial bookmarks.

OK, let's create a new commit on the Mercurial side and push it. We have to be sure we do this on the default branch, since as I said, that's the only branch that `hg-git` is pushing (in this mode of operation).

    ~/repo/yagh-test6 $ hg checkout -r8
    0 files updated, 0 files merged, 0 files removed, 0 files unresolved

    ~/repo/yagh-test6 $ vim data && hg commit -m "latest on default"

    ~/repo/yagh-test6 $ hg parents
    changeset:   18:e1c4d4ffeba8
    tag:         tip
    parent:      8:9f5b5d581bed
    user:        Jim Pryor <dubiousjim@gmail.com>
    date:        Sat Jun 30 12:23:20 2012 -0400
    summary:     latest on default

    ~/repo/yagh-test6 $ hg push
    pushing to /usr/home/jim/repo/test5
    exporting hg objects to git
    creating and sending data
        default::refs/tags/tag2 => GIT:2b9279f9
        default::refs/tags/tag1 => GIT:c9afde41
        default::refs/heads/master => GIT:2b9279f9

    $ cd ~/repo/test5 && git log --oneline --date-order $(git rev-list --all)
    2b9279f to be tagged2
    d94575d post tag1
    129b7eb Added tag tag1 for changeset d03e4e8a14b0
    c9afde4 to be tagged1
    0293f63 initial commit

That doesn't look good.

    $ cd ~/repo/yagh-test6 && hg push -rtip
    pushing to /usr/home/jim/repo/test5
    creating and sending data
    abort: revision e1c4d4ffeba8 cannot be pushed since it doesn't have a ref

    ~/repo/yagh-test6 $ hg tags -v
    tip                               18:e1c4d4ffeba8
    mark3                             16:f409556ae260 local
    tag2                               4:54a73ff52ed4
    default/master                     4:54a73ff52ed4
    tag1                               1:d03e4e8a14b0

    ~/repo/yagh-test6 $ hg tag --local -rtip default/master
    abort: tag 'default/master' already exists (use -f to force)

    ~/repo/yagh-test6 $ hg tag -f --local -rtip default/master

    ~/repo/yagh-test6 $ hg tags -v
    tip                               18:e1c4d4ffeba8
    mark3                             16:f409556ae260 local
    tag2                               4:54a73ff52ed4
    default/master                     4:54a73ff52ed4 local
    tag1                               1:d03e4e8a14b0

Hey, it didn't update. It's still at r4. That's because the `default/master` tag is managed by the `hg-git` extension, not by the ordinary tags mechanism. Well, let's clean up our `.hg/localtags` file and try something else:

    ~/repo/yagh-test6 $ vim .hg/localtags && cat .hg/localtags
    f409556ae260823778413762e93f7aa6e6d16ad5 mark3

    ~/repo/yagh-test6 $ hg tag --local -rtip master && hg tag --local -rtip newbranch && hg tags -v
    tip                               18:e1c4d4ffeba8
    master                            18:e1c4d4ffeba8 local
    newbranch                         18:e1c4d4ffeba8 local
    mark3                             16:f409556ae260 local
    tag2                               4:54a73ff52ed4
    default/master                     4:54a73ff52ed4
    tag1                               1:d03e4e8a14b0

Now let's see if this works:

    ~/repo/yagh-test6 $ $ hg push
    pushing to /usr/home/jim/repo/test5
    creating and sending data
        default::refs/tags/tag2 => GIT:2b9279f9
        default::refs/tags/tag1 => GIT:c9afde41
        default::refs/heads/master => GIT:2b9279f9

    $ cd ~/repo/test5 && git rev-list --all | wc -l
           5

Still no joy. Lesson learned: trying to use `hg-git` without bookmarks is a pain in the rear.

OK, let's go back to yagh-test4, then. To remind ourselves, this has both some bookmarks and some local and global tags.

    $ cd ~/repo/yagh-test4 && hg bookmarks
       mark1                     7:1d8979712420
       mark2                     11:e2833a193f93

    ~/repo/yagh-test4 $ hg tags -v
    tip                               17:aad9ea416809
    mark3                             16:f409556ae260 local
    tag2                               4:54a73ff52ed4
    tag1                               1:d03e4e8a14b0

Let's see if pushing works:

    ~/repo/yagh-test4 $ hg push
    pushing to /usr/home/jim/repo/test4
    exporting hg objects to git
    creating and sending data
    Unpacking objects: 100% (27/27), done.
        default::refs/heads/mark2 => GIT:c071dc28
        default::refs/tags/tag2 => GIT:2b9279f9
        default::refs/tags/tag1 => GIT:c9afde41
        default::refs/heads/mark1 => GIT:9a989e35

    $ cd ~/repo/test4 &&  git log --oneline --date-order $(git rev-list --all)
    c071dc2 to be marked2
    9a989e3 to be marked1
    9e12910 post tag2
    9ee1d72 Added tag tag2 for changeset 54a73ff52ed4
    2b9279f to be tagged2
    d94575d post tag1
    129b7eb Added tag tag1 for changeset d03e4e8a14b0
    c9afde4 to be tagged1
    0293f63 initial commit

Everything got transferred over except revisions 8-10, and revisions 12-17 in our Mercurial repository:

<pre> 
                    + all this is branch3  +-- r17 "latest" <= tip
                    |                     /
                    \==>     +- r13 <- r14 <-- r16 mark3
                            /             \
               branch2 => r12              +-- r15 "head1"
              ends here  /
                        .  mark2
                       /
     . <-  . <-  . <-  . <-  . <-  . <-  . <-  . <- r8 <= default branch
         tag1              tag2          \   mark1
                                          r9
                                           \
                                            r10 <= branch1
</pre> 

And those are just the revisions that are ahead of any bookmark. If you'll recall, the `hg-git` documentation said that it would also transfer over local tags, but we observe here that `mark3`, which we've converted to a local tag, and the chain leading up to it, were not transferred.

Hence it looks like you've really got to rely on bookmarks to control what gets pushed.

In general, we shouldn't assume that the upstream Mercurial repositories will cooperate though. They may or may not use bookmarks themselves. If they do, we'll want to download them and track them in our Git clones. The upstream repositories may or may not use named branches. If they do, we'll want to download those and track them too. So we'll make use of that `git.branch_bookmark_suffix` setting mentioned in the `hg-git` documentation. We'll have our frontend porcelain make sure that every Mercurial named branch has a correlated bookmark that tracks its tipmost head, so that these all get pushed to Git. (We won't do anything about nodes on the branch that aren't ancestors of the branch's tipmost head. But in principle, one could could check for multiple heads and maintain a set of bookmarks that track them, too.)

OK, let's apply this to our original clone of the upstream Mercurial repository:

    $ cd ~/repo/yagh-test3 && hg bookmarks
       mark1                     7:1d8979712420
       mark2                     11:e2833a193f93
       mark3                     16:f409556ae260

    ~/repo/yagh-test3 $ hg tags -v
    tip                               17:aad9ea416809
    tag2                               4:54a73ff52ed4
    tag1                               1:d03e4e8a14b0

    ~/repo/yagh-test3 $ hg branches --active
    branch3                       17:aad9ea416809
    branch1                       10:d80cc7a33529
    default                        8:9f5b5d581bed

We'll create bookmarks to track branch1 and branch3:

    ~/repo/yagh-test3 $ hg bookmark -rbranch1 branch1_bookmark

    ~/repo/yagh-test3 $ hg bookmark -rbranch3 branch3_bookmark

    ~/repo/yagh-test3 $ vim .hg/hgrc && cat .hg/hgrc
    [paths]
    default = /home/jim/repo/test3
    [git]
    branch_bookmark_suffix = _bookmark

Now let's see if pushing works:

    ~/repo/yagh-test3 $ hg push
    pushing to /home/jim/repo/test3
    exporting hg objects to git
    creating and sending data
    Unpacking objects: 100% (48/48), done.
        default::refs/heads/mark3 => GIT:bb0b2c00
        default::refs/heads/mark2 => GIT:c071dc28
        default::refs/tags/tag2 => GIT:2b9279f9
        default::refs/tags/tag1 => GIT:c9afde41
        default::refs/heads/mark1 => GIT:9a989e35
        default::refs/heads/branch1 => GIT:b4e42711
        default::refs/heads/branch3 => GIT:911326b6

    $ cd ~/repo/test3 && git log --oneline --date-order $(git rev-list --all)
    911326b latest
    bb0b2c0 to be marked3
    acf74ed fork here
    57a866b branch3 continues
    2c67b58 post marked2
    c071dc2 to be marked2
    b4e4271 more on branch1
    fcd19dd side branch1
    9a989e3 to be marked1
    9e12910 post tag2
    9ee1d72 Added tag tag2 for changeset 54a73ff52ed4
    2b9279f to be tagged2
    d94575d post tag1
    129b7eb Added tag tag1 for changeset d03e4e8a14b0
    c9afde4 to be tagged1
    0293f63 initial commit

This pushed everything except revisions 8 and 15.

<pre>
                    + all this is branch3  +--  .  "latest" <= tip, also branch3_bookmark
                    |                     /
                    \==>     +-  .  <-  .  <--  .  mark3
                            /             \
               branch2 =>  .               +-- r15 "head1"
              ends here  /
    also branch2_book....  mark2
                       /
     . <-  . <-  . <-  . <-  . <-  . <-  . <-  . <- r8 <= default branch
         tag1              tag2          \   mark1
                                          . 
                                           \
                                            .   <= branch1
                                                   also branch1_bookmark
</pre>

And that makes sense, because r8 and r15 are exactly the revisions beyond any of our bookmarks. (We haven't marked the tip of the default branch with a bookmark, I suppose we should do that, too.)

What branches exist on the git side?

    ~/repo/test3 $ git branch -r

    ~/repo/test3 $ git branch
      branch1
      branch3
      mark1
      mark2
      mark3

Notice there's no `master` branch. Let's make one.

    ~/repo/test3 $ git branch master mark1

    ~/repo/test3 $ git branch
      branch1
      branch3
      mark1
      mark2
      mark3
    * master

Let's try adding some more commits in Mercurial and seeing if they get pushed over properly:

    $ cd ~/repo/yagh-test3 && hg checkout -C -rbranch1_bookmark
    0 files updated, 0 files merged, 0 files removed, 0 files unresolved

    ~/repo/yagh-test3 $ vim data && hg commit -m "latest on branch1"

    ~/repo/yagh-test3 $ hg parents
    changeset:   18:f4ae4285230c
    branch:      branch1
    bookmark:    branch1_bookmark
    tag:         tip
    parent:      10:d80cc7a33529
    user:        Jim Pryor <dubiousjim@gmail.com>
    date:        Sat Jun 30 14:57:51 2012 -0400
    summary:     latest on branch1

Since we checked out the `branch1_bookmark` directly, it advanced when we committed to the new head on branch1. However we can't rely on that always happening: if we had checked out `-rbranch1` or `-r10`, for instance, the `branch1_bookmark` wouldn't have been updated---even though these were all the same node. So in general, our frontend porcelain will have to make sure that the branch-tracking bookmarks are pointing to the branch heads whenever we push.

    ~/repo/yagh-test3 $ hg checkout -r8

    ~/repo/yagh-test3 $ vim data && hg commit -m "latest on default"

    ~/repo/yagh-test3 $ hg parents
    changeset:   19:75101cc9c3ef
    tag:         tip
    parent:      8:9f5b5d581bed
    user:        Jim Pryor <dubiousjim@gmail.com>
    date:        Sat Jun 30 14:58:35 2012 -0400
    summary:     latest on default

    ~/repo/yagh-test3 $ hg push
    pushing to /home/jim/repo/test3
    exporting hg objects to git
    creating and sending data
    Unpacking objects: 100% (4/4), done.
        default::refs/heads/branch1_bookmark => GIT:71a50a04
        default::refs/heads/mark3 => GIT:bb0b2c00
        default::refs/heads/mark2 => GIT:c071dc28
        default::refs/tags/tag2 => GIT:2b9279f9
        default::refs/tags/tag1 => GIT:c9afde41
        default::refs/heads/mark1 => GIT:9a989e35
        default::refs/heads/branch3_bookmark => GIT:911326b6
        default::refs/heads/master => GIT:9a989e35


    $ cd ~/repo/test3 && git log -2 --oneline --date-order $(git rev-list --all)
    71a50a0 latest on branch1
    911326b latest

    ~/repo/test3 $ git rev-list --all | wc -l
          17

Our r18 got pushed to Git, because it was at or behind a bookmark, but r19 didn't, even though it was the `tip` of the Mercurial repository and we had created a `master` branch in the Git repository.

Notice that `hg-git` creates some special Mercurial tags for us to track the state of the Git repository:

    $ cd ~/repo/yagh-test3 && hg tags -v
    tip                               19:75101cc9c3ef
    default/branch1_bookmark          18:f4ae4285230c
    default/branch3_bookmark          17:aad9ea416809
    default/mark3                     16:f409556ae260
    default/mark2                     11:e2833a193f93
    default/master                     7:1d8979712420
    default/mark1                      7:1d8979712420
    tag2                               4:54a73ff52ed4
    tag1                               1:d03e4e8a14b0


These `default/*` tags aren't stored in *either* `.hgtags` *or* in `.hg/localtags`, but in a special `hg-git` metadata file (specifically, `.hg/git-remote-refs`).

This is all working pretty well. Let's try adding a commit from the Git side, and pulling it back into Mercurial.

    $ cd ~/test3 && git reset --hard master
    HEAD is now at 9a989e3 to be marked1

    ~/test3 $ vim data && git add data && git commit -m "added in git"
    [master 9284712] added in git
     1 files changed, 1 insertions(+), 0 deletions(-)

    ~/test3 $ git show-branch master mark1
    * [master] added in git
     ! [mark1] to be marked1
    --
    *  [master] added in git
    *+ [mark1] to be marked1

    ~/test3 $ git co mark1
    Switched to branch 'mark1'

    ~/test3 $ git merge master
    Updating 9a989e3..9284712
    Fast-forward
     data |    1 +
     1 files changed, 1 insertions(+), 0 deletions(-)

    ~/test3 $ git co -b newbranch master
    Switched to a new branch 'newbranch'

    ~/test3 $ vim data && git add data && git commit -m "added to newbranch"
    [newbranch d56a467] added to newbranch
     1 files changed, 1 insertions(+), 0 deletions(-)

    ~/test3 $ git co master
    Switched to branch 'master'

    ~/test3 $ vim data && git add data && git commit -m "added more to master"
    [master bf55acc] added more to master
     1 files changed, 1 insertions(+), 0 deletions(-)

OK, so now we've advanced the `mark1` and `master` branches, and added a new branch besides. Let's pull this into Mercurial and see what happens:

    $ cd ../yagh-test3 && hg pull
    pulling from /home/jim/repo/test3
    importing git objects into hg
    (run 'hg heads' to see heads, 'hg merge' to merge)

    ~/repo/yagh-test3 $ hg log -l4 --template 'r{rev} {node|short} {tags}: {desc}\n'
    r22 5acd3b5efe61 default/master tip: added more to master
    r21 351851ece6e1 default/newbranch: added to newbranch
    r20 6bdb2775b948 default/mark1: added in git
    r19 75101cc9c3ef : latest on default

All three of the commits from Git got pulled in. Moreover our bookmarks were updated, and a new bookmark was created for the new Git branch:

    ~/repo/yagh-test3 $ hg bookmarks
       master                    22:5acd3b5efe61
       newbranch                 21:351851ece6e1
       mark1                     20:6bdb2775b948
       ...[output pruned]...

The `hg-git`-managed tags were updated as well:

    ~/repo/yagh-test3 $ hg tags
    tip                               22:5acd3b5efe61
    default/master                    22:5acd3b5efe61
    default/newbranch                 21:351851ece6e1
    default/mark1                     20:6bdb2775b948
    ...[output pruned]...

This all seems to be working as expected. The only awkwardness I see is that these bookmarks and `hg-git`-managed tags seem to overlap in functionality. Also, all of our Git repository is getting pulled in; there's no division between local and hg-tracking branches. But these are things a frontend porcelain can take care of.

The `hg-git` seems to dislike pushing to the Git `master` branch, even if we update the `master` bookmark on the Mercurial side:

    ~/repo/yagh-test3 $ hg up -C master
    0 files updated, 0 files merged, 0 files removed, 0 files unresolved

    ~/repo/yagh-test3 $ vim data && hg commit -m "advance master"   

    ~/repo/yagh-test3 $ hg parents
    changeset:   23:21c8a3d179f7
    bookmark:    master
    tag:         tip
    user:        Jim Pryor <dubiousjim@gmail.com>
    date:        Sat Jun 30 15:20:05 2012 -0400
    summary:     advance master

    ~/repo/yagh-test3 $ hg push
    pushing to /home/jim/repo/test3
    exporting hg objects to git
    creating and sending data
    Unpacking objects: 100% (4/4), done.
    abort: git remote error: refs/heads/master failed to update

but that's just because we had the `master` branch checked out. If we instead check out some other branch, we can push to master just fine:

    $ cd ~/test3 && git co mark1 && cd ~/repo/yagh-test3 && hg push
    Switched to branch 'mark1'
    pushing to /home/jim/repo/test3
    creating and sending data
    Unpacking objects: 100% (4/4), done.
        default::refs/heads/branch1_bookmark => GIT:71a50a04
        default::refs/heads/mark3 => GIT:bb0b2c00
        default::refs/heads/newbranch => GIT:d56a467e
        default::refs/heads/mark2 => GIT:c071dc28
        default::refs/tags/tag2 => GIT:2b9279f9
        default::refs/tags/tag1 => GIT:c9afde41
        default::refs/heads/mark1 => GIT:92847126
        default::refs/heads/branch3_bookmark => GIT:911326b6
        default::refs/heads/master => GIT:83feef0e

    $ cd ~/test2 && $ git log -2 --oneline --date-order $(git rev-list --all)
    83feef0 advance master
    bf55acc added more to master


Testing Method 4
----------------

The `hg-git` documentation describes a different mode of operation for the extension, using the commands `hg gexport` and `hg gimport` instead of `hg push` and `hg pull`. I suspect there's no good reason to use these, now that it's possible to `hg push` and `hg pull` to git repositories stored locally. But for completeness, let's check out how these work too.

Here is [the relevant part of the `hg-git` documentation](http://mercurial.selenic.com/wiki/HgGit):

    Using hg-git to interact with a hg repository with git

    TODO: this section is outdated (references to master branch and exportbranch config)

    You can create a local .git repository like this:

    Editr the .hg/hgrc (or your ~/.hgrc if you want to make this the default):

    [git]
    intree=1

    Then do the following from in the hg repository:

    hg gexport

    This will create a .git repository in the working directory (alongside the .hg directory) that you can interact with like any regular git repository. If you have made commits in the git repository and want to convert them to hg commits, first make sure the changes you want are on the master branch, then do:

    hg gimport

    This will put your changes on top of the current hg tip.

    Optionally you can change your hgrc to include an exportbranch statement:

    [git]
    intree=1
    exportbranch=refs/heads/from-hg

    This will cause 'hg gexport' to update the 'from-hg' branch, instead of the master branch, so that your changes will not be lost even if you work on the master branch.


I went through all of the steps from the preceding section with yagh-test5, yagh-test4, and so on, substituting `hg gexport` for `hg push` and `hg gimport` for `hg pull`. Here is what the `.hg/hgrc` file I used:

    [git]
    intree=1
    exportbranch=refs/heads/from-hg
    branch_bookmark_suffix=_bookmark

Things seemed to act pretty much the same, except that `hg-git` didn't create all those `default/*` tags. It seems to do that only when pushing and pulling.

Also, the `from-hg` branch seems to be ignored, even if we manually create it. The Mercurial `tip` is never automatically copied, but only when some bookmark happens to point to it. (If any bookmark is "active" then it will track the `tip` as you commit to it. See the Mercurial documentation.)

I'm guessing that the `git.exportbranch` setting is obsolete and is no longer honored. And indeed, checking their git log we see an entry on 23 June 2009:

    Drop importbranch/exportbranch options (exportbranch was really broken)

Plus "exportbranch" does not appear anywhere in the `hg-git` source. I wish these guys would keep their documentation more up-to-date.

In the course of all this, I noticed that new branches on the Git side only seem to get corresponding bookmarks created for them on the Mercurial side if they have new commits, not already in the Mercurial database. I expect this holds for `hg pull`ing, too, not just for `hg import`ing.


Summary
-------

OK, so the `hg-git` extension seems to work pretty well. We just have to make sure we have bookmarks tracking all of the heads on the Mercurial side that we want to push or export to Git. At this point in time, there doesn't seem to be much difference in functionality between `hg push`ing and `hg gexport`ing.


Designing a nice frontend
-------------------------

TODO
