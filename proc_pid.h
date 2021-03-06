#ifndef PROCPID_H
#define PROCPID_H

#include "ep_processor.h" // Base class: EpProcessor
#include "data_h10.h"
#include "particle_constants.h"

using namespace ParticleConstants;

class ProcPid : public EpProcessor
{

public:
	ProcPid(TDirectory *td,DataAna* dataAna,TString h10type, 
		    Bool_t mon=kFALSE,Bool_t monOnly=kFALSE);
	~ProcPid();

	void handle(DataH10* dH10);
	//void write();
				
protected:
	Int_t _h10idxP;
	Int_t _h10idxPip;
	Int_t _h10idxPim;
	
	static const Int_t NUM_EVTCUTS = 18;
	enum { EVT_NULL, EVT, EVT_TRK,
		   EVT_SPACE1, 	
		   EVT_TRK_POS, EVT_TRK_POS_DC, EVT_TRK_POS_SC, EVT_TRK_POS_BOSP, EVT_TRK_POS_BOSPIP,
		   EVT_SPACE2,
	       EVT_TRK_NEG, EVT_TRK_NEG_DC, EVT_TRK_NEG_SC, EVT_TRK_NEG_BOSPIM,
	       EVT_SPACE3,
	       EVT_PPIP_EX, EVT_PPIM_EX, EVT_PIPPIM_EX, EVT_PPIPPIM_EX
	};     
	     
	void updatePid(DataH10* dH10);
	Float_t getCCtheta(Float_t x_sc, Float_t y_sc, Float_t z_sc, Float_t cx_sc, Float_t cy_sc, Float_t cz_sc);
};

ProcPid::ProcPid(TDirectory *td, DataAna* dataAna, TString h10type, 
                 Bool_t mon/* = kFALSE*/,Bool_t monOnly /*= kFALSE*/)
                 :EpProcessor(td, dataAna, h10type, mon, monOnly)
{
	td->cd();	
	hevtsum = new TH1D("hevtsum","Event Statistics",NUM_EVTCUTS,0.5,NUM_EVTCUTS+0.5);
	hevtsum->SetMinimum(0);
	hevtsum->GetXaxis()->SetBinLabel(EVT,"Total");
	hevtsum->GetXaxis()->SetBinLabel(EVT_TRK,"Charged Tracks");
	
	hevtsum->GetXaxis()->SetBinLabel(EVT_TRK_POS,"+ve");
	hevtsum->GetXaxis()->SetBinLabel(EVT_TRK_POS_DC,"+ve DC");
	hevtsum->GetXaxis()->SetBinLabel(EVT_TRK_POS_SC,"+ve SC");
	hevtsum->GetXaxis()->SetBinLabel(EVT_TRK_POS_BOSP,"+ve = BOS p");
	hevtsum->GetXaxis()->SetBinLabel(EVT_TRK_POS_BOSPIP,"+ve = BOS #pi^{+}");
	
	hevtsum->GetXaxis()->SetBinLabel(EVT_TRK_NEG, "-ve");
	hevtsum->GetXaxis()->SetBinLabel(EVT_TRK_NEG_DC,"-ve DC");
	hevtsum->GetXaxis()->SetBinLabel(EVT_TRK_NEG_SC,"-ve SC");
	hevtsum->GetXaxis()->SetBinLabel(EVT_TRK_NEG_BOSPIM,"-ve = BOS  #pi^{-}");
	
	hevtsum->GetXaxis()->SetBinLabel(EVT_PPIP_EX,"e^{-} + p + #pi^{+}");
	hevtsum->GetXaxis()->SetBinLabel(EVT_PPIM_EX,"e^{-} + p + #pi^{-}");
	hevtsum->GetXaxis()->SetBinLabel(EVT_PIPPIM_EX,"e^{-} + #pi^{+} + #pi^{-}");
	hevtsum->GetXaxis()->SetBinLabel(EVT_PPIPPIM_EX,"e^{-} + p + #pi^{+} + #pi^{-}");
}

ProcPid::~ProcPid()
{
	
}

void ProcPid::handle(DataH10* dH10)
{
	//Info("ProcPid::handle()", "");
	pass = kFALSE;
	
	hevtsum->Fill(EVT);
	
	if (mMon||mMonOnly)
	{
		if (dAna->top==0 && hists[iMODE_MON][iEVTINC][iSECTOR0]==NULL) { //i.e. inclusive event
			TDirectory* dirmon = dirout->mkdir(TString::Format("mon"));
			dAna->makeHistsPid(hists[iMODE_MON][iEVTINC], dirmon);
		}else if(dAna->top!=0 && hists[iMODE_MON][iTOP1][iSECTOR0]==NULL){ //i.e. 2pi event
			for(Int_t iTop=iTOP1;iTop<nTOP;iTop++){
				TDirectory* dirmon = dirout->mkdir(TString::Format("mon%d",iTop));
				dAna->makeHistsPid(hists[iMODE_MON][iTop], dirmon);
			}
		}
	
	
		updatePid(dH10);
		if (dAna->top == 0) { //i.e inclusive event
			dAna->fillHistsPid(hists[iMODE_MON][iEVTINC]);
		}else { //i.e 2pi event
			dAna->fillHistsPid(hists[iMODE_MON][dAna->top-1]);
		}
	}
	
		
	if (mMonOnly){
		pass = kTRUE;
		EpProcessor::handle(dH10);
		return;
	}	
	
	//pid cut
	dAna->pid.h10IdxP = dAna->pid.h10IdxPip = dAna->pid.h10IdxPim = 0; //atrivedi 041713: First reset indices set in monitoring mode; better soln?
	for (Int_t i = 1; i < dH10->gpart; i++) {
		hevtsum->Fill(EVT_TRK);
		
		if(dH10->q[i]==1){
			hevtsum->Fill(EVT_TRK_POS);
			if (dH10->dc[i]>0) {
				hevtsum->Fill(EVT_TRK_POS_DC);
				if (dH10->sc[i]>0) {
					hevtsum->Fill(EVT_TRK_POS_SC);
					if (dH10->id[i]==PROTON){
						hevtsum->Fill(EVT_TRK_POS_BOSP);
						dH10->id[i]=PROTON;
						dAna->pid.h10IdxP = i;
					}
					if (dH10->id[i]==PIP){
						hevtsum->Fill(EVT_TRK_POS_BOSPIP);
						dH10->id[i]=PIP;
						dAna->pid.h10IdxPip = i;
					}
				}
			}
		}else if(dH10->q[i]==-1){
			hevtsum->Fill(EVT_TRK_NEG);
			if (dH10->dc[i]>0) {
				hevtsum->Fill(EVT_TRK_NEG_DC);
				if (dH10->sc[i]>0) {
					hevtsum->Fill(EVT_TRK_NEG_SC);
					if (dH10->id[i]==PIM){
						hevtsum->Fill(EVT_TRK_NEG_BOSPIM);
						dH10->id[i]=PIM;
						dAna->pid.h10IdxPim = i;
					}
				}
			}
		}
		
	}
	if(dAna->skimq.isEVT_2POS_EX && dAna->pid.h10IdxP>0 && dAna->pid.h10IdxPip>0) {
		hevtsum->Fill(EVT_PPIP_EX);
		pass = kTRUE;
	}
	if(dAna->skimq.isEVT_1POS1NEG_EX){
		if(dAna->pid.h10IdxP>0 && dAna->pid.h10IdxPim>0) {
			hevtsum->Fill(EVT_PPIM_EX);
			pass = kTRUE;
		}
		if(dAna->pid.h10IdxPip>0 && dAna->pid.h10IdxPim>0) {
			hevtsum->Fill(EVT_PIPPIM_EX);
			pass = kTRUE;
		}
	}
	if(dAna->skimq.isEVT_2POS1NEG_EX && dAna->pid.h10IdxP>0 && dAna->pid.h10IdxPip>0 && dAna->pid.h10IdxPim>0) {
		hevtsum->Fill(EVT_PPIPPIM_EX);
		pass = kTRUE;
	}
	
	if (pass) {
		if (mMon)
		{
			if (hists[iMODE_CUT][iEVTINC][iSECTOR0]==NULL) {
				TDirectory* dircut = dirout->mkdir(TString::Format("cut"));
				dAna->makeHistsPid(hists[iMODE_CUT][iEVTINC], dircut);
			}
			dAna->fillHistsPid(hists[iMODE_CUT][iEVTINC]);
		}
		
		EpProcessor::handle(dH10);
	}
}

void ProcPid::updatePid(DataH10* dH10)
{
	Float_t l_e = dH10->sc_r[dH10->sc[0]-1];
	Float_t t_e = dH10->sc_t[dH10->sc[0]-1];
	Float_t tOFF = t_e-(l_e/SOL);
	
	for (Int_t i = 1; i < dH10->gpart; i++) {
		Float_t p = dH10->p[i];
		Float_t l = dH10->sc_r[dH10->sc[i]-1];
		Float_t t = dH10->sc_t[dH10->sc[i]-1];
		Float_t beta = ( l/(t - tOFF) )/SOL; 
					
		if(dH10->id[i] == PROTON){
			Float_t betaStrP = TMath::Sqrt((p*p)/(MASS_P*MASS_P+p*p));
			Float_t dtP = l/(betaStrP*SOL) + tOFF - t;
			
			dAna->pid.h10IdxP = i;
			dAna->pid.sectorP = dH10->sc_sect[dH10->sc[i]-1];
			dAna->pid.betaP = beta;
			dAna->pid.pP = p;
			dAna->pid.betaStrP = betaStrP;
			dAna->pid.dtP = dtP;
			//from EC
			dAna->pid.P_ec_ei   = dH10->ec_ei[dH10->ec[i]-1];
			dAna->pid.P_ec_eo   = dH10->ec_eo[dH10->ec[i]-1];
			dAna->pid.P_etot    = dH10->etot[dH10->ec[i]-1];
			//from CC
			dAna->pid.P_nphe    = dH10->nphe[dH10->cc[i]-1];
			dAna->pid.P_cc_segm = (dH10->cc_segm[dH10->cc[i]-1]%1000)/10;
			//calculate cc_theta
			Float_t dc_xsc  = dH10->dc_xsc[dH10->dc[i]-1];
			Float_t dc_ysc  = dH10->dc_ysc[dH10->dc[i]-1];
			Float_t dc_zsc  = dH10->dc_zsc[dH10->dc[i]-1];
			Float_t dc_cxsc = dH10->dc_cxsc[dH10->dc[i]-1];
			Float_t dc_cysc = dH10->dc_cysc[dH10->dc[i]-1];
			Float_t dc_czsc = dH10->dc_czsc[dH10->dc[i]-1];
			dAna->pid.P_cc_theta = getCCtheta(dc_xsc, dc_ysc, dc_zsc, dc_cxsc, dc_cysc, dc_czsc);
		}
		if(dH10->id[i] == PIP){
			Float_t betaStrPip = TMath::Sqrt((p*p)/(MASS_PIP*MASS_PIP+p*p));
			Float_t dtPip = l/(betaStrPip*SOL) + tOFF - t;
			
			dAna->pid.h10IdxPip = i;
			dAna->pid.sectorPip = dH10->sc_sect[dH10->sc[i]-1];
			dAna->pid.betaPip = beta;
			dAna->pid.pPip = p;
			dAna->pid.betaStrPip = betaStrPip;
			dAna->pid.dtPip = dtPip;
			//from EC
			dAna->pid.Pip_ec_ei   = dH10->ec_ei[dH10->ec[i]-1];
			dAna->pid.Pip_ec_eo   = dH10->ec_eo[dH10->ec[i]-1];
			dAna->pid.Pip_etot    = dH10->etot[dH10->ec[i]-1];
			//from CC
			dAna->pid.Pip_nphe    = dH10->nphe[dH10->cc[i]-1];
			dAna->pid.Pip_cc_segm = (dH10->cc_segm[dH10->cc[i]-1]%1000)/10;
			//calculate cc_theta
			Float_t dc_xsc  = dH10->dc_xsc[dH10->dc[i]-1];
			Float_t dc_ysc  = dH10->dc_ysc[dH10->dc[i]-1];
			Float_t dc_zsc  = dH10->dc_zsc[dH10->dc[i]-1];
			Float_t dc_cxsc = dH10->dc_cxsc[dH10->dc[i]-1];
			Float_t dc_cysc = dH10->dc_cysc[dH10->dc[i]-1];
			Float_t dc_czsc = dH10->dc_czsc[dH10->dc[i]-1];
			dAna->pid.Pip_cc_theta = getCCtheta(dc_xsc, dc_ysc, dc_zsc, dc_cxsc, dc_cysc, dc_czsc);
		}
		if(dH10->id[i] == PIM){
			Float_t betaStrPim = TMath::Sqrt((p*p)/(MASS_PIM*MASS_PIM+p*p));
			Float_t dtPim = l/(betaStrPim*SOL) + tOFF - t;
			
			dAna->pid.h10IdxPim = i;
			dAna->pid.sectorPim = dH10->sc_sect[dH10->sc[i]-1];
			dAna->pid.betaPim = beta;
			dAna->pid.pPim = p;
			dAna->pid.betaStrPim = betaStrPim;
			dAna->pid.dtPim = dtPim;
			//from EC
			dAna->pid.Pim_ec_ei   = dH10->ec_ei[dH10->ec[i]-1];
			dAna->pid.Pim_ec_eo   = dH10->ec_eo[dH10->ec[i]-1];
			dAna->pid.Pim_etot    = dH10->etot[dH10->ec[i]-1];
			//from CC
			dAna->pid.Pim_nphe    = dH10->nphe[dH10->cc[i]-1];
			dAna->pid.Pim_cc_segm = (dH10->cc_segm[dH10->cc[i]-1]%1000)/10;
			//calculate cc_theta
			Float_t dc_xsc  = dH10->dc_xsc[dH10->dc[i]-1];
			Float_t dc_ysc  = dH10->dc_ysc[dH10->dc[i]-1];
			Float_t dc_zsc  = dH10->dc_zsc[dH10->dc[i]-1];
			Float_t dc_cxsc = dH10->dc_cxsc[dH10->dc[i]-1];
			Float_t dc_cysc = dH10->dc_cysc[dH10->dc[i]-1];
			Float_t dc_czsc = dH10->dc_czsc[dH10->dc[i]-1];
			dAna->pid.Pim_cc_theta = getCCtheta(dc_xsc, dc_ysc, dc_zsc, dc_cxsc, dc_cysc, dc_czsc);
		}
	}
}

Float_t ProcPid::getCCtheta(Float_t x_sc, Float_t y_sc, Float_t z_sc, Float_t cx_sc, Float_t cy_sc, Float_t cz_sc){
	//Define CC plane equation: Ax + By + Cz + D = 0
	Float_t A = -0.000785;
	Float_t B = 0;
	Float_t C = -0.00168;
	Float_t D = 1;
	Float_t magS = TMath::Sqrt(A*A + B*B + C*C);

	//length of line perpendicular to CC plane from hit in SC plane
	Float_t h = 0;

	//cosine of angle between h & t vector
	Float_t cAlpha = 0;

	//magnitude of vector t
	Float_t t = 0;

	h = ((A*x_sc + B*y_sc + C*z_sc) + D)/magS;

	cAlpha = (cx_sc*x_sc + cy_sc*y_sc + cz_sc*z_sc)/magS;

	t = h/cAlpha;

	Float_t x_cc = x_sc - t*cx_sc;
	Float_t y_cc = y_sc - t*cy_sc;
	Float_t z_cc = z_sc - t*cz_sc;

	return TMath::ACos(z_cc/TMath::Sqrt(x_cc*x_cc + y_cc*y_cc + z_cc*z_cc)) * (180/TMath::Pi());
}

#endif // PROCPID_H
