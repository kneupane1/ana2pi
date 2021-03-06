#ifndef EPPROCESSOR_CXX
#define EPPROCESSOR_CXX

#include "ep_processor.h"

EpProcessor::EpProcessor(TDirectory *td, DataAna* dataAna, TString h10type, Bool_t mon, Bool_t monOnly /*= kFALSE*/) {
	_isFirstProc = kFALSE;
	pass = kFALSE;
	mMon = mon;
	mMonOnly = monOnly;

	for(Int_t iProcMode=0;iProcMode<nPROCMODE;iProcMode++){
		for(Int_t iEvtSel=0;iEvtSel<nEVTSEL;iEvtSel++){
			//hists[iProcMode][iEvtSel] = NULL;
			//histsEkin[iProcMode][iEvtSel] = NULL;
			hists[iProcMode][iEvtSel] = new TObjArray*[nSECTOR];
			histsEkin[iProcMode][iEvtSel] = new TObjArray*[nSECTOR];
			for(Int_t iSector=0;iSector<nSECTOR;iSector++){
				hists[iProcMode][iEvtSel][iSector] = NULL;
				histsEkin[iProcMode][iEvtSel][iSector] = NULL;
			}
		}
	}
		
	if (td != NULL) dirout = td;
	else dirout = gDirectory;
	TDirectory* dirMother = (TDirectory*)dirout->GetMother();
	if (dirMother!=NULL && dirMother->GetListOfKeys()->GetEntries() == 1) _isFirstProc=kTRUE;
	if (_isFirstProc) Info("EpProcessor::EpProcessor()", "%s isFirstProc!\n", td->GetName());
				
	if (dataAna != NULL) dAna = dataAna;
	
	/* Determint h10type */
	is_h10e1f = is_h10e16 = is_h10exp = is_h10sim = kFALSE;
	TObjArray *h10type_tokens = h10type.Tokenize(":");
	h10exp   = h10type_tokens->At(0)->GetName();
	h10dtype = h10type_tokens->At(1)->GetName();
	if (h10type_tokens->GetEntries() == 3) h10skim = h10type_tokens->At(2)->GetName();
	
	if (h10exp.EqualTo("e1f")) is_h10e1f = kTRUE;
	else if (h10exp.EqualTo("e16")) is_h10e16 = kTRUE;
	else Info("EpProcessor::EpProcessor()", "Could not determine h10type.experiment!\n");
	
	if (h10dtype.EqualTo("exp")) is_h10exp = kTRUE;
	else if (h10dtype.EqualTo("sim")) is_h10sim = kTRUE;
	else Info("EpProcessor::EpProcessor()", "Could not determine h10type.dtype!\n");
	
	Info("EpProcessor::EpProcessor()", "EpProcessor intitialized with following h10type: %s:%s:%s\n", h10exp.Data(), h10dtype.Data(), h10skim.Data());
	/* *** */
		
	next = 0;
}

EpProcessor::~EpProcessor(){
	Info("~EpProcessor()", "");
	for(Int_t iProcMode=0;iProcMode<nPROCMODE;iProcMode++){
		for(Int_t iEvtSel=0;iEvtSel<nEVTSEL;iEvtSel++){
			//dAna->deleteHists(hists[iProcMode][iEvtSel]);
			//dAna->deleteHists(histsEkin[iProcMode][iEvtSel]);
			for(Int_t iSector=0;iSector<nSECTOR;iSector++){
				delete hists[iProcMode][iEvtSel][iSector];
				delete histsEkin[iProcMode][iEvtSel][iSector];
			}
			delete hists[iProcMode][iEvtSel];
			delete histsEkin[iProcMode][iEvtSel];
		}
	}
}

void EpProcessor::add(EpProcessor *n) {
	if (next) next->add(n);
	else next = n;
}

void EpProcessor::setNext(EpProcessor *n) {
	next = n;
}

Bool_t EpProcessor::isFirstProc(){
	return _isFirstProc;
}

void EpProcessor::handle(DataH10* dH10) {
	//printf("In EpProcessor::handle\n");
	if (next) next->handle(dH10);
}

void EpProcessor::write(){
	Info("EpProcessor::write()", "");
	if(hevtsum!= NULL){
		dirout->cd();
		hevtsum->Write();
	}
	TDirectory* _dirout;
	for(Int_t iProcMode=0;iProcMode<nPROCMODE;iProcMode++){
		for(Int_t iEvtSel=0;iEvtSel<nEVTSEL;iEvtSel++){
			for(Int_t iSector=0;iSector<nSECTOR;iSector++){
				if (iProcMode == iMODE_MON && iEvtSel == iEVTINC){
					_dirout = dirout->GetDirectory(TString::Format("mon/sector%d", iSector));
					if (_dirout != NULL) _dirout->cd();
				}else if (iProcMode == iMODE_MON && iEvtSel != iEVTINC){
					_dirout = dirout->GetDirectory(TString::Format("mon%d/sector%d", iEvtSel, iSector));
					if (_dirout != NULL) _dirout->cd();
				}else if (iProcMode == iMODE_CUT){
					_dirout = dirout->GetDirectory(TString::Format("cut/sector%d", iSector));
					if (_dirout != NULL) _dirout->cd();
				}
				if (hists[iProcMode][iEvtSel][iSector] != NULL) {
					//Info("EpProcessor::write()", "hists[%d][%d][%d]", iProcMode, iEvtSel, iSector);
					//dAna->writeHists(hists[iProcMode][iEvtSel], _dirout);
					hists[iProcMode][iEvtSel][iSector]->Write();
					//Info("EpProcessor::write()", "done hists[%d][%d][%d]", iProcMode, iEvtSel, iSector);
				}
				if (histsEkin[iProcMode][iEvtSel][iSector] != NULL)	{
					//Info("EpProcessor::write()", "histsEkin[%d][%d]", iProcMode, iEvtSel);
					//dAna->writeHists(histsEkin[iProcMode][iEvtSel], _dirout);
					histsEkin[iProcMode][iEvtSel][iSector]->Write();
					//Info("EpProcessor::write()", "done histsEkin[%d][%d]", iProcMode, iEvtSel);
				}
			}
		}
	}
}

#endif // EPPROCESSOR_H
