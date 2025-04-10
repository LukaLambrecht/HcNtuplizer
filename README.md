# Ntuplizer for Hc analysis

This repository contains an ntuplizer for an analysis of H boson production in association with charmed mesons.
It starts from customized NanoAOD, as produced with [this NanoAOD producer](https://github.com/LukaLambrecht/HcNano),
which is essentially central NanoAOD, just with some extra branches added for reconstructed charmed mesons from pairs and triplets of individual tracks.
(Note: this ntuplizer also runs on regular central NanoAOD, as the custom additional branches are not actively used here).


## How to set up
Download and run the installation script as follows:
```
wget https://raw.githubusercontent.com/LukaLambrecht/HcNtuplizer/refs/heads/dev/Run3/setup.sh
bash setup.sh
```

This will set up the ntuplizer with the following structure (as conventional for CMSSW modules): CMSSW_<version>/src/PhysicsTools/HcNtuplizer.

The CMSSW version is currently hard-coded in the setup script.
In case another CMSSW version is needed, you can edit the setup script after downloading it but before running it.

Note: this was tested in the `/afs` area on `lxplus`; might need modifications in other environments.


## How to run

### Prepare the jobs
Prepare the jobs by running the following command (in the `run` directory):

```  
python3 run.py -s <sample list> -y <year> -t <data type> -o <output dir>  
```

The sample list must contain either paths to datasets on DAS, or locally accessible folders representing the root files for a given sample.
The data type must be either `data` (for data) or `mc` (for simulation).
This command creates a directory `jobs_<data type>_<year>` containing all required information to run the ntuplizing jobs,
but will not yet run or submit the jobs.

### Local tests
For running some local tests, go into the `jobs_<data type>_<year>` directory, and run `python3 processor.py <job id>`.
You can check the valid job ids in the `metadata.json`.

### Submit to condor
When everything looks good, submit the jobs by running `condor_submit submit.sh` (in the jobs folder as above).

You can check the job status with `python3 run.py --check-status -y <year> -t <data type>`.
Once the jobs are finished, you can scan their output for potential failures using the following command:
```
python3 jobcheck.py --dir jobs_<data type>_<year> --notags
```
Note: this is work in progress, and absense of warnings issued by this script does not guarantee that all jobs actually ran fine.

### Merging output files  
Run `run.py --post -y <year> -t <data type> --xsec-file <path to file with cross-sections for all simulated samples>`.

This will merge all files per sample and add the correct normalization factor.
