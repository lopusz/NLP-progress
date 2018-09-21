#!/bin/bash

CONDA_DIR=conda
ENV_NAME=conda_env

DIR=$(pwd)
ENV_DIR=$(dirname ${BASH_SOURCE[0]})
CONDA_SHORT_DIR=${ENV_DIR}/${CONDA_DIR}

cd ${CONDA_SHORT_DIR}
CONDA_BIN_DIR=$(pwd)/bin
cd ${DIR}


if echo $PATH | grep -qe "^${CONDA_BIN_DIR}:"; then
    echo "Python env already set-up"
else
    export PATH="${CONDA_BIN_DIR}:${PATH}"
    echo "Setting up python environment"

    source activate ${ENV_DIR}/${ENV_NAME}
fi

