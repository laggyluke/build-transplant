#!/usr/bin/env bash
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update
sudo apt-get install -y build-essential vim curl git mercurial \
  python-dev python-pip libldap2-dev libsasl2-dev

# add github and bitbucket to ssh known hosts
echo "github.com ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAq2A7hRGmdnm9tUDbO9IDSwBK6TbQa+PXYPCPy6rbTrTtw7PHkccKrpp0yVhp5HdEIcKr6pLlVDBfOLX9QUsyCOV0wzfjIJNlGEYsdlLJizHhbn2mUjvSAHQqZETYP81eFzLQNnPHt4EVVUh7VfDESU84KezmD5QlWpXLmvU31/yMf+Se8xhHTvKSCZIFImWwoG6mbUoWf9nzpIoaSjB+weqqUUmpaaasXVal72J+UX2B+2RPW3RcT0eOzQgqlJL3RKrTJvdsjE3JEAvGq3lGHSZXy28G3skua2SmVi/w4yCE6gbODqnTWlg7+wC604ydGXA8VJiS5ap43JXiUFFAaQ==" | sudo tee -a /etc/ssh/ssh_known_hosts
echo "bitbucket.org ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAubiN81eDcafrgMeLzaFPsw2kNvEcqTKl/VqLat/MaB33pZy0y3rJZtnqwR2qOOvbwKZYKiEO1O6VqNEBxKvJJelCq0dTXWT5pbO2gDXC6h6QDXCaHo6pOHGPUy+YBaGQRGuSusMEASYiWunYN0vCAI8QaXnWMXNMdFP3jHAJH0eDsoiGnLPBlBp4TNm6rYI74nMzgz3B9IikW4WVK+dc8KZJZWYjAuORU3jc1c/NPskD2ASinf8v3xnfXeukU0sJ5N6m5E8VLjObPEO+mN2t/FZTMZLiFqPWc/ALSqnMnnhwrNi2rbfg/rd/IpL8Le3pSBne8+seeFVBoGqzHM9yXw==" | sudo tee -a /etc/ssh/ssh_known_hosts

# install redis (for celery)
sudo add-apt-repository -y ppa:chris-lea/redis-server
sudo apt-get update
sudo apt-get install -y redis-server

# create / chown transplant workdir
sudo mkdir -p /var/lib/transplant
sudo chown $USER:$USER /var/lib/transplant

# install, create and activate virtualenv
sudo pip install virtualenv
mkdir -p "$HOME/envs"
virtualenv "$HOME/envs/transplant"
source "$HOME/envs/transplant/bin/activate"

# activate virtualenv on login
echo "source $HOME/envs/transplant/bin/activate" | sudo tee /etc/profile.d/transplant-virtualenv.sh > /dev/null
# BUG: bash prompt is set later during login process, so it won't indicate virtualenv

# install dev dependencies
pip install honcho redis

# install transplant blueprint
cd /vagrant
rm -rf ./relengapi_transplant.egg-info
pip install -e .[test]
