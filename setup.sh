# setup script for HcNano package within CMSSW

# git settings
BRANCH=main
GIT_USER=LukaLambrecht
REPO_NAME=HcNtuplizer

# other settings
RELEASE=CMSSW_14_0_4
# (note: maybe make command line arg?)

# install CMSSW
echo "Installing $RELEASE..."
scram project CMSSW $RELEASE
cd $RELEASE/src
eval `scram runtime -sh`
echo "Current CMSSW_BASE: $CMSSW_BASE"

# git clone this repository
echo "Cloning the $REPO_NAME repository..."
git cms-init
git clone https://github.com/$GIT_USER/$REPO_NAME PhysicsTools/$REPO_NAME
echo "Cloning the nanoAOD-tools-modules repository..."
git clone https://github.com/cms-cat/nanoAOD-tools-modules.git PhysicsTools/NATModules

# compile and move into package
echo "Compiling..."
cd $CMSSW_BASE/src
scramv1 b
echo "Setup finished"
