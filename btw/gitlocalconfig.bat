@echo off
call git init
call git config --global user.name "Peter Nemec"
call git config --global user.email peteneme@centrum.sk
call git remote add origin https://github.com/peteneme/pyxWorks.git
call rem git branch --set-upstream-to=origin/master master
call git pull origin master --force
call git remote -v
call git config --list
call git pull origin master --force
call git push --set-upstream origin master