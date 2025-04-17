# Conditionally deactivate if an environment is activated
if [ -n "${CONDA_DEFAULT_ENV}" ]; then
    echo "Deactivating conda environment: ${CONDA_DEFAULT_ENV}"
    conda deactivate
fi

# if /workdir/miniconda3/env/wepppy310-env exists, conda env remove it
if [ -d "/workdir/miniconda3/envs/wepppy310-env" ]; then
    rm -rf /workdir/miniconda3/envs/wepppy310-env
    echo "Removed existing conda environment: wepppy310-env"
fi

conda clean --all
conda update -n base conda
conda config --set channel_priority flexible
conda env create -f /workdir/wepppy/install/conda/wepppy310-env.yaml --yes

# copy .pth files to site-packages
cp /workdir/wepppy/install/conda/*.pth /workdir/miniconda3/envs/wepppy310-env/lib/python3.10/site-packages/

git clone https://github.com/rogerlew/rosetta /workdir/miniconda3/envs/wepppy310-env/lib/python3.10/site-packages/rosetta

pip install . --no-deps --no-cache-dir 
