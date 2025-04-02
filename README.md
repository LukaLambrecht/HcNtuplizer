# Ntuplizer for Hc analysis

This repository contains an ntuplizer for an analysis of H boson production in association with charmed mesons.
It starts from customized NanoAOD, as produced with [this NanoAOD producer](https://github.com/LukaLambrecht/HcNano).
It is essentially central NanoAOD, just with some extra branches added for reconstructed charmed mesons from pairs and triplets of individual tracks.


# How to setup
Download and run the installation script as follows:
```
wget https://raw.githubusercontent.com/LukaLambrecht/HcNano/refs/heads/main/setup.sh
bash setup.sh
```

Note: this was tested in the `/afs` area on `lxplus`; might need modifications in other environments.


# How to run

TO UPDATE

```  
cd PhysicsTools/NanoHc/run  
python3 runHcTrees.py --year <year> --output <output dir> (<--type ["mc","data"]>)  
```
Note: It is advised to use the argument ```-n 5``` in order to split the number of files to 5 per job instead of the default 10

# Test locally  
```  
cd jobs_<type>_<year>  
python3 processor.py <job id>  
```
Note: Check the `metadata.json` file for the job ids

# Submit to condor  
```  
cd jobs_<type>_<year>  
condor_submit submit.sh    
```  

# Check jobs status  
Run again ```runHcTrees.py``` with ```--check-status```  

# Merging output files  
Run again ```runHcTrees.py``` with ```--post```  


# Important notes 
- Add/remove modules in ```run/static_files/processor.py```  
- Add/remove samples in ```run/samples```   
- You can find log files in each jobs dir   
- You can write new modules in ```python/producers```  
