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


# parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('-s', '--samplelist', help='List of samples to process', default=None)
parser.add_argument('-o', '--output', help='Output dir', default=None)
parser.add_argument('-y', '--year', type=str, help='Year to run', required=True)
parser.add_argument('-t', '--dtype', type=str, help='Data type (mc or data)', default = "mc", choices=['mc', 'data'])
parser.add_argument('-n', type=int, help='Number of files per job', default=10)
parser.add_argument('--post', help='Merge output files', default=False, action='store_true')
parser.add_argument('--xsec-file', type=str, help='Cross-section file', default=None)
parser.add_argument('--check-status', help='Check jobs status', action='store_true')
parser.add_argument('--resubmit', help='Resubmit failed jobs', action='store_true')
args = parser.parse_args()

golden_json = {
    '2016APV': 'Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt',
    '2016': 'Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt',
    '2017': 'Cert_294927-306462_13TeV_UL2017_Collisions17_GoldenJSON.txt',
    '2018': 'Cert_314472-325175_13TeV_Legacy2018_Collisions18_JSON.txt',
    '2022': 'Cert_Collisions2022_355100_362760_Golden.json',
    '2022EE': 'Cert_Collisions2022_355100_362760_Golden.json',
    '2023': 'Cert_Collisions2023_366442_370790_Golden.json',
    '2023BPix': 'Cert_Collisions2023_366442_370790_Golden.json'
}

# for merging: specifiy whether to use the standard or the custom haddnano
#haddnano = 'haddnano.py' # standard built-in haddnano (available after doing cmsenv)
haddnano = os.path.join(os.path.dirname(__file__), 'haddnano.py') # custom haddnano
if haddnano!='haddnano.py':
    if not os.path.exists(haddnano):
        msg = f'Requested to use custom haddnano script "{haddnano}",'
        msg += ' but it does not seem to exist.'
        raise Exception(msg)
    else:
        msg = f'Note: using non-standard haddnano script "{haddnano}" for merging.'
        print(msg)


def create_metadata_json():
    # write metadata json file

    # check sample list
    if args.samplelist is None:
        msg = 'A sample list must be provided.'
        raise Exception(msg)
    if not os.path.exists(args.samplelist):
        msg = f'Provided sample list {args.samplelist} does not exist.'
        raise Exception(msg)
    
    dataset_type = args.dtype
    jobs_dir = "jobs_" + dataset_type + "_" + args.year
    year = args.year
    
    # read samples yaml file
    samples_yaml_file = args.samplelist
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
        # set path to golden json file
        if args.year not in golden_json.keys():
            msg = f'Year {args.year} not found in golden json dict.'
            raise Exception(msg)
        golden_json_file = (os.environ['CMSSW_BASE']
          + "/src/PhysicsTools/HcNtuplizer/data/JSON/"
          + golden_json[args.year])
        if not os.path.exists(golden_json_file):
            msg = f'Golden json file {golden_json_file} does not exist.'
            raise Exception(msg)
        json_content["golden_json"] = golden_json_file
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
    jobs_dir_path = os.getcwd() + "/" + args.jobs_dir 
    
    condor_submit_file = os.path.join(args.jobs_dir, 'submit.sh')
    f = open(condor_submit_file, 'w')
    f.write('''
executable = condor_exec.sh

arguments = $(jobid) ''' + cmssw_base + ''' ''' + jobs_dir_path  + ''' 

request_memory  = 2000
request_disk    = 10000000

output = log/$(jobid).out
error = log/$(jobid).err
log = log/$(jobid).log

JobBatchName = HcTrees_''' + args.dtype + '''_''' + args.year + '''
+JobFlavour = "tomorrow"

queue jobid from ''' + jobids_file)
    f.close()
    print(f'Created condor submit file {condor_submit_file}.')


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

    # check provided config file
    if cfgfile is None:
        msg = 'A config file for the cross-sections must be provided.'
        raise Exception(msg)
    if not os.path.exists(cfgfile):
        msg = f'Provided xsec config file {cfgfile} does not exist.'
        raise Exception(msg)

    xsec_dict = {}
    lines = []
    # read lines (remove comments and empty lines)
    with open(cfgfile) as f:
        for l in f:
            l = l.strip(' \n\t')
            if len(l)==0 or l.startswith('#'): continue
            lines.append(l)
    # parse each line
    for line in lines:
        pieces = line.split()
        if len(pieces)!=2:
            msg = 'WARNING in parsing cross-section dict:'
            msg += f' could not parse line {line}, skipping.'
            print(msg)
            continue
        xsec = float(pieces[0])
        sample = pieces[1]
        if sample in xsec_dict.keys() and xsec_dict[sample] != xsec:
            raise RuntimeError(f"Inconsistent cross-sections for sample {sample}")
        xsec_dict[sample] = xsec
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
    Note: safe to run on data, nothing will happen because the sample is skipped
          if the corresponding cross-section is not found in the provided config.
    Expected file structure before this operation:
      <output directory>/<data type>/<year>/<sample>/<process>/<root files>
    File structure after this operation:
      <output directory>/<data type>/<year>/<sample>/<process>/merged_tree.root (merged root file)
        (note: merged_tree.root is not created if there were no or only one file to start from).
      <output directory>/<data type>/<year>/<sample>/<process>/weighted_tree.root (copy of above with added weights)
        (note: weighted_tree.root is not created if there were no files to start from).
      <output directory>/<data type>/<year>/<sample>/<sample>_final_merged.root
        (note: <sample>_final_merged.root is not created if there were no or only one process to start from).
    '''

    # read cross-sections
    print(f'Using following cross-section file: {args.xsec_file}')
    xsec_dict = parse_sample_xsec(args.xsec_file)

    # read metadata
    with open(args.jobs_dir + "/metadata.json", 'r') as file:
        data = json.load(file)
    base_output_dir = data["output_dir"]
    dataset_type = data["type"]
    year = data["year"]
    
    # loop over samples
    print('Merging files per process...')
    sample_dirs = {sample: [] for sample in data["sample_names"]}
    for sample in sample_dirs:
        print(f'  - Sample: {sample}')
        sample_path = os.path.join(base_output_dir, dataset_type, year, sample)
        if not os.path.isdir(sample_path): continue

        # loop over processes for this sample
        physics_process_dirs = ([
            d.name for d in Path(sample_path).iterdir() if d.is_dir()
        ])
        for physics_process in physics_process_dirs:
            print(f'    - Process: {physics_process}')

            # find cross-section for this process
            if physics_process not in xsec_dict:
                print(f"      Process {physics_process} not found in xsec file, skipping.")
                continue
            xsec = xsec_dict[physics_process]

            # find all files for this process
            process_dir = os.path.join(sample_path, physics_process)
            root_files = ([os.path.join(process_dir, f) for f in os.listdir(process_dir)
                           if( f.endswith('.root')
                           and f!='merged_tree.root'
                           and f!='weighted_tree.root' )])
            if not root_files:
                print(f"      No ROOT files found in {process_dir}, skipping.")
                continue

            # merge split files for this process
            merged_file = os.path.join(process_dir, "merged_tree.root")
            if len(root_files) > 1:
                merge_cmd = f"{haddnano} {merged_file} {' '.join(map(str, root_files))}"
                print(f"      Merging {len(root_files)} files into {merged_file}")
                subprocess.run(merge_cmd, shell=True, check=True)
            else: merged_file = str(root_files[0])

            # add weights to the merged file
            weighted_file = os.path.join(process_dir, "weighted_tree.root")
            subprocess.run(f"cp {merged_file} {weighted_file}", shell=True)
            add_weights(weighted_file, xsec)
            sample_dirs[sample].append(weighted_file)

    # merge weighted process files per sample
    # note: skipped for now since this step is implicitly repeated
    #       in merge_output_files()
    '''print('Merging processes per sample...')
    for sample, process_files in sample_dirs.items():
        print(f'  - Sample: {sample}')
        if len(process_files) > 1:
            # if more than 1 file, need to merge them
            final_merged_file = os.path.join(base_output_dir,
              dataset_type, year, sample, f"{sample}_final_merged.root")
            merge_cmd = f"{haddnano} {final_merged_file} {' '.join(process_files)}"
            print(f"  Merging {len(process_files)} weighted files into {final_merged_file}")
            subprocess.run(merge_cmd, shell=True, check=True)
        elif len(process_files) == 1:
            # if only 1 file, it is already final
            print(f"Only one file for {sample}, no need to merge.")
            pass
        else: pass'''


def merge_output_files():
    '''
    Merges all files per sample into one final ROOT file in the merged directory.
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
    print('Merging output files...')
    sample_dirs = ([d.name
      for d in Path(os.path.join(base_output_dir, dataset_type, year)).iterdir()
      if d.is_dir()
    ])
    for sample in sample_dirs:
        sample_path = os.path.join(base_output_dir, dataset_type, year, sample)

        # skip the merged directory itself
        if sample == "merged": continue
        print(f'  - Now merging sample {sample}...')

        # find all files for this sample
        # note: if run_add_weights() was run before this function,
        #       we use the "weighted_tree.root" per physics process for this sample;
        #       else (i.e. if "weighted_tree.root") does not exist,
        #       use all raw files per physics process for this sample.
        # todo: the current implementation is not robust against cases
        #       where "weighted_tree.root" exists for some physics processes but not for others
        #       (in principle this shouldn't happen, but one never knows).
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
            print(f"    No weighted files found for sample {sample}. Merging raw data files instead.")
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
                merge_cmd = f"{haddnano} {output_file} {' '.join(input_files)}"
                print(f"    Merging raw data files for {sample} into {output_file}...")
                subprocess.run(merge_cmd, shell=True, check=True)
            else:
                print(f"No ROOT files found for {sample}, skipping...")

        elif len(weighted_files) > 1:
            # if multiple weighted files exist, merge them
            final_merged_file = os.path.join(merged_dir, f"{sample}_final_merged.root")
            merge_cmd = f"{haddnano} {final_merged_file} {' '.join(weighted_files)}"
            print(f"    Merging {len(weighted_files)} weighted files for sample {sample} into {final_merged_file}....")
            subprocess.run(merge_cmd, shell=True, check=True)

        else:
            # if only one weighted file exists, rename it as the final output
            final_merged_file = os.path.join(merged_dir, f"{sample}_final_merged.root")
            os.rename(weighted_files[0], final_merged_file)
            print(f"    Only one weighted file for {sample}, renamed to {final_merged_file}...")


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
    '''
    Resubmit failed jobs
    '''

    # get the job ids of failed jobs
    jobids = check_job_status()[1]['failed']
    
    # write the failed job ids to the resubmit file
    jobids_file = os.path.join(args.jobs_dir, 'resubmit.txt')
    with open(jobids_file, 'w') as f:
        f.write('\n'.join(jobids))
    print(f'Failed job ids written to {jobids_file}.')

    # make a new condor submit file with the failed job ids
    write_condor_submit(jobids_file = os.path.abspath(jobids_file))


def main():

    # set name for jobs directory
    jobs_dir = "jobs_" + args.dtype + "_" + args.year
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
    
    # check job directory and output directory 
    helpers.check_if_dir_exists(jobs_dir)
    if args.output is None:
        msg = 'An output directory must be provided.'
        raise Exception(msg)
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
