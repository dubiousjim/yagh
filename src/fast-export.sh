#!/bin/sh

MASTER=default

if which python2 >/dev/null 2>&1; then
    PYTHON=python2
    export PYTHON
fi

set -e

# Try to use GNU Coreutils readlink --canonicalize if available,
# falling back to less robust shell script only if not found.
if which greadlink >/dev/null 2>&1; then
    canon="greadlink --canonicalize"
elif readlink -f / >/dev/null 2>&1; then
    canon="readlink -f"
elif which realpath >/dev/null 2>&1; then
    canon="realpath"
else
    canon=canonicalize
fi

# shell implementation of `readlink -f $1`
# changes current directory
canonicalize () {
    local path dir file
    path="$1"
    
    while [ -L "$path" ]; do
        dir=$(dirname "$path")
        path=${$(ls -l "$path")#* -> }
        cd "$dir"
    done
    
    dir=$(dirname "$path")
    file=$(basename "$path")
    if [ ! -d "$dir" ]; then
        echo "canonicalize: $dir: No such directory" >&2
        exit 1
    fi
    dir=$(cd "$dir" && pwd -P)
    printf "%s/%s\n" "$dir" "$file"
}

git-current-branch () {
    local ref
    ref=$(git symbolic-ref -q HEAD) && echo "${ref#refs/heads/}"
}

check-hg-fast-export () {
    local home
    # Search for hg-fast-export $PATH, use if available, if not fall back
    # to looking around for it relative to the current executable's realpath.
    if type hg-fast-export >/dev/null 2>&1; then
        HG_FAST_EXPORT=hg-fast-export
    else
        home=$(dirname "$($canon "$0")")
        # home=$($canon "$home/../fast-export")
        HG_FAST_EXPORT=$home/hg-fast-export.sh
        if ! type "$HG_FAST_EXPORT" >/dev/null 2>&1; then
            echo "ERROR: executable not found, $HG_FAST_EXPORT" >&2
            exit 1
        fi
    fi
}

git-hg-clone () {
    check-hg-fast-export
    
    if [ "--force" = "$1" ]; then
        FORCE="--force"
        shift
    fi
    HG_REMOTE=$1
    
    if [ $# -lt 2 ]; then
        CHECKOUT=$(basename "${1%#*}")
    else
        CHECKOUT=$2
    fi
    if [ -e "$CHECKOUT" ]; then
        echo "ERROR: $CHECKOUT exists" >&2
        exit 1
    fi
    git init "$CHECKOUT"
    hg clone -U "$HG_REMOTE" "$CHECKOUT/.git/hgremote"
    (
        cd "$CHECKOUT"
        git init --bare .git/hgremote/.hg/git
        (
            cd .git/hgremote/.hg/git
            "$HG_FAST_EXPORT" ${MASTER:+-M "$MASTER"} -r ../.. $FORCE
        )
        git remote add hg .git/hgremote/.hg/git
        git fetch hg
        local m=${MASTER:-master}
        if git rev-parse --verify -q "remotes/hg/$m" >/dev/null; then
            local branch=$m
        else
            local branch=$(cd .git/hgremote/ && hg tip | awk '/^branch:/ {print $2; exit}')
        fi
        git config hg.tracking.master "$branch"
        git pull hg "$branch"
    )
}

git-hg-fetch () {
    check-hg-fast-export
    if [ "--force" = "$1" ]; then
        FORCE="--force"
        shift
    fi
    hg -R .git/hgremote pull
    (
        cd .git/hgremote/.hg/git
        "$HG_FAST_EXPORT" ${MASTER:+-M "$MASTER"} $FORCE
    )
    git fetch hg
}

git-hg-pull () {
    while [ $# -gt 0 ]; do
        case "$1" in
        --rebase)
            REBASE="--rebase"
            ;;
        --force)
            FORCE="--force"
            ;;
        esac
        shift
    done

    git-hg-fetch $FORCE

    local current_branch remote_branch

    if ! current_branch=$(git-current-branch); then
            echo "ERROR: You are not currently on a branch." >&2
            exit 1
    fi

    if [ "master" = "$current_branch" ]; then
        remote_branch=$(git config hg.tracking.master || true)

        if [ -z "$remote_branch" ]; then
            local m=${MASTER:-master}
            if git rev-parse --verify -q "remotes/hg/$m" >/dev/null; then
                remote_branch=$m
                git config hg.tracking.master "$m"
            else
                echo "ERROR: Cannot determine remote branch. There is no remote branch called $m, and hg.tracking.master not set. Merge the desired branch manually." >&2
                exit 1
            fi
        fi
    else
        remote_branch=$(git config "hg.tracking.$current_branch" || true)
        if [ -z "$remote_branch" ]; then
             echo "ERROR: Cannot determine the remote branch to pull from. Run git merge manually against the desired remote branch." >&2
             echo "Alternatively, set hg.tracking.$current_branch to the name of the branch in hg the current branch should track." >&2
             exit 1
        fi
    fi

    if [ "--rebase" = "$REBASE" ]; then
        git rebase "hg/$remote_branch"
    else
        git merge "hg/$remote_branch"
    fi
}

git-hg-checkout () {
    if [ "--force" = "$1" ]; then
        FORCE="--force"
        shift
    fi
    git-hg-fetch $FORCE
    if git rev-parse --verify -q "remotes/hg/$1" >/dev/null; then
        git checkout "hg/$1" -b "$1"
        git config "hg.tracking.$1" "$1"
    else
        echo "ERROR: Remote branch $1 doesn't exist." >&2
        exit 1
    fi
}

usage () {
    echo "To clone a mercurial repo run:"
    echo "  git hg clone <path/to/mercurial/repo> [local_checkout_path]"
    echo ""
    echo " if that fails (due to unnamed heads) try:"
    echo "  git hg clone --force <path/to/mercurial/repo> [local_checkout_path]"
    echo ""
    echo "To work with a cloned mercurial repo use: "
    echo "  git hg fetch [ --force ]                   fetch latest branches from mercurial"
    echo "  git hg pull [ --force ] [ --rebase ]       fetch and merge (or rebase) into the"
    echo "                                             current branch"
    echo "  git hg checkout [ --force ] branch_name    checkout a mercurial branch"
}

FORCE=
REBASE=
CMD=$1
shift
case "$CMD" in
    clone|fetch|pull|checkout)
        git-hg-$CMD "$@"
        ;;
    *)
        usage
        exit 1
        ;;
esac
