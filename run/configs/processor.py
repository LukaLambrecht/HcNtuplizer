# Define processor

# import producers
from PhysicsTools.NanoAODTools.postprocessing.framework.postprocessor import PostProcessor
from PhysicsTools.HcNtuplizer.producers.HtoZZto4LProducer import HtoZZto4LProducer
from PhysicsTools.HcNtuplizer.producers.puWeightProducer import PileupWeightProducer
from PhysicsTools.HcNtuplizer.producers.leptonSFProducer import ElectronSFProducer, MuonSFProducer
from PhysicsTools.HcNtuplizer.producers.jetSFProducer import JetVMAPProducer, jetJERCProducer
from PhysicsTools.HcNtuplizer.producers.leptonScaleResProducer import eleScaleRes, muonScaleRes

# other imports
import os
import sys
import json 

# read command line args
if len(sys.argv)!=2:
    raise Exception('This processor needs 1 command line arg (job id)')
jobid = name = sys.argv[1]

# read json file
# (note: a file called "metadata.json" is assumed to be present
#  when running this processor)
file_path = 'metadata.json'
with open(file_path, 'r') as file:
    data = json.load(file)

# load settings from json file    
files = data["jobs"][int(jobid)]["input_files"]
base_output_dir = data["output_dir"]
year = data["year"]
dataset_type = data["type"]
golden_json = data["golden_json"]
sample = data["jobs"][int(jobid)]["sample_name"]
physics_process = data["jobs"][int(jobid)]["physics_process"]
if dataset_type == "data": era_data = data["jobs"][int(jobid)]["era"]
else: era_data = None

# convert keep_and_drop_input.txt to python list
with open('keep_and_drop_input.txt', 'r') as file:
    keep_and_drop_input_branches = file.readlines()
keep_and_drop_input_branches = [line.strip() for line in keep_and_drop_input_branches]

# convert keep_and_drop_output.txt to python list
with open('keep_and_drop_output.txt', 'r') as file:
    keep_and_drop_output_branches = file.readlines()
keep_and_drop_output_branches = [line.strip() for line in keep_and_drop_output_branches]

# set output directory
output_dir = os.path.join(base_output_dir, dataset_type, year, sample, physics_process) 

# build the PostProcessor
p = PostProcessor(
    outputDir = output_dir, 
    inputFiles = files, 
    modules=[
        JetVMAPProducer(year,dataset_type),
        #jetJERCProducer(year, era_data, dataset_type), # need Rho variables (removed in current custom nanoaod?)
        eleScaleRes(year, dataset_type),
        #muonScaleRes(year, dataset_type), # unresolved symbol lookup error
        HtoZZto4LProducer(year, dataset_type, sample),
        PileupWeightProducer(year, dataset_type),
        ElectronSFProducer(year, dataset_type), 
        MuonSFProducer(year, dataset_type),
            ],
    branchsel=keep_and_drop_input_branches,
    outputbranchsel=keep_and_drop_output_branches,
    postfix="_" + physics_process,
    prefetch=True,
    jsonInput=golden_json
)
p.run()
