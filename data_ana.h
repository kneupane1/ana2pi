#ifndef DATAANA_H
#define DATAANA_H


#include "data_eid.h"
#include "data_efid.h"
#include "data_pfid.h"
#include "data_pfid_elast.h"
#include "data_eeff.h"
#include "data_skim_q.h"
#include "data_skim_q_elast.h"
#include "data_mom.h"
#include "data_pid.h"
#include "data_pid_new.h"
#include "data_peff.h"
#include "data_pid_elast.h"
#include "data_pid_elast_new.h"
#include "data_ekin.h"
#include "data_2pi.h"
#include "data_h10.h"
#include "data_elastic.h"
#include <TObjArray.h>

class DataAna
{
public:
	DataAna();
	virtual ~DataAna();
	void Clear();
	Int_t opart;
	Int_t h10idxE;
	Int_t h10idxP;
	Int_t h10idxPip;
	Int_t h10idxPim;
	Int_t top;
	
	DataEid eid;
	DataEFid efid;
	DataPFid pfid;
	DataPFidElast pfid_elast;
	DataEEff eeff;
	DataSkimQ skimq;
	DataSkimQElast skimq_elast;
	DataPid pid;
	DataPidNew pidnew;
	DataPEff peff;
	DataPidElast pid_elast;
	DataPidElastNew pid_elastnew;
	DataMom mom;
	DataEkin eKin;
	DataEkin eKin_mc;
	Data2pi d2pi;
	Data2pi d2pi_mc;
	DataElastic dElast;
	DataElastic dElast_ST;
	
	struct h8Dbng{
		Int_t bins;
		Double_t xmin;
		Double_t xmax;
	} bngQ2, bngW, bngMppip, bngMppim, bngMpippim, bngTheta, bngPhi, bngAlpha;
	
	void makeHistsEid(TObjArray** hists, TDirectory* dirout);
	void makeHistsEFid(TObjArray** hists, TDirectory* dirout);
	void makeHistsPFid(TObjArray** hists, TDirectory* dirout);
	void makeHistsPFidElast(TObjArray** hists, TDirectory* dirout);
	void makeHistsEEff(TObjArray** hists, TDirectory* dirout);
	void makeHistsPEff(TObjArray** hists, TDirectory* dirout);
	void makeHistsMomCor(TObjArray** hists, TDirectory* dirout);
	void makeHistsPid(TObjArray** hists, TDirectory* dirout);
	void makeHistsPidMon(TObjArray** hists, TDirectory* dirout);
	void makeHistsPidCut(TObjArray** hists, TDirectory* dirout);
	void makeHistsPidElast(TObjArray** hists, TDirectory* dirout);
	void makeHistsPidElastMon(TObjArray** hists, TDirectory* dirout);
	void makeHistsPidElastCut(TObjArray** hists, TDirectory* dirout);
	void makeHistsEkin(TObjArray** hists, TDirectory* dirout);
	
	TObjArray* makeHistsEkin();
	TObjArray* makeHistsMM();
	TObjArray** makeYields();

	TObjArray* makeHistsMMElastic();
	TObjArray* makeYieldsElastic();
	
	void writeHists(TObjArray** hists, TDirectory *dirout);
	
	void deleteHists(TObjArray** hists);
	
	void fillHistsEid(TObjArray** hists, Bool_t useMc = kFALSE);
    void fillHistsEFid(TObjArray** hists, Bool_t useMc = kFALSE);
    void fillHistsPFid(TObjArray** hists, Bool_t useMc = kFALSE);
    void fillHistsPFidNew(TObjArray** hists, Bool_t useMc = kFALSE);
    void fillHistsPFidElast(TObjArray** hists, Bool_t useMc = kFALSE);
    void fillHistsPFidElastNew(TObjArray** hists, Bool_t useMc = kFALSE);
    void fillHistsEEff(TObjArray** hists, Bool_t useMc = kFALSE);
    void fillHistsPEff(TObjArray** hists, Bool_t useMc = kFALSE);
    void fillHistsPEffNew(TObjArray** hists, Bool_t useMc = kFALSE);
    void fillHistsMomCor(TObjArray** hists, Bool_t useMc = kFALSE);
	void fillHistsPid(TObjArray** hists, Bool_t useMc = kFALSE);
	void fillHistsPidMon(TObjArray** hists, Bool_t useMc = kFALSE);
	void fillHistsPidCut(TObjArray** hists, Bool_t useMc = kFALSE);
	void fillHistsPidElast(TObjArray** hists, Bool_t useMc = kFALSE);
	void fillHistsPidElastMon(TObjArray** hists, Bool_t useMc = kFALSE);
	void fillHistsPidElastCut(TObjArray** hists, Bool_t useMc = kFALSE);
	void fillHistsEkin(TObjArray** hists, Bool_t useMc = kFALSE);
	
	void fillHistsEkin(TObjArray* hists, Bool_t useMc = kFALSE);
	void fillHistsMM(TObjArray *hists, Bool_t useMc = kFALSE);
	void fillYields(TObjArray** hists, Float_t w, Bool_t useMc = kFALSE);

	void fillHistsMMElastic(TObjArray *hists, Bool_t useMc = kFALSE);
	void fillYieldsElastic(TObjArray* hists, Bool_t useMc = kFALSE);

	void addBranches_Data2pi(TTree* t, Bool_t useMc=kFALSE);
	void addBranches_DataElastic(TTree* t, Bool_t useMc=kFALSE);
	void addBranches_DataEid(TTree* t);
	void addBranches_DataPid(TTree* t);
	void addBranches_DataPidNew(TTree* t);
	void addBranches_DataPidElast(TTree* t);
};

#endif // DATAANA_H
