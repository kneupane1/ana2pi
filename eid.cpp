#include "eid.h"
#include <TString.h>

Eid* Eid::ms_instance = 0;

Bool_t Eid::Pass(Int_t sector, Float_t p, Float_t sf)
{
	return ( PassThreshold(p) && PassSF(sector, p, sf) );
}

Bool_t Eid::PassSF(Int_t sector, Float_t p, Float_t sf)
{
	//printf("here\n");
	//printf("sf = %f, p = %f, sector = %d\n", sf, p, sector);
	Double_t ceil = _fpol3High[sector-1]->Eval(p);
	Double_t floor = _fpol3Low[sector-1]->Eval(p);
	//printf("here2\n");
	//printf("sf = %f, p = %f, sector = %d, ceil = %f, floor = %f; pass = %d\n", sf, p, sector, ceil, floor, ( sf>floor && sf<ceil )?1:0);
	return ( sf>floor && sf<ceil );
}

Bool_t Eid::PassThreshold(Float_t p)
{
	return ( p > _ecThreshold );
}

Eid::Eid(char* eidParFileName)
{
	//_fname = "/home/trivedia/CLAS/workspace/ana2pi/eid/eid.exp.out"; //atrivedi
	//_fname = "/home/trivedia/CLAS/workspace/at-ana/eid.out"; //atrivedi
	_fname = eidParFileName; //atrivedi 031213
        eidParFileFound = kTRUE;
	fprintf(stdout, "Reading eid pars from %s\n", _fname.c_str());
	_f.open(_fname.c_str());
	_ecThreshold = 0.5;
	for (Int_t iSector = 0; iSector < 6; iSector++) {
		_mean[iSector][0] = 3.0;
		_sigma[iSector][0] = 3.3;
		_mean[iSector][1] = _mean[iSector][2] = _mean[iSector][3] = 0.0;
		_sigma[iSector][1] = _sigma[iSector][2] = _sigma[iSector][3] = 0.0;
	}
	if (_f.is_open()) {
		_f >> _cutParMap;
		//get EC momentum threshold
		char str_ec_threshold[100];
		sprintf(str_ec_threshold, "ec_threshold");
		sscanf(_cutParMap[str_ec_threshold].c_str(),"%lf",&_ecThreshold);
		//get SFcut parameters
		for (Int_t iSector = 0; iSector < 6; iSector++) {
			for (Int_t iPar = 0; iPar < 4; iPar++) {
				char str_mean[100], str_sigma[100];
				TString parName = TString::Format("%d_SFmean_a%i", iSector+1, iPar);
				sprintf(str_mean, parName.Data());
				parName = TString::Format("%d_SFsigma_a%i", iSector+1, iPar);
				sprintf(str_sigma, parName.Data());
				sscanf(_cutParMap[str_mean].c_str(),"%lf",&_mean[iSector][iPar]);
				sscanf(_cutParMap[str_sigma].c_str(),"%lf",&_sigma[iSector][iPar]);
			}
		}
	} else {
                eidParFileFound = kFALSE;
		fprintf(stdout, "%s not found -- using default electron id parameters!\n", _fname.c_str());
	}
	for (Int_t iSector = 0; iSector < 6; iSector++) {
		TString fname = TString::Format("fpol3Mean_s%i",iSector+1);
		_fpol3Mean[iSector] = new TF1(fname.Data(),"pol3",0,5.5);
		fname = TString::Format("fpol3Low_s%i",iSector+1);
		_fpol3Low[iSector] = new TF1(fname.Data(),"pol3",0,5.5);
		fname = TString::Format("fpol3High_s%i",iSector+1);
		_fpol3High[iSector] = new TF1(fname.Data(),"pol3",0,5.5);
		for (Int_t iPar = 0; iPar < 4; iPar++) {
			Double_t parm_mean = _mean[iSector][iPar];
			Double_t parm_sigma = _sigma[iSector][iPar];
			_fpol3Mean[iSector]->FixParameter(iPar, parm_mean);
			_fpol3Low[iSector]->FixParameter(iPar, parm_mean-3*parm_sigma);
			_fpol3High[iSector]->FixParameter(iPar, parm_mean+3*parm_sigma);
		}
	}
	_f.close();
}

Eid::~Eid()
{
	for (Int_t iSector = 0; iSector < 6; iSector++) {
		delete _fpol3Mean[iSector];
		delete _fpol3Low[iSector];
		delete _fpol3High[iSector];
	}
}

/*Eid* Eid::Instance()
{
	if(ms_instance == 0) {
		ms_instance = new Eid();
	}
	return ms_instance;
}*/

void Eid::Release()
{
	if(ms_instance) {
		delete ms_instance;
	}
	ms_instance = 0;
}

void Eid::Print()
{
	for (Int_t iSector = 0; iSector < 6; iSector++) {
		for (Int_t iPar = 0; iPar < 4; iPar++) {
			printf("%d_SFsigma_a%i = %f\n", iSector+1, iPar, _sigma[iSector][iPar]);
		}
	}
}

TObjArray* Eid::getFuncsCuts()
{
	TObjArray *ret = new TObjArray(18);
	for (Int_t iSector = 0; iSector < 6; iSector++) {
		ret->Add(_fpol3Mean[iSector]);
		ret->Add(_fpol3Low[iSector]);
		ret->Add(_fpol3High[iSector]);
	}
	return ret;
}
