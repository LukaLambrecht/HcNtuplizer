#!/usr/bin/env python

# external imports
import os
import sys
import subprocess
import json
from pathlib import Path
import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True
import argparse
import yaml

# local imports
import helpers


## parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('--year', type=str, help='Year to run', default="2022")
parser.add_argument('--output', type=str, help='Output dir', default = "/eos/user/i/iparaske/HcTrees/")
parser.add_argument('--type', type=str, help='mc or data', default = "mc", choices=['mc', 'data'])
parser.add_argument('--post',help='Merge output files',action='store_true')
parser.add_argument('-n',type=int, help='Number of files per job', default=10)
parser.add_argument('--xsec-file', type=str, help='xsec file', default = "samples/xsec.conf")
parser.add_argument('--check-status', help='Checks jobs status', action='store_true')
parser.add_argument('--resubmit', help='Resubmit failed jobs', action='store_true')
args = parser.parse_args()

golden_json = {
    '2022': 'Cert_Collisions2022_355100_362760_Golden.json',
    '2022EE': 'Cert_Collisions2022_355100_362760_Golden.json',
    '2023': 'Cert_Collisions2023_366442_370790_Golden.json',
    '2023BPix': 'Cert_Collisions2023_366442_370790_Golden.json'
}


def create_metadata_json():
    # write metadata json file
    
    dataset_type = args.type
    jobs_dir = "jobs_" + dataset_type + "_" + args.year
    year = args.year
    
    # read samples yaml file
    samples_yaml_file = (os.environ['CMSSW_BASE']
      + "/src/PhysicsTools/HcNtuplizer/run/samples/"
      + dataset_type + "_" + year + ".yaml")
    print(f'Reading sample list {samples_yaml_file}')
    with open(samples_yaml_file, 'r') as file:
        samples = yaml.safe_load(file)

    # find samples in listed sample file
    physics_processes = []
    eras = []
    das_dict = {}
    nfiles = 0
    print('Finding files...')
    for sample in samples:
        das_dict[sample] = {}
        for dataset in samples[sample]:
            
            # find files
            if os.path.exists(dataset):
                # list local files
                print(f'  - Finding files in local dataset {dataset}...')
                physics_process = dataset.split("/")[-1].split("_Run")[0] # to improve
                physics_processes.append(physics_process)
                files_found = [os.path.join(dataset, f) for f in os.listdir(dataset) if f.endswith('.root')]
            else:
                # find files using DAS
                print(f'  - Finding files in remote dataset {dataset} with DAS...')
                das_query = 'dasgoclient --query="file dataset=' + dataset + '"'
                query_out = os.popen(das_query)
                files_found = ['root://xrootd-cms.infn.it/'+_file.strip() for _file in query_out]
                physics_process = dataset.split("/")[1]
                physics_processes.append(physics_process)
            
            # printouts for logging
            nfiles += len(files_found)
            print(f'    Found {len(files_found)} files, physics process: {physics_process}.')

            #  add to structure   
            if dataset_type == "data":
                # special settings for data
                era = dataset.split("/")[2]
                eras.append(era)
                if physics_process not in das_dict[sample]:
                    das_dict[sample][physics_process] = {}
                if era not in das_dict[sample][physics_process]:
                    das_dict[sample][physics_process][era] = []
                das_dict[sample][physics_process][era].extend(files_found)
            else:
                # special settings for mc
                if physics_process not in das_dict[sample]:
                    das_dict[sample][physics_process] = []
                das_dict[sample][physics_process].extend(files_found)

    # write metadata json file
    json_file = jobs_dir + '/metadata.json'
    json_content = {}
    json_content["output_dir"] = args.output
    json_content["jobs_dir"] = args.jobs_dir
    json_content["year"] = args.year    
    json_content["type"] = dataset_type
    if dataset_type == "data":  
        json_content["golden_json"] = (os.environ['CMSSW_BASE']
          + "/src/PhysicsTools/HcNtuplizer/data/JSON/" + golden_json[args.year])
    else: json_content["golden_json"] = None
    json_content["sample_names"] = []
    json_content["physics_processes"] = []
    if dataset_type == "data": json_content["eras"] = []
    json_content["jobs"] = []
        
    for sample_name in samples: json_content["sample_names"].append(sample_name)
    for physics_process in physics_processes: json_content["physics_processes"].append(physics_process)
    if dataset_type == "data":
        for era in eras: json_content["eras"].append(era)

    # loop over samples, make chunks, and write job info    
    job_id = 0
    if dataset_type == "data":
        for sample in samples:
            for physics_process in das_dict[sample]:
                for era in das_dict[sample][physics_process]:
                    for chunk in enumerate(helpers.get_chunks(das_dict[sample][physics_process][era],args.n)):
                        json_content["jobs"].append({
                          "job_id": job_id,
                          "input_files": chunk[1],
                          "sample_name": sample,
                          "physics_process": physics_process,
                          "era": era })
                        job_id += 1
    else:
        for sample in samples:
            for physics_process in das_dict[sample]:
                for chunk in enumerate(helpers.get_chunks(das_dict[sample][physics_process],args.n)):
                    json_content["jobs"].append({
                      "job_id": job_id,
                      "input_files": chunk[1],
                      "sample_name": sample,
                      "physics_process": physics_process})
                    job_id += 1

    with open(json_file, 'w') as file:
        json.dump(json_content, file, indent=4)

    # printouts for logging
    print(f'Found {nfiles} in total, resulting in {job_id} jobs.')
        

def write_condor_submit(jobids_file):
    '''
    Create the submit.sh file in the job directory
    '''
    cmssw_base = os.environ['CMSSW_BASE']
    jobs_dir_path =os.getcwd() + "/" + args.jobs_dir 
    
    condor_submit_file = open(args.jobs_dir + "/submit.sh","w")
    condor_submit_file.write('''
executable = condor_exec.sh

arguments = $(jobid) ''' + cmssw_base + ''' ''' + jobs_dir_path  + ''' 

request_memory  = 2000
request_disk    = 10000000

output = log/$(jobid).out
error = log/$(jobid).err
log = log/$(jobid).log

JobBatchName = HcTrees_''' + args.type + '''_''' + args.year + '''
+JobFlavour = "tomorrow"

queue jobid from ''' + jobids_file)

    condor_submit_file.close()


def create_condor_submit():
    '''
    Get number of jobs from metadata.json,
    and write job_ids.txt and submit.sh in the job directory
    '''    
    # get job ids from json
    with open(args.jobs_dir + "/metadata.json", 'r') as file:
        data = json.load(file)  
    njobs = len(data["jobs"])
    jobs_list = [i for i in range(njobs)]
    
    # write job ids to txt file
    with open(args.jobs_dir + "/job_ids.txt", 'w') as file:
        for index, item in enumerate(jobs_list):
            if index < len(jobs_list) - 1:
                file.write(str(item) + '\n')
            else:
                file.write(str(item))
    
    # write submit.sh
    write_condor_submit(jobids_file="job_ids.txt")


def parse_sample_xsec(cfgfile):
    """ Parses the cross-section file and returns a dictionary. """
    xsec_dict = {}
    with open(cfgfile) as f:
        for l in f:
            l = l.strip()
            if not l or l.startswith('#'):
                continue
            pieces = l.split()
            samp = None
            xsec = None
            isData = False
            for s in pieces:
                if '/MINIAOD' in s or '/NANOAOD' in s:
                    samp = s.split('/')[1]
                    if '/MINIAODSIM' not in s and '/NANOAODSIM' not in s:
                        isData = True
                        break
                else:
                    try:
                        xsec = float(s)
                    except ValueError:
                        try:
                            import numexpr
                            xsec = numexpr.evaluate(s).item()
                        except:
                            pass
            if samp is None:
                print(f"Ignore line:\n{l}")
            elif not isData and xsec is None:
                print(f"Cannot find cross section:\n{l}")
            else:
                if samp in xsec_dict and xsec_dict[samp] != xsec:
                    raise RuntimeError(f"Inconsistent entries for sample {samp}")
                xsec_dict[samp] = xsec
    return xsec_dict


def add_weights(file, xsec, lumi=1000., treename='Events'):
    """ Adds cross-section weights to a merged ROOT file if not already present. """
    from array import array
    ROOT.PyConfig.IgnoreCommandLineOptions = True

    def _get_sum(tree, wgtvar):
        htmp = ROOT.TH1D('htmp', 'htmp', 1, 0, 10)
        tree.Project('htmp', '1.0', wgtvar)
        sum_value = float(htmp.Integral())
        htmp.Delete()
        return sum_value
    
    def _fill_const_branch(tree, branch_name, buff):
        if tree.GetBranch(branch_name):  # Prevent overwriting existing branch
            print(f"Branch {branch_name} already exists in {file}, skipping.")
            return
        b = tree.Branch(branch_name, buff, f'{branch_name}/F')
        for _ in range(tree.GetEntries()):
            b.Fill()

    f = ROOT.TFile(str(file), 'UPDATE')
    run_tree = f.Get('Runs')
    tree = f.Get(treename)

    # Check if 'xsecWeight' branch already exists
    if tree.GetBranch("xsecWeight"):
        print(f"xsecWeight already exists in {file}, skipping weight addition.")
    else:
        sumwgts = _get_sum(run_tree, 'genEventSumw')
        print(sumwgts)
        if sumwgts == 0:
            raise ValueError(f"genEventSumw is zero in {file}, preventing division by zero.")
        
        xsecwgt = xsec * lumi / sumwgts
        xsec_buff = array('f', [xsecwgt])
        _fill_const_branch(tree, "xsecWeight", xsec_buff)
        print(f"Added xsecWeight to {file}")

    tree.Write(treename, ROOT.TObject.kOverwrite)
    f.Close()

def run_add_weights():
    '''
    Merges, applies weights, and combines physics processes per sample.
    '''

    # read cross-sections
    xsec_dict = parse_sample_xsec(args.xsec_file)

    # read metadata
    with open(args.jobs_dir + "/metadata.json", 'r') as file:
        data = json.load(file)
    base_output_dir = data["output_dir"]
    dataset_type = data["type"]
    year = data["year"]
    
    # loop over samples
    sample_dirs = {sample: [] for sample in data["sample_names"]}
    for sample in sample_dirs:
        sample_path = os.path.join(base_output_dir, dataset_type, year, sample)
        if not os.path.isdir(sample_path): continue

        # loop over processes for this sample
        physics_process_dirs = ([
            d.name for d in Path(sample_path).iterdir() if d.is_dir()
        ])
        for physics_process in physics_process_dirs:

            # find cross-section for this process
            if physics_process not in xsec_dict:
                print(f"Process {physics_process} not found in xsec file, skipping.")
                continue
            xsec = xsec_dict[physics_process]

            # find all files for this process
            process_dir = os.path.join(sample_path, physics_process)
            root_files = list(Path(process_dir).glob("*.root"))
            if not root_files:
                print(f"No ROOT files found in {process_dir}, skipping...")
                continue

            # merge split files for this process
            merged_file = os.path.join(process_dir, "merged_tree.root")
            if len(root_files) > 1:
                merge_cmd = f"haddnano.py {merged_file} {' '.join(map(str, root_files))}"
                print(f"Merging {len(root_files)} files into {merged_file}")
                subprocess.run(merge_cmd, shell=True, check=True)
            else: merged_file = str(root_files[0])

            # add weights to the merged file
            weighted_file = os.path.join(process_dir, "weighted_tree.root")
            subprocess.run(f"cp {merged_file} {weighted_file}", shell=True)
            add_weights(weighted_file, xsec)
            sample_dirs[sample].append(weighted_file)

    # merge weighted process files per sample
    for sample, process_files in sample_dirs.items():
        if len(process_files) > 1:
            # if more than 1 file, need to merge them
            final_merged_file = os.path.join(base_output_dir,
              dataset_type, year, sample, f"{sample}_final_merged.root")
            merge_cmd = f"haddnano.py {final_merged_file} {' '.join(process_files)}"
            print(f"Merging {len(process_files)} weighted files into {final_merged_file}")
            subprocess.run(merge_cmd, shell=True, check=True)
        elif process_files:
            # if only 1 file, it is already final
            final_merged_file = process_files[0]
            print(f"Only one file for {sample}, no need to merge.")


def merge_output_files():
    '''
    Merges all files per sample into one final ROOT file in the merged/ directory.
    '''

    # load metadata
    file_path = os.path.join(args.jobs_dir, 'metadata.json')
    with open(file_path, 'r') as file:
        data = json.load(file)

    base_output_dir = data["output_dir"]
    dataset_type = data["type"]
    year = data["year"]
    
    # create merged output directory
    merged_dir = os.path.join(base_output_dir, dataset_type, year, "merged")
    os.makedirs(merged_dir, exist_ok=True)

    # loop over sample directories in the provided input directory
    sample_dirs = ([d.name
      for d in Path(os.path.join(base_output_dir, dataset_type, year)).iterdir()
      if d.is_dir()
    ])
    for sample in sample_dirs:
        sample_path = os.path.join(base_output_dir, dataset_type, year, sample)

        # skip the merged directory itself
        if sample == "merged": continue

        # find all files for this sample
        weighted_files = []
        physics_process_dirs = [d for d in Path(sample_path).iterdir() if d.is_dir()]
        for process_dir in physics_process_dirs:
            weighted_file = os.path.join(process_dir, "weighted_tree.root")
            if os.path.exists(weighted_file):
                # copy and rename weighted files to merged directory
                renamed_weighted_file = os.path.join(merged_dir, f"{sample}_weighted_{process_dir.name}.root")
                subprocess.run(f"cp {weighted_file} {renamed_weighted_file}", shell=True)
                weighted_files.append(renamed_weighted_file)

        # if no weighted files exist, just merge the raw files
        # (e.g. for data)
        if not weighted_files:
            print(f"No weighted files found for sample {sample}. Merging raw data files instead.")
            input_files = []
            for process_dir in physics_process_dirs:
                infiles_dir = os.path.join(base_output_dir, dataset_type, year, sample, process_dir.name)
                for root, _, files in os.walk(infiles_dir):
                    for file in files:
                        if file.endswith(".root"):
                            input_files.append(os.path.join(root, file))

            # define merged output file
            output_file = os.path.join(merged_dir, f"{sample}_merged.root")

            if input_files:
                merge_cmd = f"haddnano.py {output_file} {' '.join(input_files)}"
                print(f"Merging raw data files for {sample} into {output_file}")
                subprocess.run(merge_cmd, shell=True, check=True)
            else:
                print(f"No ROOT files found for {sample}, skipping...")

        elif len(weighted_files) > 1:
            # if multiple weighted files exist, merge them
            final_merged_file = os.path.join(merged_dir, f"{sample}_final_merged.root")
            merge_cmd = f"haddnano.py {final_merged_file} {' '.join(weighted_files)}"
            print(f"Merging {len(weighted_files)} weighted files into {final_merged_file}")
            subprocess.run(merge_cmd, shell=True, check=True)

        else:
            # if only one weighted file exists, rename it as the final output
            final_merged_file = os.path.join(merged_dir, f"{sample}_final_merged.root")
            os.rename(weighted_files[0], final_merged_file)
            print(f"Only one weighted file for {sample}, renamed to {final_merged_file}")


def check_job_status():
    
    file_path = args.jobs_dir + '/metadata.json'
    with open(file_path, 'r') as file:
        data = json.load(file)
    
    njobs = len(data['jobs'])
    jobids = {'running': [], 'failed': [], 'completed': []}
    for jobid in range(njobs):
        logpath = os.path.join(args.jobs_dir, "log", '%d.log' % jobid)
        # print(logpath)
        if not os.path.exists(logpath):
            print('Cannot find log file %s' % logpath)
            jobids['failed'].append(str(jobid))
            continue
        with open(logpath) as logfile:
            errormsg = None
            finished = False
            for line in reversed(logfile.readlines()):
                if 'Job removed' in line or 'aborted' in line:
                    errormsg = line
                if 'Job submitted from host' in line:
                    # if seeing this first: the job has been resubmited
                    break
                if 'return value' in line:
                    if 'return value 0' in line:
                        finished = True
                    else:
                        errormsg = line
                    break
            if errormsg:
                print(logpath + '\n   ' + errormsg)
                jobids['failed'].append(str(jobid))
            else:
                if finished:
                    jobids['completed'].append(str(jobid))
                else:
                    jobids['running'].append(str(jobid))
    assert sum(len(jobids[k]) for k in jobids) == njobs
    all_completed = len(jobids['completed']) == njobs
    info = {k: len(jobids[k]) for k in jobids if len(jobids[k])}
    print('Job %s status: ' % args.jobs_dir + str(info))
    return all_completed, jobids

def resubmit():
    # Ensure check_job_status accepts 'args' as an argument
    jobids = check_job_status()[1]['failed']  
    
    jobids_file = os.path.join(args.jobs_dir, 'resubmit.txt')

    with open(jobids_file, 'w') as f:
        f.write('\n'.join(jobids))

    # Pass the correct absolute path to write_condor_submit
    write_condor_submit(jobids_file=jobids_file)

def main():

    # set name for jobs directory
    jobs_dir = "jobs_" + args.type + "_" + args.year
    args.jobs_dir = jobs_dir

    # handle special cases
    if args.resubmit:
        resubmit()
        sys.exit(0)
    
    if args.check_status:
        check_job_status()
        sys.exit(0)
   
    if args.post:
        run_add_weights()
        merge_output_files()
        sys.exit(0)   
    
    # check output directory 
    helpers.check_if_dir_exists(jobs_dir)
    helpers.check_if_dir_exists(args.output)
    print("Will write output trees to " + args.output)
    print("Number of files per job: " + str(args.n))
    
    # create necessary dirs
    os.system("mkdir -p " + jobs_dir + "/log/")
    
    # copy necessary files to jobs dir
    os.system("cp configs/processor.py " + jobs_dir)
    os.system("cp configs/keep_and_drop*.txt " + jobs_dir)
    os.system("cp configs/condor_exec.sh " + jobs_dir)
    
    # create metadata json and condor submit files in the jobs dir
    create_metadata_json()
    create_condor_submit()


if __name__ == "__main__":
    main()
