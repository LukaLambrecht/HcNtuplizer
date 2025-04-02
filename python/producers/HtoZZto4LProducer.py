# Main analyzer for H -> ZZ -> 4L decays


# external imports
import os
import sys
import json
import ROOT
import math
import itertools
from functools import cmp_to_key
ROOT.PyConfig.IgnoreCommandLineOptions = True

# NanoAODTools imports
from PhysicsTools.NanoAODTools.postprocessing.framework.datamodel import Collection
from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module

# local imports
from ..helpers.utils import sumP4

# load lumi dict
thisdir = os.path.abspath(os.path.dirname(__file__))
topdir = os.path.abspath(os.path.join(thisdir, '../..'))
datadir = os.path.abspath(os.path.join(topdir, 'data'))
lumi_file = os.path.join(datadir, 'lumi/lumi.json')
with open(lumi_file, 'r') as f: lumi_dict = json.load(f)


class Zcandidate:
    
    def __init__(self, lep1, lep2):
        self.lep1 = lep1
        self.lep2 = lep2
        self.pt = sumP4(self.lep1, self.lep2).Pt()
        self.eta = sumP4(self.lep1, self.lep2).Eta()
        self.phi = sumP4(self.lep1, self.lep2).Phi()
        self.mass = sumP4(self.lep1, self.lep2).M()

class ZZcandidate:

    def __init__(self,Z1,Z2):
        self.Z1 = Z1
        self.Z2 = Z2
        self.pt = sumP4(self.Z1, self.Z2).Pt()
        self.eta = sumP4(self.Z1, self.Z2).Eta()
        self.phi = sumP4(self.Z1, self.Z2).Phi()
        self.mass = sumP4(self.Z1, self.Z2).M()
        #self.mass2 = sumP4(self.Z1, self.Z2).M() seems to be a bug? to see if it is used anywhere...

class HtoZZto4LProducer(Module):
    
    def __init__(self, year, dataset_type, sample):
        
        # copy and check provided arguments
        self.year = year
        self.sample = sample
        self.dataset_type = dataset_type
        allowed_dtypes = ['mc', 'data']
        if self.dataset_type not in allowed_dtypes:
            raise Exception(f'Data type not recognized: {self.dataset_type}.')
        self.isMC = True if self.dataset_type == 'mc' else False

        # define the variables to add to the output tree
        self.lep_vars = ["pt","eta","phi", "pdgId"]
        self.jet_vars = ["pt","eta","phi","mass","bdisc","cvbdisc","cvldisc","gvudsdisc"]
        self.jet_vars_mc = ["hadronFlavour"]
        self.Z_vars = ["pt","eta","phi","mass","onshell_mass","offshell_mass"]
        self.ZZ_vars = ["pt","eta","phi","mass"] 
        self.H_vars = ["pt","eta","phi","mass"]  
        self.H4e_vars=["pt","eta","phi","mass"]
        self.H4mu_vars=["pt","eta","phi","mass"]
        self.H2e2mu_vars=["pt","eta","phi","mass"]  
        self.ZZ4e_vars=["pt","eta","phi","mass"]
        self.ZZ4mu_vars=["pt","eta","phi","mass"]
        self.ZZ2e2mu_vars=["pt","eta","phi","mass"]

        # define the prefixes
        self.mu_prefix = "mu_"
        self.el_prefix = "el_"
        self.lep_prefix = "lep_"
        self.jet_prefix = "jet_"
        self.Z_prefix = "Z_"
        self.ZZ_prefix = "ZZ_"
        self.ZZ4e_prefix = "ZZ4e_"
        self.ZZ4mu_prefix = "ZZ4mu_"
        self.ZZ2e2mu_prefix = "ZZ2e2mu_"
        self.H_prefix = "H_"
        self.H4e_prefix = "H4e_"
        self.H4mu_prefix = "H4mu_"
        self.H2e2mu_prefix = "H2e2mu_"

    def beginJob(self):
        pass

    def endJob(self):
        pass

    def beginFile(self, inputFile, outputFile, inputTree, wrappedOutputTree):
        
        # set output tree
        self.out = wrappedOutputTree
        
        # define lepton branches
        for lep_var in self.lep_vars:
            self.out.branch(self.mu_prefix + lep_var, "F", 20, lenVar="nMu")
            self.out.branch(self.el_prefix + lep_var, "F", 20, lenVar="nEl")
            self.out.branch(self.lep_prefix + lep_var, "F", 20, lenVar="nLep")
        
        # define jet branches
        for jet_var in self.jet_vars:
            self.out.branch(self.jet_prefix + jet_var, "F", 20, lenVar="nJet")
        if self.isMC: 
            for jet_var in self.jet_vars_mc:
                self.out.branch(self.jet_prefix + jet_var, "F", 20, lenVar="nJet")
        
        # define trigger branches
        self.out.branch("HLT_passZZ4lEle", "O")   # pass Ele triggers
        self.out.branch("HLT_passZZ4lMu", "O")    # pass Muon triggers
        self.out.branch("HLT_passZZ4lMuEle", "O") # pass MuEle triggers
        self.out.branch("HLT_passZZ4l", "O")      # pass trigger requirements for the given sample (including sample precedence vetos) 

        # Define luminosity branch
        self.out.branch("lumiwgt", "F")

        # Define branches for the Z candidates
        for Z_var in self.Z_vars:
            self.out.branch(self.Z_prefix + Z_var, "F", 20, lenVar="nZ")

        # Define branches for the ZZ candidates
        for ZZ_var in self.ZZ_vars:
            self.out.branch(self.ZZ_prefix + ZZ_var, "F", 20, lenVar="nZZ")

        for ZZ4e_var in self.ZZ4e_vars:
            self.out.branch(self.ZZ4e_prefix + ZZ4e_var, "F", 20, lenVar="nZZ4e")

        for ZZ4mu_var in self.ZZ4mu_vars:
            self.out.branch(self.ZZ4mu_prefix + ZZ4mu_var, "F", 20, lenVar="nZZ4mu")

        for ZZ2e2mu_var in self.ZZ2e2mu_vars:
            self.out.branch(self.ZZ2e2mu_prefix + ZZ2e2mu_var, "F", 20, lenVar="nZZ2e2mu")

        # Define branches for the H candidates
        for H_var in self.H_vars:
            self.out.branch(self.H_prefix + H_var, "F", 20, lenVar="nH")

        for H4e_var in self.H4e_vars:
            self.out.branch(self.H4e_prefix + H4e_var, "F", 20, lenVar="nH4e")

        for H4mu_var in self.H4mu_vars:
            self.out.branch(self.H4mu_prefix + H4mu_var, "F", 20, lenVar="nH4mu")

        for H2e2mu_var in self.H2e2mu_vars:
            self.out.branch(self.H2e2mu_prefix + H2e2mu_var, "F", 20, lenVar="nH2e2mu")
        
    def endFile(self, inputFile, outputFile, inputTree, wrappedOutputTree):
        pass

    def analyze(self, event):
        '''
        Analyze a single event.
        Note: if returns False, the rest of the event is skipped;
              if returns True, continues to the next analyzer for the same event.
        '''

        # skip event if no good primary vertices are found
        if event.PV_npvsGood < 1: return False

        # apply trigger selection
        if self._select_triggers(event) is False: return False

        # select good muon and electron candidates
        self._select_muons(event)
        self._select_electrons(event)  
        event.selectedLeptons = event.selectedMuons + event.selectedElectrons
        if len(event.selectedLeptons) < 4: return False

        # select good jet candidates
        self._select_jets(event)

        # select good Z candidates 
        self._select_Z_candidates(event)
        if len(event.Zcandidates) < 2: return False
        
        # select ZZ and H candidates
        self._select_ZZ_candidates(event)
        self._select_H_candidates(event)
        
        # fill all event info to the output tree
        self._fill_event_info(event)
        return True


    def _select_triggers(self, event):

        passTrigger = False 
        out_data = {}
        if self.year == "2022" or self.year == "2022EE" :
            # (note: checked that these are unprescaled in run 359751)
            passSingleEle = event.HLT_Ele30_WPTight_Gsf
            passSingleMu = event.HLT_IsoMu24
            passDiEle = (event.HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL
                         or event.HLT_DoubleEle25_CaloIdL_MW)
            passDiMu = event.HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ_Mass3p8
            passMuEle = (event.HLT_Mu23_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL
                         or event.HLT_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL_DZ
                         or event.HLT_Mu12_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL_DZ
                         or event.HLT_Mu23_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL_DZ
                         or event.HLT_DiMu9_Ele9_CaloIdL_TrackIdL_DZ
                         or event.HLT_Mu8_DiEle12_CaloIdL_TrackIdL_DZ)
            passTriEle = False
            passTriMu = event.HLT_TripleMu_10_5_5_DZ or event.HLT_TripleMu_12_10_5
        elif self.year == "2023" or self.year == "2023BPix" :
            # note: checked that these are unprescaled.
            # reference twikis:
            # - https://twiki.cern.ch/twiki/bin/view/CMS/EgHLTRunIIISummary
            # - https://twiki.cern.ch/twiki/bin/view/CMS/MuonHLT2023
            passSingleEle = event.HLT_Ele30_WPTight_Gsf
            passSingleMu = event.HLT_IsoMu24
            passDiEle = event.HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL
            passDiMu = event.HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ_Mass3p8
            passMuEle = event.HLT_Mu23_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL
            passTriEle = False
            passTriMu = event.HLT_TripleMu_10_5_5_DZ or event.HLT_TripleMu_12_10_5
        else:
            print(f"Year {self.year} not found")

        if self.isMC or self.sample == "any" :
            passTrigger = (passDiEle or passDiMu or passMuEle or
                           passTriEle or passTriMu
                           or passSingleEle or passSingleMu)
        else:
            # note: for data it is important to ensure that each event is taken only
            #       from a single primary dataset (called "sample" here).
            if self.sample == "" : raise Exception("Sample must be set in data")
            if (self.sample in ["DoubleEle", "DoubleEG", "EGamma"] and (passDiEle or passTriEle)) \
               or (self.sample in ["Muon", "DoubleMu", "DoubleMuon"] and (passDiMu or passTriMu) and not passDiEle and not passTriEle) \
               or (self.sample in ["MuEG", "MuonEG"] and passMuEle and not passDiEle and not passTriEle and not passDiMu and not passTriMu) \
               or (self.sample in ["SingleElectron", "EGamma"] and passSingleEle and not passMuEle and not passDiMu and not passTriMu and not passDiEle and not passTriEle) \
               or (self.sample in ["SingleMuon", "Muon"] and passSingleMu and not passSingleEle and not passMuEle and not passDiMu and not passTriMu and not passDiEle and not passTriEle):
                passTrigger = True

        self.out.fillBranch("HLT_passZZ4lEle", passSingleEle or passDiEle or passTriEle)
        self.out.fillBranch("HLT_passZZ4lMu", passSingleMu or passDiMu or passTriMu)
        self.out.fillBranch("HLT_passZZ4lMuEle", passMuEle)
        self.out.fillBranch("HLT_passZZ4l", passTrigger)

        return passTrigger


    def _select_Z_candidates(self, event):

        event.Zcandidates = []
        
        # loop over all pairs of leptons
        lepton_pairs = list(itertools.combinations(event.selectedLeptons, 2))
        for lepton_pair in lepton_pairs:
            
            # select same flavor and opposite charge
            if (lepton_pair[0].pdgId + lepton_pair[1].pdgId) != 0: continue
            
            # put negative charged lepton always as lep1 (useful later)
            lep1, lep2 = (lepton_pair[0], lepton_pair[1]) if lepton_pair[0].pdgId < 0 else (lepton_pair[1], lepton_pair[0])
            
            # build Z candidate
            Zcand = Zcandidate(lep1,lep2)
            
            # apply (loose) mass window
            if Zcand.mass < 12 or Zcand.mass > 120: continue
        
            # add Z candidate to collection
            event.Zcandidates.append(Zcand)


    def _flag_onshell_and_offshell_Z(self, Zcand_pair):
        # determine which of both Z candidates is on-shell, and which is off-shell
        # (based on which |mZcandidate - mZ| is the smallest) 
        Z1 = Zcand_pair[0]
        Z2 = Zcand_pair[1]        
        mZ = 91.1876
        d_mZ1_mZ = abs( Z1.mass - mZ )
        d_mZ2_mZ = abs( Z2.mass - mZ )
        onshell_idx = 0 if d_mZ1_mZ < d_mZ2_mZ else 1
        offshell_idx = 1 if d_mZ1_mZ < d_mZ2_mZ else 0
        Zcand_pair[onshell_idx].is_onshell = True
        Zcand_pair[offshell_idx].is_onshell = False
        
        
    def _select_ZZ_candidates(self, event):
        
        event.ZZcandidates = []
        mZ = 91.1876

        # loop over pairs of Z candidates                
        Zcand_pairs = list(itertools.combinations(event.Zcandidates, 2))
        for Zcand_pair in Zcand_pairs:
            
            # determine which one is on-shell and which one is off-shell,
            # and put the on-shell one first.
            # (in other words, put the one with smallest |mZcandidate - mZ| first)
            self._flag_onshell_and_offshell_Z(Zcand_pair) 
            Z1, Z2 = (Zcand_pair[0], Zcand_pair[1]) if Zcand_pair[0].is_onshell else (Zcand_pair[1], Zcand_pair[0])
  
            # apply mass cut on on-shell Z candidate 
            if Z1.mass < 40: continue  
            
            leptons = [Z1.lep1, Z1.lep2, Z2.lep1, Z2.lep2] 
            
            # two distinct leptons must pass pt > 10 and pt > 20
            num_passed_pt20 = 0
            num_passed_pt10 = 0
            for lep in leptons:
                if lep.pt > 20: num_passed_pt20 += 1
                elif lep.pt > 10: num_passed_pt10 += 1
            if num_passed_pt20 == 0 or (num_passed_pt10 + num_passed_pt20) < 2: continue

            # loop over all pairs of leptons that make the two Z candidates 
            lepton_pairs = list(itertools.combinations(leptons, 2))
            dr_ll_values = [] # between each of the four leptons (Ghost removal: all pairs)
            m_ll_values = [] # between each of the four leptons (QCD suppression: opposite-sign pairs and same flavour)                     
            for lepton_pair in lepton_pairs:
                lep1 = lepton_pair[0]
                lep2 = lepton_pair[1]
                dr = math.sqrt( (lep1.eta - lep2.eta)**2 + (lep1.phi - lep2.phi)**2 ) 
                dr_ll_values.append(dr)
                if (lep1.pdgId + lep2.pdgId) == 0:
                    m_ll = sumP4(lep1, lep2).M()
                    m_ll_values.append(m_ll)
            if any(dr < 0.02 for dr in dr_ll_values): continue
            if any(m_ll < 4 for m_ll in m_ll_values): continue
            
            # check alternative pairing (4e or 4mu)
            if abs(Z1.lep1.pdgId) == abs(Z1.lep2.pdgId) == abs(Z2.lep1.pdgId) == abs(Z2.lep2.pdgId):

                # define Za as the one closest to Z mass, and Zb as the other pair
                Ztemp1 = Zcandidate(Z1.lep1, Z2.lep2)
                Ztemp2 = Zcandidate(Z2.lep1, Z1.lep2)
                Za, Zb = (Ztemp1, Ztemp2) if ( abs(Ztemp1.mass - mZ) < abs(Ztemp2.mass - mZ) ) else (Ztemp2, Ztemp1)
                                
                # reject if |mZa - mZ| < |mZ1 - mZ| and mZb < 12
                if ( abs(Za.mass - mZ) < abs(Z1.mass - mZ) ) and Zb.mass < 12: continue

            # reject if inv mass of 4-lepton system < 70            
            m_4l = sumP4(Z1.lep1, Z1.lep2, Z2.lep1, Z2.lep2).M()
            if m_4l < 70: continue
            
            # add result to collection 
            ZZcand = ZZcandidate(Z1,Z2)
            event.ZZcandidates.append(ZZcand)      
            

    def _select_H_candidates(self, event):
        # pick the best H candidate from a set of ZZ candidates

        mZ = 91.1876
        
        def best_candidate_comparator(a, b):
            # note: return -1 means a is better;
            #       return 1 means b is better.
            if abs(a.Z1.mass - b.Z1.mass) < 1e-4 :
                if a.Z2.lep1.pt + a.Z2.lep2.pt > b.Z2.lep1.pt + b.Z2.lep2.pt: return -1
                else: return 1
            else:
                if abs(a.Z1.mass - 91.1876) < abs(b.Z1.mass - 91.1876): return -1
                else: return 1

        event.Hcandidates = []
        if len(event.ZZcandidates) == 0: return
        best_candidate = min(event.ZZcandidates, key=cmp_to_key(best_candidate_comparator))
        event.Hcandidates.append(best_candidate)

        
    ## taken from here https://github.com/CJLST/ZZAnalysis/blob/Run3/NanoAnalysis/python/nanoZZ4lAnalysis.py    
    def _select_muons(self, event):

        event.selectedMuons = []
        muons = Collection(event, "Muon")
        for mu in muons:
            
            passMuID = mu.isPFcand or (mu.highPtId > 0 and mu.pt > 200)
            if( mu.pt > 5 and abs(mu.eta) < 2.4
                and mu.dxy < 0.5 and mu.dz < 1
                and abs(mu.sip3d) < 4 and mu.pfRelIso03_all < 0.35
                and passMuID and (mu.isGlobal or (mu.isTracker and mu.nStations > 0)) ):
                mu._wp_ID = 'TightID'
                mu._wp_Iso = 'LoosePFIso'
                event.selectedMuons.append(mu)
            

    ## taken from here https://github.com/CJLST/ZZAnalysis/blob/Run3/NanoAnalysis/python/nanoZZ4lAnalysis.py       
    def _select_electrons(self, event):

        event.selectedElectrons = []
        electrons = Collection(event, "Electron")
        for el in electrons:
            el.etaSC = el.eta + el.deltaEtaSC
            if( el.pt > 7 and abs(el.eta) < 2.5
                and el.dxy < 0.5 and el.dz < 1
                and abs(el.sip3d) < 4 ):
                el._wp_ID = 'wp90iso'
                
                ## https://github.com/CJLST/ZZAnalysis/blob/Run3/NanoAnalysis/python/getEleBDTCut.py#L22-L31
                # todo: check if this is still needed and if there isn't a cleaner solution
                if abs(el.etaSC) < 0.8:
                    if el.pt < 10:
                        if el.mvaIso < 0.9044286167: continue
                    else:
                        if el.mvaIso < 0.1968600840: continue
                elif 0.8 < abs(el.etaSC) < 1.479:
                    if el.pt < 10:
                        if el.mvaIso < 0.9094166886: continue
                    else:
                        if el.mvaIso < 0.0759172100: continue                  
                else: # |el.etaSC| > 1.479
                    if el.pt < 10:
                        if el.mvaIso < 0.9443653660: continue
                    else:
                        if el.mvaIso < -0.5169136775: continue                      
                                    
                event.selectedElectrons.append(el)


    def _select_jets(self, event):

        event.selectedJets = []
        jets = Collection(event, "Jet")
        FsrPhotons = Collection(event, "FsrPhoton")

        for jet in jets:

            # basic kinematic selection
            if( jet.pt <= 20 or abs(jet.eta) >= 2.5 ): continue
            
            # skip jet if it overlaps with selected leptons
            jet_isolated = True
            for lep in event.selectedLeptons:
                dR_jet_lep = math.sqrt( (lep.eta - jet.eta)**2 + (lep.phi - jet.phi)**2 ) 
                if dR_jet_lep <= 0.4: jet_isolated = False
            if not jet_isolated: continue
            
            # skip jet if it overlaps with FSR photons
            photon_isolated = True
            for photon in FsrPhotons:
                dR_jet_photon = math.sqrt( (photon.eta - jet.eta)**2 + (photon.phi - jet.phi)**2 ) 
                if dR_jet_photon <= 0.4: photon_isolated = False
            if not photon_isolated: continue                   
            
            event.selectedJets.append(jet)
        

    def _fill_event_info(self, event):
        out_data = {}
        
        out_data["lumiwgt"] = lumi_dict[self.year]

        ## leptons
        leptons_pt_sorted = sorted(event.selectedLeptons, key=lambda particle: particle.pt, reverse=True)

        lep_pt = []
        lep_eta = []
        lep_phi = []
        lep_pdgId=[]
        el_pt = []
        el_eta = []
        el_phi = []
        el_pdgId =[]
        mu_pt = []
        mu_eta = []
        mu_phi = []
        mu_pdgId = []
        for lep in leptons_pt_sorted:
            lep_pt.append(lep.pt)
            lep_eta.append(lep.eta)
            lep_phi.append(lep.phi)
            lep_pdgId.append(lep.pdgId)
            if abs(lep.pdgId) == 11: # el
                el_pt.append(lep.pt)
                el_eta.append(lep.eta)
                el_phi.append(lep.phi)
                el_pdgId.append(lep.pdgId)
            if abs(lep.pdgId) == 13: # mu
                mu_pt.append(lep.pt)
                mu_eta.append(lep.eta)
                mu_phi.append(lep.phi)
                mu_pdgId.append(lep.pdgId)            
            
        out_data[self.lep_prefix + "pt"] = lep_pt
        out_data[self.lep_prefix + "eta"] = lep_eta
        out_data[self.lep_prefix + "phi"] = lep_phi
        out_data[self.lep_prefix + "pdgId"] = lep_pdgId
        out_data[self.el_prefix + "pt"] = el_pt
        out_data[self.el_prefix + "eta"] = el_eta
        out_data[self.el_prefix + "phi"] = el_phi 
        out_data[self.el_prefix + "pdgId"] = el_pdgId     
        out_data[self.mu_prefix + "pt"] = mu_pt
        out_data[self.mu_prefix + "eta"] = mu_eta
        out_data[self.mu_prefix + "phi"] = mu_phi
        out_data[self.mu_prefix + "pdgId"] = mu_pdgId
                    
        ## jets  
        ak4_bdisc = []
        ak4_cvbdisc = []
        ak4_cvldisc = []
        ak4_gvudsdisc = []
        ak4_pt = []
        ak4_eta = []
        ak4_phi = []
        ak4_mass = []
        ak4_hadronFlavour = []
        
        for jet in event.selectedJets:
            # ak4_bdisc.append(jet.btagDeepFlavB)
            # ak4_cvbdisc.append(jet.btagDeepFlavCvB)
            # ak4_cvldisc.append(jet.btagDeepFlavCvL)
            # ak4_gvudsdisc.append(jet.btagDeepFlavQG)
            ak4_pt.append(jet.pt)
            ak4_eta.append(jet.eta)
            ak4_phi.append(jet.phi)
            ak4_mass.append(jet.mass)
            if self.isMC: ak4_hadronFlavour.append(jet.hadronFlavour)
        
        # out_data[self.jet_prefix + "bdisc"] = ak4_bdisc
        # out_data[self.jet_prefix + "cvbdisc"] = ak4_cvbdisc
        # out_data[self.jet_prefix + "cvldisc"] = ak4_cvldisc 
        # out_data[self.jet_prefix + "gvudsdisc"] = ak4_gvudsdisc 
        out_data[self.jet_prefix + "pt"] = ak4_pt 
        out_data[self.jet_prefix + "eta"] = ak4_eta 
        out_data[self.jet_prefix + "phi"] = ak4_phi 
        out_data[self.jet_prefix + "mass"] = ak4_mass 
        if self.isMC: out_data[self.jet_prefix + "hadronFlavour"] = ak4_hadronFlavour 
           
        ## Z candidates
        Zcandidate_mass = []
        Zcandidate_pt = []
        Zcandidate_eta = []
        Zcandidate_phi = []
        Zcandidate_onshell_mass = []
        Zcandidate_offshell_mass = []
        for Zcandidate in event.Zcandidates:
            Zcandidate_mass.append(Zcandidate.mass)
            Zcandidate_pt.append(Zcandidate.pt)
            Zcandidate_eta.append(Zcandidate.eta)
            Zcandidate_phi.append(Zcandidate.phi)
            if Zcandidate.is_onshell: Zcandidate_onshell_mass.append(Zcandidate.mass)
            else: Zcandidate_offshell_mass.append(Zcandidate.mass)

                
        out_data[self.Z_prefix + "mass"] = Zcandidate_mass
        out_data[self.Z_prefix + "pt"] = Zcandidate_pt
        out_data[self.Z_prefix + "eta"] = Zcandidate_eta 
        out_data[self.Z_prefix + "phi"] = Zcandidate_phi 
        out_data[self.Z_prefix + "onshell_mass"] = Zcandidate_onshell_mass
        out_data[self.Z_prefix + "offshell_mass"] = Zcandidate_offshell_mass

        ## ZZ candidates
        # Initialize output lists
        ZZcandidate_mass = []
        ZZcandidate_mass_4e=[]
        ZZcandidate_mass_4mu=[]
        ZZcandidate_mass_2e2mu=[]
        ZZcandidate_pt = []
        ZZcandidate_eta = []
        ZZcandidate_phi = []

        for ZZcandidate in event.ZZcandidates:
            ZZcandidate_mass.append(ZZcandidate.mass)
            ZZcandidate_pt.append(ZZcandidate.pt)
            ZZcandidate_eta.append(ZZcandidate.eta)
            ZZcandidate_phi.append(ZZcandidate.phi)

            # Extract PDG IDs
            lep_ids = {
                abs(ZZcandidate.Z1.lep1.pdgId),
                abs(ZZcandidate.Z1.lep2.pdgId),
                abs(ZZcandidate.Z2.lep1.pdgId),
                abs(ZZcandidate.Z2.lep2.pdgId)
            }

            # Classify by decay channel
            if lep_ids == {11}:  
                ZZcandidate_mass_4e.append(ZZcandidate.mass)
            elif lep_ids == {13}:  
                ZZcandidate_mass_4mu.append(ZZcandidate.mass)
            elif lep_ids == {11, 13}:  
                ZZcandidate_mass_2e2mu.append(ZZcandidate.mass)

        # Store in output dictionary
        out_data[self.ZZ_prefix + "mass"] = ZZcandidate_mass
        out_data[self.ZZ4e_prefix + "mass"] = ZZcandidate_mass_4e
        out_data[self.ZZ4mu_prefix + "mass"] = ZZcandidate_mass_4mu
        out_data[self.ZZ2e2mu_prefix + "mass"] = ZZcandidate_mass_2e2mu
        out_data[self.ZZ_prefix + "pt"] = ZZcandidate_pt
        out_data[self.ZZ_prefix + "eta"] = ZZcandidate_eta
        out_data[self.ZZ_prefix + "phi"] = ZZcandidate_phi

        # Similar structure for Higgs candidates
        Hcandidate_mass = []
        Hcandidate_mass_4e=[]
        Hcandidate_mass_4mu=[]
        Hcandidate_mass_2e2mu=[]
        Hcandidate_pt = []
        Hcandidate_eta = []
        Hcandidate_phi = []

        for Hcandidate in event.Hcandidates:
            Hcandidate_mass.append(Hcandidate.mass)
            Hcandidate_pt.append(Hcandidate.pt)
            Hcandidate_eta.append(Hcandidate.eta)
            Hcandidate_phi.append(Hcandidate.phi)

            # Extract PDG IDs
            lep_ids = {
                abs(Hcandidate.Z1.lep1.pdgId),
                abs(Hcandidate.Z1.lep2.pdgId),
                abs(Hcandidate.Z2.lep1.pdgId),
                abs(Hcandidate.Z2.lep2.pdgId)
            }

            # Classify by decay channel
            if lep_ids == {11}:  
                Hcandidate_mass_4e.append(Hcandidate.mass)
            elif lep_ids == {13}:  
                Hcandidate_mass_4mu.append(Hcandidate.mass)
            elif lep_ids == {11, 13}:  
                Hcandidate_mass_2e2mu.append(Hcandidate.mass)
                
        out_data[self.H_prefix + "mass"] = Hcandidate_mass
        out_data[self.H4e_prefix + "mass"] = Hcandidate_mass_4e
        out_data[self.H4mu_prefix + "mass"] = Hcandidate_mass_4mu
        out_data[self.H2e2mu_prefix + "mass"] =  Hcandidate_mass_2e2mu
        out_data[self.H_prefix + "pt"] = Hcandidate_pt
        out_data[self.H_prefix + "eta"] = Hcandidate_eta 
        out_data[self.H_prefix + "phi"] = Hcandidate_phi 
                
        # if self.isMC:
        #     out_data["l1PreFiringWeight"] = event.L1PreFiringWeight_Nom                
                
        ## fill all branches
        for key in out_data:
            self.out.fillBranch(key, out_data[key])
            
        return True
