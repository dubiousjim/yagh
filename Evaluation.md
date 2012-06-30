Using Git to interact with upstream Mercurial repositories
==========================================================

Backends
--------

There are a couple different backend methods one can use to drive a Git/Mercurial bridge, and then some additional choices one can make about packaging those backends for day-to-day use. (In git-speak, what "porcelain" to install on top of them.)

Before we sort out our frontend choices, though, we've got to settle which backend engines we're going to use. Here are the options.

1. `git fast-import` is a component in the standard Git distribution that imports text-serialized repositories. There is another component `git fast-export` that serializes Git repositories to the needed format; but what we need is a way to serialize *Mercurial* repositories into that format. Someone has in fact made that; it's available as the `hg-fast-export` scripts (`hg-fast-export.py`, `hg-fast-export.sh`, and `hg2git.py`) that are in the [fast-export project](http://repo.or.cz/w/fast-export.git). (That project also has some `hg-reset` scripts that I don't yet understand; and also some scripts for interacting with Subversion.)
        So these `hg-fast-export` scripts provide a way to serialize a Mercurial repository, and we can pipe the result into `git fast-import`. That's one way to go from hg->git.

2. How about the reverse direction, from git->hg? One way to do this is with the `convert` extension for Mercurial. This already comes with the standard Mercurial distribution, though it's not enabled by default. No problem, though: whatever frontend porcelain we build can just explicitly enable it for the Mercurial repos we use.
        This extension is able to keep track of conversions that it has already made into a Mercurial repository, so that later conversions can be incremental. However, as we'll see below, there are severe limits to how well this works when we combine it with hg->git exports going in the other direction.

3. A different Mercurial extension is `hg-git`. This *isn't* part of the standard Mercurial distribution, but needs to be installed separately. As with the `convert` extension, our frontend porcelain can take care of enabling this extension in the repositories where we're going to use it, so the user doesn't need to make it enabled globally. She just needs to have it installed.
        Be sure to note the difference between the `hg-git` Mercurial extension, and `git-hg`, which is a frontend tool providing Git/Hg integration using Methods 1 and 2 described above (that is, this tool doesn't even use `hg-git`).
        The documentation for the `hg-git`  extension describes three different modes of operation. The first involves cloning a Mercurial repository from an existing upstream Git repository. That doesn't fit our needs; it's instead what someone has to do who wants to *use Mercurial to interact with Git-based projects.* We're interested in the reverse. The second mode described involves starting with a Mercurial repository, spawning a Git repository off of *it*, and then interacting with that Git repository just as in the first method. This is a method we could use. We will call it our method 3. It would permit going in both directions: both pulling from Mercurial into Git and pushing back.
        The documentation for `hg-git` says that this method can't be used with *local* Git repositories because ["Dulwich doesn't support local repositories yet"]
(https://bitbucket.org/durin42/hg-git/). They say you have to speak to the Git repository over a network (though it could simply be a network connection to localhost). However, on my machine I'm not encountering any such limitations. It looks like in recent versions of these tools using a local Git repository, specified by a plain old pathname, works fine.


4. I said that the documentation for `hg-git` describes three modes of operation. The last of these provides a different way we could use this extension. This involves, not pushing and pulling to a Git repository that may be (but needn't be) remote, but rather `gexport`ing and `gimport`ing to a local Git repository. The default behavior is to `gexport` and `gimport` to a bare Git repository hidden in the `.hg` folder, but in fact we can arrange for that repository to be located anywhere and it needn't be left bare. One of the existing frontends has this Git repository sharing its working directory with the local Mercurial repository.


Now there are details to work out about which parts of the Mercurial repository we're going to synch to Git: the tip of the default branch for sure, but what about other named branches? what about bookmarks from upstream? what about tags? And what parts of Git are we going to synch to Hg: which branches and how will they be identified in Mercurial? and again, what about tags?

But as we think about those details, let's also begin exploring what basic constraints these different backends impose. That may affect the decisions we make about what gets synched with what.


I created a test Mercurial repository that you can clone from <https://dubiousjim@code.google.com/p/yagh-test/>. This is a small repository displaying a variety of   features: it has several named branches, one of them "inactive" and another with multiple heads. There are also some bookmarks already in the upstream repository, and some committed tags. Here is how it looks on my machine (perhaps the revision numbers could be different when you clone it).

    
                                           +-- r17 "latest" <= tip
                    all this is branch3   /
                             +- r13 <- r14 <-- r16 mark3
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

The tags, bookmarks, and branches are as indicated. The "latest" and "head1" labels aren't any of those; they're just what the commit messages on r15 and r17 say.

Testing Methods 1 and 2
-----------------------

Okay, let's see how well method 1 works.

    ~/repo $ hg clone https://dubiousjim@code.google.com/p/yagh-test/ yagh-test1
    requesting all changes
    adding changesets
    adding manifests
    adding file changes
    added 18 changesets with 18 changes to 2 files (+4 heads)
    updating to branch default
    2 files updated, 0 files merged, 0 files removed, 0 files unresolved

    ~/repo $ git init --bare test1.git && cd test1.git && rm hooks/*.sample
    Initialized empty Git repository in /usr/home/jim/repo/test1.git/

Those sample hooks would just be distracting later.

    ~/repo/test1.git $ /usr/local/libexec/yagh/hg-fast-export.sh -r ~/repo/yagh-test1
    Error: repository has at least one unnamed head: hg r16
    git-fast-import statistics:
    ---------------------------------------------------------------------
    Alloc'd objects:       5000
    Total objects:            0 (         0 duplicates                  )
          blobs  :            0 (         0 duplicates          0 deltas of          0 attempts)
          trees  :            0 (         0 duplicates          0 deltas of          0 attempts)
          commits:            0 (         0 duplicates          0 deltas of          0 attempts)
          tags   :            0 (         0 duplicates          0 deltas of          0 attempts)
    Total branches:           0 (         0 loads     )
          marks:           1024 (         0 unique    )
          atoms:              0
    Memory total:          2282 KiB
           pools:          2048 KiB
         objects:           234 KiB
    ---------------------------------------------------------------------
    pack_report: getpagesize()            =       4096
    pack_report: core.packedGitWindowSize = 1073741824
    pack_report: core.packedGitLimit      = 8589934592
    pack_report: pack_used_ctr            =          0
    pack_report: pack_mmap_calls          =          0
    pack_report: pack_open_windows        =          0 /          0
    pack_report: pack_mapped              =          0 /          0
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

Uh-oh, looks like nothing got imported. That's because the `hg-fast-export` scripts didn't like the unnamed heads in our repository (it identified r16 as one such, but r15 is as well). The only way to proceed here is to give these scripts the `--force` flag. Then things work ok, but we'll be missing out on some sanity checks. If you know your upstream repository will almost never have multiple heads on a single branch, then you don't need to worry about this. Note that it's not enough that the heads be bookmarked: here the script complained about r16 even though that is bookmarked as "mark3".

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

The `-M master2` flag lets you specify what branch on the Git-side the Mercurial "default" branch should be exported to. This defaults to "master", but depending on your Git habits, it might be cognitively more natural to put it someplace else you'll be less likely to try to directly modify. The `-o origin2` flag permits you to specify a prefix for all the Git-side branches these scripts export to (including any branch specified with `-M`). We'll see how that works below. Here's the output I got. Notice there are errors for the two untagged heads on branch3, but the export continues anyway. (The "latest" head on branch3 *is* tagged, as "tip".)

    Error: repository has at least one unnamed head: hg r16
    Error: repository has at least one unnamed head: hg r15
    origin2/master2: Exporting full revision 1/18 with 1/0/0 added/changed/removed files
    origin2/master2: Exporting simple delta revision 2/18 with 0/1/0 added/changed/removed files
    origin2/master2: Exporting simple delta revision 3/18 with 1/0/0 added/changed/removed files
    Skip .hgtags
    origin2/master2: Exporting simple delta revision 4/18 with 0/1/0 added/changed/removed files
    origin2/master2: Exporting simple delta revision 5/18 with 0/1/0 added/changed/removed files
    origin2/branch2: Exporting simple delta revision 6/18 with 0/1/0 added/changed/removed files
    origin2/master2: Exporting simple delta revision 7/18 with 0/1/0 added/changed/removed files
    Skip .hgtags
    origin2/branch2: Exporting simple delta revision 8/18 with 0/1/0 added/changed/removed files
    origin2/master2: Exporting simple delta revision 9/18 with 0/1/0 added/changed/removed files
    origin2/branch3: Exporting simple delta revision 10/18 with 0/1/0 added/changed/removed files
    origin2/master2: Exporting simple delta revision 11/18 with 0/1/0 added/changed/removed files
    origin2/branch1: Exporting simple delta revision 12/18 with 0/1/0 added/changed/removed files
    origin2/branch3: Exporting simple delta revision 13/18 with 0/1/0 added/changed/removed files
    origin2/master2: Exporting simple delta revision 14/18 with 0/1/0 added/changed/removed files
    origin2/branch1: Exporting simple delta revision 15/18 with 0/1/0 added/changed/removed files
    origin2/branch3: Exporting simple delta revision 16/18 with 0/1/0 added/changed/removed files
    origin2/branch3: Exporting simple delta revision 17/18 with 0/1/0 added/changed/removed files
    origin2/branch3: Exporting simple delta revision 18/18 with 0/1/0 added/changed/removed files
    Exporting tag [tag1] at [hg r1] [git :2]
    Exporting tag [tag2] at [hg r4] [git :5]
    Issued 20 commands
    git-fast-import statistics:
    ---------------------------------------------------------------------
    Alloc'd objects:       5000
    Total objects:           50 (         0 duplicates                  )
          blobs  :           16 (         0 duplicates         13 deltas of         14 attempts)
          trees  :           16 (         0 duplicates          0 deltas of         16 attempts)
          commits:           18 (         0 duplicates          0 deltas of          0 attempts)
          tags   :            0 (         0 duplicates          0 deltas of          0 attempts)
    Total branches:           6 (         4 loads     )
          marks:           1024 (        18 unique    )
          atoms:              1
    Memory total:          2344 KiB
           pools:          2110 KiB
         objects:           234 KiB
    ---------------------------------------------------------------------
    pack_report: getpagesize()            =       4096
    pack_report: core.packedGitWindowSize = 1073741824
    pack_report: core.packedGitLimit      = 8589934592
    pack_report: pack_used_ctr            =         42
    pack_report: pack_mmap_calls          =         19
    pack_report: pack_open_windows        =          1 /          1
    pack_report: pack_mapped              =       4158 /       4158
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

But we can interact with them as if they were. Notice we have no `master` branch, so let's create one. We'll set it to track `origin2/master2` so we can push and pull from there:

    ~/repo/test1.git $ git branch --track master origin2/master2
    Branch master set up to track local branch origin2/master2.

Now I'll point out two nice things about how this all worked. One is that our tags were imported from Mercurial: you can see them in the above file listing, or you can ask Git directly:

    ~/repo/test1.git $ git tag
    tag1
    tag2

The other nice thing is that although we got error messages about the unnamed heads, they were still imported into the Git database. Here's a handy Git alias I have in my `~/.gitconfig`:

    $ git config --global --get alias.lost-commits
    !sh -c 'git fsck --unreachable | grep commit | cut -d\  -f3 | xargs git log --no-walk $*' -- git-log

Using that, we can ask:

    ~/repo/test1.git $ git lost-commits --oneline
    f39fb92 to be marked3
    0a861da head1

And there are the two unnamed heads from the Mercurial repository. Git might GC them after a while, though I expect they'd then be reimported again the next time we import records from Mercurial.

Let's try adding another changeset on the Mercurial side and doing the hg->git import again.

    $ cd ../yagh-test1 && hg up tip
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
    Total objects:            3 (         0 duplicates                  )
          blobs  :            1 (         0 duplicates          0 deltas of          1 attempts)
          trees  :            1 (         0 duplicates          0 deltas of          1 attempts)
          commits:            1 (         0 duplicates          0 deltas of          0 attempts)
          tags   :            0 (         0 duplicates          0 deltas of          0 attempts)
    Total branches:           3 (         1 loads     )
          marks:           1024 (         1 unique    )
          atoms:              1
    Memory total:          2344 KiB
           pools:          2110 KiB
         objects:           234 KiB
    ---------------------------------------------------------------------
    pack_report: getpagesize()            =       4096
    pack_report: core.packedGitWindowSize = 1073741824
    pack_report: core.packedGitLimit      = 8589934592
    pack_report: pack_used_ctr            =          5
    pack_report: pack_mmap_calls          =          2
    pack_report: pack_open_windows        =          2 /          2
    pack_report: pack_mapped              =       4479 /       4479
    ---------------------------------------------------------------------

    ~/repo/test1.git $ git log --oneline -2 origin2/branch3
    df0cd1a post-latest
    bcd39c5 latest

Ok, cool, so new commits on the Mercurial side get imported in the way we'd expect.

Besides the need to `--force` if a Mercurial named branch---or the default branch---has multiple heads, the only other downside I see to this *importing* method is that it ignores bookmarks in the Mercurial repository. Depending on how the upstream repositories you want to interact with operate, that may or may not be a problem. The folks behind the `hg-git` extension say that Mercurial bookmarks are conceptually closer to Git branches than Mercurial named branches are. (References to the latter, but not to either of the former, are hard-written into a commit and are difficult to expunge or modify. Also, commits can only belong to one Mercurial named branch at a time.) So they encourage Mercurial/Git integration based on Mercurial bookmarks rather than named branches.

However, if your upstream Mercurial repositories do happen to be structured in ways that work well with this import method, then it may well suit your needs. I haven't done any performance comparisons versus the `hg-git` methods, but many users do report satisfaction using the [git-hg](https://github.com/cosmin/git-hg) frontend, which is based on the import method we're looking at now.

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

Ok, so we've made a change and pushed it both to `master` and to our "hg-tracking" branch `origin2/master2`. Ideally we'd have some frontend porcelain that made that more elegant, but this is what we'd expect the end result to be. Now we want to push that change back from the "hg-tracking" branch to our clone of the Mercurial repository. If that succeeds, then our frontend porcelain could arrange for the change to be `hg push`ed back upstream.

The [documentation for convert]() describes a `branchmap` file that lets you explicitly specify which Git branches being imported in should go to which Mercurial named branches. So we'll try that out:

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

There's that r34 again. Now come on, here. Why our revision numbers so high. We started off with a repository with 19 changesets (the 0..17 we cloned plus the "post-latest" one we added). Then we added one on the Git side. So we should now have 20 changesets. Instead we have 37. It looks like all of the reachable old Git commits (all the ancestors of the named heads in Mercurial) have been duplicated in the Mercurial repository. This is unacceptable.

Maybe there's some way to clean this all up and get it to work. I don't know. But on the face of it, this method just looks terribly unsuited to play the role of an ongoing git->hg bridge. Of course, that's not its intended purpose: it's *meant* for importing Git commits that the destination Mercurial repository had never seen, for example, if we were converting the Git repository into an empty Mercurial repository. But it initially looked like it might do what we need for an ongoing back-and-forth bridge. That's in fact how the `githg` tool uses it. But it doesn't work. We can't be polluting our Mercurial repository with all these duplicate commits everytime we push. Not to mention that our Git-created commits are descended in the history from the new copies of the old commits, rather than from the originals, as we intended.

The `convert` extension has a configuration setting `convert.hg.usebranchnames` that defaults to `true`. So far as I can tell, turning that off has no effect if you continue to specify a `--branchmap` file. I tried repeating everything we did before without the `-M` and `-o` flags to `hg-fast-export`, but we end up with the same duplication when we try to `convert` the Git repository back into Mercurial.

The `convert` extension comes with a flag `--rev` that permits you to specify what revisions to import *up until*, but we want the opposite: to be able to specify what revisions not to import *before*. The extension's documentation [discusses that](), but says you need to do this:

    The second way would be to use the splice map and say "The first commit I'm
    interested in should have 0000000000000000000000000000000000000000 as its
    parent." After the repository conversion, you can then clean the history and
    remove unwanted branches. [This will] still require downloading all
    changes, though. 

Perhaps we could do something like that (only using an existing Mercurial changeset as the parent we splice onto, rather than 0000000000000000000000000000000000000000). But wow, that's a lot more work than we were expecting. And no doubt our initial efforts to get that working will be brittle and break in corner cases that didn't occur to us. Perhaps if there were no alternatives, this is what we'd have to do. But given how difficult this all looks, let's turn instead to the `hg-git` methods.

Lesson learned: the backend method the `git-hg` tool uses to push from Git to Mercurial is not usable. The tool does declare that functionality "experimental", but in its current implementation it's just broken. It will double your Mercurial repository every time you push, and your new Git commits will not be a descendent of any commit already in the database. Don't use `git-hg` to push to Mercurial; if you're going to use it, use it for pulling only.

