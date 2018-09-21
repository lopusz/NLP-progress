#!/bin/bash

CONDA_DIR=conda
ENV_NAME=conda_env

wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
CONDA_FULL_DIR=$(pwd)/${CONDA_DIR}
bash ./Miniconda3-latest-Linux-x86_64.sh -b -p ${CONDA_FULL_DIR}
rm -f ./Miniconda3-latest-Linux-x86_64.sh
export PATH="${CONDA_FULL_DIR}/bin:${PATH}"

ENV_FULL_DIR=$(pwd)/${ENV_NAME}
conda env create -p ${ENV_FULL_DIR} -f environment.yml 

#conda install -y pytorch-cpu torchvision-cpu -c pytorch
#pip install --upgrade pip
#pip install tensorflow==1.4.1
#pip install --ignore-installed --upgrade https://storage.googleapis.com/tensorflow/linux/gpu/tensorflow_gpu-1.9.0-cp36-cp36m-linux_x86_64.whl 
#pip install keras
