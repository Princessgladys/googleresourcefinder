#!/bin/bash

# Make the open source release.

date=$(date -u +'%FT%H-%M-%SZ')
here=$(dirname $0)
name=smsforlife-$date
work=/tmp/build.$$

rm -rf $work
mkdir $work

cd $here/..
mkdir $work/$name
cp -pr . $work/$name/
pushd $work
tar cvfz $name.tar.gz $name --exclude '*.pyc' --exclude '.hg' --exclude '*.tar.gz'
popd
cp $work/$name.tar.gz .

rm -rf $work
