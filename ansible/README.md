# README for gerrit-stats ansible playbooks

The ansible playbook in this directory:

- Sets up a host named `devel-stats` to run `gerrit-stats`
- It creates a `devel-stats` user
- It clones this repo in that user's home directory
- Makes a script to run `gerrit-stats` via docker on the `gerrit-stats` host

## Install

Most install is done in a virtualenv created by `ansible/run.sh`.

But you need a host in your `~/.ssh/config` named `devel-stats.`

Here's mine:

    Host bastlabs
        HostName primary.bastion.wmflabs.org
        PubkeyAuthentication yes
        ProxyCommand none

    Host devel-stats
        Hostname stats.devel-stats.eqiad1.wikimedia.cloud
        ProxyCommand ssh -a -W %h:%p bastlabs

## Usage

    ./ansible/run.sh
