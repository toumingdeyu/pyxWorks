#!/bin/bash
VERSIONDIR="ncs-4.7"

#unpack file
sh ./nso-*.signed.bin --skip-verification

#start installer bin file
sh ./nso-*.installer.bin ${HOME}/${VERSIONDIR} --local-install

#start ncs-setup
${HOME}/${VERSIONDIR}/ncs-setup --dest ${HOME}/ncs-run

#copy packages to ncs-run
cp -r ${HOME}/${VERSIONDIR}/packages/neds/* ${HOME}/ncs-run/packages/

# do path record in bashrc
echo source ${HOME}/${VERSIONDIR}/ncsrc >source ${HOME}/.bashrc

#do some batch files
echo cd $HOME/ncs-run; ncs > cd ${HOME}/startncs
echo ncs --stop;sleep 5;pgrep ncs > ${HOME}/stopncs
echo ncs_cli -u admin -C > ${HOME}/ncscli_adm
echo ncs-make-package --service-skeleton python-and-template $1 > ${HOME}/newpackage

#do files executable 
chmod +x ${HOME}/startncs
chmod +x ${HOME}/stopncs
chmod +x ${HOME}/ncscli_adm
chmod +x ${HOME}/newpackage







