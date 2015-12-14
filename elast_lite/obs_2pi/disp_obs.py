from __future__ import division
import ROOT
from rootpy.io import root_open, DoesNotExist

from collections import OrderedDict
import array
import itertools

import os,sys
import time

import numpy as np
import matplotlib.pyplot as plt

import math

import atlib as atlib

from rootpy.interactive import wait

from proc_h8 import H5_DIM,VSTS,VARS,SEQ_ALL 

ROOT.gROOT.ProcessLine(".L THnTool.C+")
from ROOT import THnTool

# Tools 
thntool=THnTool()

#! For Luminosity & vgflux
LUM_E1F=19.844 #fb^-1
E1F_E0=5.499

LUM_E16=28
E16_E0=5.754

LUM_INVFB_TO_INVMICROB=1000000000

PI=3.14159265358979312
FSC=0.00729735253
A=FSC
NA=6.02214129E23
QE=1.60217646E-19
MP=0.93827203

Q2BINW=0.5 #Gev^2
WBINW=0.025 # GeV

#! Create dictionary for VAR_NAMES(VST,VAR): 
#! + VAR_NAMES(VST,VAR) should correspond with 'DataAna::MakeYields()':
#! 		+VST1: Delta++ => (p,pip)pim
#! 		+VST2: Rho     => (pip,pim)p
#! 		+VST3: Delta0  => (p,pim)pip
VAR_NAMES={(1,VARS[0]):"M_{p#pi^{+}}",(1,VARS[1]):"M_{#pi^{+}#pi^{-}}",
		   (1,VARS[2]):"#theta_{#pi^{-}}",(1,VARS[3]):"#phi_{#pi^{-}}",
		   (1,VARS[4]):"#alpha_{[p_{f}#pi^{+}][p#pi^{-}]}",
		   (2,VARS[0]):"M_{p#pi^{+}}",(2,VARS[1]):"M_{#pi^{+}#pi^{-}}",
		   (2,VARS[2]):"#theta_{p}",(2,VARS[3]): "#phi_{p}",
		   (2,VARS[4]):"#alpha_{[#pi^{+}#pi^{-}][pp_{f}]}",
		   (3,VARS[0]):"M_{p#pi^{+}}",(3,VARS[1]):"M_{p#pi^{-}}",
		   (3,VARS[2]):"#theta_{#pi^{+}}",(3,VARS[3]): "#phi_{#pi^{+}}",
		   (3,VARS[4]):"#alpha_{[p_{f}#pi^{-}][p#pi^{+}]}"}

VAR_UNIT_NAMES={VARS[0]:"GeV",VARS[1]:"GeV",VARS[2]:"deg",VARS[3]:"deg",VARS[4]:"deg"}
VAR_UNIT_NAMES_AFTR_NORM_FCTR_CALC={VARS[0]:"GeV",VARS[1]:"GeV",VARS[2]:"",VARS[3]:"rad",VARS[4]:"rad"}

#! Following dictionaries for extracting R2
R2_NAMED={'A':'R2_{T}+R2_{L}','B':'R2_{LT}','C':'R2_{TT}','D':'R2_{LT^{\'}}'}
H5_MFUNCD={'A':'1','B':'cphi','C':'c2phi','D':'sphi'}
MTHD_NAMED={'mthd1':'h5-mply-itg','mthd2':'phi-proj-fit','mthd3':'phi-prof-mply-itg'}
#! The following binning information taken from h8_bng.h
NBINS={'M1':14,'M2':14,'THETA':10,'PHI':10,'ALPHA':10}	
#! The following for phi-projection canvas
NXPADS={'M1':2,'M2':2,'THETA':2,'PHI':2,'ALPHA':2}
NYPADS={'M1':7,'M2':7,'THETA':5,'PHI':5,'ALPHA':5}
#! Fit function (needed for mthd2)
FPHI=ROOT.TF1("fphi", "([0] + [1]*cos(x*TMath::DegToRad()) + [2]*cos(2*x*TMath::DegToRad()) + [3]*sin(x*TMath::DegToRad()))",0,360)
FPHI.SetParameter(0,1)
FPHI.SetParameter(1,10)
FPHI.SetParameter(2,20)
FPHI.SetParameter(3,100)
FPHI.SetParName(0, "A")
FPHI.SetParName(1, "B")
FPHI.SetParName(2, "C")
FPHI.SetParName(3, "D")#hPD

#! Constants relating to plotting and its aesthetics
PLT_SEQ_ALL=SEQ_ALL#['ST','SR','SA','SC','SH','SF','ER','EC','EH','EF']
PLT_SEQ_ALL.remove('SA') #! SA is not plotted, at least not as an Observable

CLRS_PLT_SEQ_ALL={('ST'):ROOT.gROOT.ProcessLine("kGreen"),
				  ('SR'):ROOT.gROOT.ProcessLine("kMagenta"),
				  ('SC'):ROOT.gROOT.ProcessLine("kOrange"),
				  ('SH'):ROOT.gROOT.ProcessLine("kPink+1"),
				  ('SF'):ROOT.gROOT.ProcessLine("kRed"),
				  ('ER'):ROOT.gROOT.ProcessLine("kYellow"),
				  ('EC'):ROOT.gROOT.ProcessLine("kCyan"),
				  ('EH'):ROOT.gROOT.ProcessLine("kBlack"),
				  ('EF'):ROOT.gROOT.ProcessLine("kBlue")}

MRKS_PLT_SEQ_ALL={('ST'):ROOT.gROOT.ProcessLine("kPlus"),
				  ('SR'):ROOT.gROOT.ProcessLine("kOpenStar"),
				  ('SC'):ROOT.gROOT.ProcessLine("kFullDotLarge"),
				  ('SH'):ROOT.gROOT.ProcessLine("kCircle"),
				  ('SF'):ROOT.gROOT.ProcessLine("kFullDotLarge"),
				  ('ER'):ROOT.gROOT.ProcessLine("kOpenStar"),
				  ('EC'):ROOT.gROOT.ProcessLine("kFullDotLarge"),
				  ('EH'):ROOT.gROOT.ProcessLine("kCircle"),
				  ('EF'):ROOT.gROOT.ProcessLine("kFullDotLarge")}

def nu(w,q2):
	return (w*w-MP*MP+q2)/(2*MP)

def epsilon(w,q2):
	n=nu(w,q2)
	e0=E1F_E0
	e1=e0-n
	epsInv=1+2*(q2+n*n)/(4*e0*e1-q2)
	return 1.0/epsInv

def getvgflux(w,q2,e0=E1F_E0):
	eps=epsilon(w,q2)
	return A*w*(w*w-MP*MP)/(4*PI*e0*e0*MP*MP*q2*(1-eps))

class DispObs:
	def __init__(self,obsdir,simnum='siml',view="norm",q2min=1.25,q2max=5.25,wmin=1.400,wmax=2.125,expt='e1f',dbg=False):
		print "*** In DispObs::_init_() ***"
		self.OBSDIR=obsdir
		self.SIM_NUM=simnum
		self.VIEW=view
		self.Q2MIN,self.Q2MAX=q2min,q2max
		self.WMIN,self.WMAX=wmin,wmax
		if expt=='e1f':
			self.LUM=LUM_E1F
			self.E0=E1F_E0
		elif expt=='e16':
			self.LUM=LUM_E16
			self.E0=E16_E0

		self.DBG=dbg
				
		self.FIN=root_open(os.path.join(self.OBSDIR,self.SIM_NUM,'yield.root'))
		self.OUTDIR=os.path.join(self.OBSDIR,self.SIM_NUM)

		#! Set SEQS to process
		if   self.VIEW=="norm":
			self.SEQS=['EC','EF']
		elif self.VIEW=="fullana":
			self.SEQS=SEQ_ALL
		elif self.VIEW=="ERyield":
			self.SEQS=['ER']
		else:
			sys.exit("view={norm,fullana,ERyield} only")

		print "OBSDIR=%s\nFIN=%s\nOUTDIR=%s"%(self.OBSDIR,self.FIN,self.OUTDIR)
		print "self.VIEW=",self.VIEW
		print "SEQS to process=",self.SEQS
		print "expt=",expt
		time.sleep(3)

		#! Some general ROOT related setup
		#! + Print only Warning and Error messages
		#! + Not print Info messages, for examples, from TCanvas::SaveAs()
		#! source: https://root.cern.ch/phpBB3/viewtopic.php?t=8787
		ROOT.gErrorIgnoreLevel=ROOT.gROOT.ProcessLine('kWarning')

		print "*** _init_() Done *** \n"

	def plot_1D(self,h1,q2wbin):
		"""
		"""
		print "In DispObs::plot_1D()"

		#! Set up plotting aesthetics
		self.plot_1D_athtcs()
		self.hist_1D_athtcs(h1)
				
		#! TCanvas's pad_map[pad,vst,var] defined as per Gleb's display
		pad_map=[(1,1,"M1"),   (2,3,'M2'),   (3,2,'M2'),
				 (4,1,"THETA"),(5,3,'THETA'),(6,2,'THETA'),
				 (7,1,"ALPHA"),(8,3,'ALPHA'),(9,2,'ALPHA')]
						  
		c=ROOT.TCanvas("c","c",1000,1000)
		pad_t=ROOT.TPad("pad_l","Legend pad",0.25,0.935,0.75,1.00)
		pad_p=ROOT.TPad("pad_p","Plots pad",0.01,0.97,0.99,0.01)
		if (self.VIEW=="fullana"):pad_p.SetFillColor(ROOT.gROOT.ProcessLine("kGray+2"))
		pad_p.Draw()
		pad_t.Draw()
		pad_t.cd()
		pt=ROOT.TPaveText(.05,.1,.95,.8)
		pt.AddText("Q2_W bin=%s"%q2wbin)
		pt.SetTextSize(0.40)
		pt.Draw()
		pad_p.Divide(3,3)
		for item in pad_map:
			pad,vst,var=item[0],item[1],item[2]
			print "pad,vst,var=",pad,vst,var
			gpad=pad_p.cd(pad)
			if self.VIEW=="norm" or self.VIEW=="ERyield":
				#! First set minimum(=0) and maximum of y-axis
				maxl=[h1[seq,vst,var].GetMaximum() for seq in self.SEQS]
				maximum=max(maxl)
				for htmp in [h1[seq,vst,var] for seq in self.SEQS]:
					htmp.SetMinimum(0.)
					htmp.SetMaximum(maximum+0.5)
				#! Now draw
				for i,seq in enumerate(self.SEQS):
					draw_opt="" if i==0 else "same"
					h1[seq,vst,var].Draw(draw_opt)
			elif self.VIEW=="fullana":#! Draw all hists normed to same integral (since I want to compare their distributions)
				#! seq that can be directly drawn normalized
				seq_drct=['ST','SR','SF','ER','EF']
				#! seq that need to be manipulated
				#! + In this case the following seqs need to be scaled as per 
				#!   their counterpart h1n['F'] histograms such that after normalization
				#!   the following relationship is still preserved:
				#!   h1n[F]=h1n[C]+h1n[H]
				seq_mnpl_sim=['SC','SH']
				seq_mnpl_exp=['EC','EH']
				h1n=OrderedDict() 

				#! First draw 'seq_drct'
				for i,seq in enumerate(seq_drct):
					draw_opt=""
					if i>0:
						draw_opt="sames"
					h1n[seq]=h1[seq,vst,var].DrawNormalized(draw_opt,1000)
				#! Set the minimum and maximum of y coordinate of normed histograms
				maxl=[h1n[seq].GetMaximum() for seq in seq_drct]#[hEF_n.GetMaximum(),hSF_n.GetMaximum(),hER_n.GetMaximum(),hSR_n.GetMaximum(),hST_n.GetMaximum()]
				maximum=max(maxl)
				for htmp in [h1n[seq] for seq in seq_drct]:#[hEF_n,hSF_n,hER_n,hSR_n,hST_n]:
					htmp.SetMinimum(0.)
					htmp.SetMaximum(maximum+10)

				#! Now process and then draw seq_mnpl_sim/exp
				#! Scale EC, EH as per EF
				#! Obtain scale factor
				h_scl_exp=h1n['EF'].Clone("h_scl_exp")
				h_scl_exp.Divide(h1['EF',vst,var])
				#! Scale and draw
				for seq in seq_mnpl_exp:
					h1n[seq]=h1[seq,vst,var].Clone()
					h1n[seq].Multiply(h_scl_exp)
					h1n[seq].Draw("sames")
				#! Scale SC, SH as per SF
				#! Obtain scale factor
				h_scl_sim=h1n['SF'].Clone("h_scl_sim")
				h_scl_sim.Divide(h1['SF',vst,var])
				#! Scale and draw
				for seq in seq_mnpl_sim:
					h1n[seq]=h1[seq,vst,var].Clone()
					h1n[seq].Multiply(h_scl_sim)
					h1n[seq].Draw("sames")

				#! Re-draw h1n['ST'] for verification
				#! + This makes h1n['ST'] appear as a green '+' on top of SF;
				#!   othewise it is hidden under h1n['SF'] which is drawn earlier
				h1n['ST'].Draw("same")
				
				gpad.Update()

				#! Add TLegend if pad==1
				if pad==1:
					l=ROOT.TLegend(0.75,0.50,0.90,0.90)
					l.SetFillStyle(0)
					l.SetBorderSize(0)
					l.SetTextSize(0.06)
					for seq in seq_drct+seq_mnpl_sim+seq_mnpl_exp:
						l.AddEntry(h1n[seq],seq,"p")#EF
					l.Draw()
		#! Save canvas by q2bin (create folder tagged by q2bin)
		q2bin=self.get_q2bin(q2wbin)
		wbin=self.get_wbin(q2wbin)
		outdir_q2bin=os.path.join(self.OUTDIR_1D,"q%s"%q2bin)
		if not os.path.exists(outdir_q2bin):
			os.makedirs(outdir_q2bin)
		c.SaveAs("%s/c_w%s_q%s.png"%(outdir_q2bin,wbin,q2bin))
		c.SaveAs("%s/c_w%s_q%s.eps"%(outdir_q2bin,wbin,q2bin))

		print "*** plot_1D() Done ***\n"
		return

	def disp_1D(self):
		"""
		1. Get Q2-W bin list from yield.root
		2. Create h2(seq,vst,var) to store integrated yields=f(Q2-bin,W-bin)
		3. Per Q2-W bin:
			+ Extract h1(seq,vst,var)(=Obs_1D) where
				+ seq:
					+ =EC,EF       if view="norm" 
					+ =PLT_SEQ_ALL if view="fullana"
					+ =ER          if view="ERyield"
				+ var:	
					+ if vst==1:           VARS=(M1,THETA,ALPHA)
					+ if vst==2 or vst==3: VARS=(M2,THETA,ALPHA)

			+ If self.VIEW="norm", then Normalize h1(seq,vst,var)
			+ Fill relevant bin of h2 (=Intg_yld)
			+ Plot h1(seq,vst,var)
		4. Plot h2(seq,vst,var) and its projection on W
		"""
		print "*** In DispObs::disp_1D() ***"

		#! Make OUTDIR_1D
		#self.OUTDIR_1D=os.path.join(self.OUTDIR,"Obs_1D%s"%("_norm" if self.VIEW==True else ""))
		self.OUTDIR_1D=os.path.join(self.OUTDIR,"Obs_1D_%s"%self.VIEW)
		if not os.path.exists(self.OUTDIR_1D):
			os.makedirs(self.OUTDIR_1D)

		#! Make OUTDIR_2D
		#self.OUTDIR_ITG_YLD=os.path.join(self.OUTDIR,"Obs_Itg_Yld%s"%("_norm" if self.VIEW==True else ""))
		self.OUTDIR_ITG_YLD=os.path.join(self.OUTDIR,"Obs_Itg_Yld_%s"%self.VIEW)
		if not os.path.exists(self.OUTDIR_ITG_YLD):
			os.makedirs(self.OUTDIR_ITG_YLD)

		#! + Get Q2-W binning from file
		#! + Q2-W binning in the file is as per Q2-W binning of h8s
		if self.DBG==True:
			q2wbinl=self.get_q2wbinlist(self.Q2MIN,self.Q2MAX,self.WMIN,self.WMAX,dbg=True,dbg_bins=2)
		else:
			q2wbinl=self.get_q2wbinlist(self.Q2MIN,self.Q2MAX,self.WMIN,self.WMAX)
		print "DispObs::disp_1D() Q2-W bins got from yield.root=",q2wbinl

		#! Place holder for h2[seq,vst,var]: histogram to keep integrated yields in each Q2-W bin
		#! + Implementation appears sloppy for now, but it is created inside Q2-W bin loop
		h2=None
		#! + Get binning information for Q2 and W, individually, from Q2-W binning
		#! + This is needed later to specify the Q2- and W-binning when creating h2
		q2bng=self.get_q2bng(q2wbinl)
		wbng=self.get_wbng(q2wbinl)
		print "DispObs::disp_1D() nq2bins,nwbins=",q2bng['NBINS'],wbng['NBINS']

		print "DispObs::disp_1D() Going to begin processing Q2-W bins from file"
		#! Now, per Q2-W bin:
		#! + Obtain h1 (=obs_1D)
		#! + Create, if h2==None, and fill h2(=Intg_yld)
		for q2wbin in q2wbinl:
			print"Processing q2wbin=",q2wbin
			#! The following will be needed when filling h2
			iq2bin=q2bng['BINS'].index(self.get_q2bin_le(q2wbin))
			iwbin=wbng['BINS'].index(self.get_wbin_le(q2wbin))
			print "q2bin#,wbin#=",iq2bin+1,iwbin+1

			#! Obtain h1(seq,vst,var)
			h1=OrderedDict()
			for item in list(itertools.product(self.SEQS,VSTS)):
				seq,vst=item[0],item[1]
				if   vst==1:           varl=['M1','THETA','ALPHA']
				elif vst==2 or vst==3: varl=['M2','THETA','ALPHA']
				for var in varl:
					h1[seq,vst,var]=self.FIN.Get("%s/%s/VST%d/h1_%s"%(q2wbin,seq,vst,var))
					#! Call Sumw2() since the errors as currently in the h1s
					#! need to be propagated in all subsequent calculations that involve them
					h1[seq,vst,var].Sumw2()
			#! End of [seq,vst,var] loop

			#! If norm, then normalize h1(SEQ,VSTS,VARS)
			if self.VIEW=="norm":
				self.norm_1D(h1,q2wbin)
			else: #! just DCosTheta normalize theta distributions
				for k in h1:
					if k[2]=='THETA':
						self.norm_1D_theta(h1[k])

			#! Fill h2(seq,vst,var)
			if h2==None:
				h2=self.make_h2_itg_yld(q2bng,wbng,h1) #! Note h1 passed as a template to provide (seq,vst,var) keys
			self.fill_h2_itg_yld(h2,h1,iq2bin,iwbin)

			#! Plot h1(seq,vst,var)
			self.plot_1D(h1,q2wbin)
		#! End of q2wbin loop

		#! Plot h2
		self.plot_h2_itg_yld(h2)

		print "*** disp_1D() Done ***\n"

	def norm_1D(self,h1,q2wbin):
		print "*** In DispObs::norm_1D() ***"
		
		#! Get virtual photon flux for this q2wbin
		q2bin_le=self.get_q2bin_le(q2wbin)
		wbin_le=self.get_wbin_le(q2wbin)
		# q2=q2bin_le+(Q2BINW/2)
		# w=wbin_le+(WBINW/2)
		q2bin_ue=self.get_q2bin_ue(q2wbin)
		q2binw=q2bin_ue-q2bin_le
		q2=q2bin_le+(q2binw/2)
		w=wbin_le+(WBINW/2)
		print "norm_1D() Going to get vgflux for %s at q2=%.2f,w=%.3f"%(q2wbin,q2,w)
		vgflux=getvgflux(w,q2,e0=self.E0)

		#! Create h1n[SEQ,VSTS,VARS]
		#! + SEQ and VSTS in this case is redundant, since normalization depends, aside from Q2,W
		#!   and vgflux, only on VAR; however this redundancy helps in code organization and readability
		h1n=OrderedDict()
		for k in h1:
			seq,vst,var=k[0],k[1],k[2]
			nbins=h1[k].GetNbinsX()
			xmin=h1[k].GetXaxis().GetXmin()
			xmax=h1[k].GetXaxis().GetXmax()
			hname="hnorm_%s_VST%d_%s"%(seq,vst,var)
			h1n[k]=ROOT.TH1F(hname,hname,nbins,xmin,xmax)

			for ibin in range(nbins):
				#! Calculate var specific normalization factor
				if var=='M1' or var=='M2':
					DM=h1n[k].GetBinWidth(ibin+1)
					var_norm_fctr=DM
				elif var=='ALPHA':
					alpha_a=h1n[k].GetBinLowEdge(ibin+1)
					alpha_b=h1n[k].GetBinLowEdge(ibin+2)
					DAlpha=math.fabs(math.radians(alpha_b)-math.radians(alpha_a))
					var_norm_fctr=DAlpha
				elif var=='THETA':
					theta_a=h1n[k].GetBinLowEdge(ibin+1)
					theta_b=h1n[k].GetBinLowEdge(ibin+2)
					DCosTheta=math.fabs(math.cos(math.radians(theta_b))-math.cos(math.radians(theta_a)))
					var_norm_fctr=DCosTheta
				normf=self.LUM*LUM_INVFB_TO_INVMICROB*vgflux*q2binw*WBINW*var_norm_fctr #!Q2BINW
				h1n[k].SetBinContent(ibin+1,normf)
				h1n[k].SetBinError(ibin+1,0)

		#! Now normalize h1s
		for k in h1:
			h1[k].Divide(h1n[k])

		print "*** norm_1D() Done\n ***"

	def norm_1D_theta(self,hTheta):
		#! 1. Create normalization factor histogram
		hDCosTheta=hTheta.Clone()
		nbins=hTheta.GetNbinsX()
		for ibin in range(nbins):
			theta_a=hTheta.GetBinLowEdge(ibin+1)
			theta_b=hTheta.GetBinLowEdge(ibin+2)# + hTheta.GetBinWidth(ibin+1)
			DCosTheta=math.fabs(math.cos(math.radians(theta_b))-math.cos(math.radians(theta_a)))
			hDCosTheta.SetBinContent(ibin+1,DCosTheta)
			hDCosTheta.SetBinError(ibin+1,0.)
		#! Now divide hTheta by hDCosTheta
		#! Do Sumw2() so that errors are correctly propagated
		hTheta.Sumw2();
		hTheta.Divide(hDCosTheta)

	def plot_h2_itg_yld(self,h2):
		print "*** In DispObs::plot_h2_itg_yld() ***"

		#! Set up some plotting related aesthetics particular to this function
		#! Marker colors and styles
		#! + The idea is to use a uniqute MarkerColor for [vst,var]
		#! + As a further distinguishing feature, since colors take time to distinguish,
		#!   each var is assigned its own MarkerStyle, which can be additionally be classified
		#!   as 'Full' or 'Open' type markers, when for example, more than one seq is being plotted on the same plot.  
		#! 
		clrd={(1,'M1'):'kRed-6',     (2,'M2'):'kRed',     (3,'M2'):'kMagenta',
			  (1,'THETA'):'kBlue-6', (2,'THETA'):'kBlue', (3,'THETA'):'kCyan',
			  (1,'ALPHA'):'kGreen-6',(2,'ALPHA'):'kGreen',(3,'ALPHA'):'kOrange'}	
		mrkr_fulld={'M1':'kFullDotLarge', 'M2':'kFullDotLarge',     
					'THETA':'kFullSquare', 'ALPHA':'kFullTriangleUp'}
		mrkr_opend={'M1':'kOpenCircle', 'M2':'kOpenCircle',     
					'THETA':'kOpenSquare', 'ALPHA':'kOpenTriangleUp'}

		#! 1. Directly plot each h2[seq,vst,var] in its own canvas
		outdir_h2=os.path.join(self.OUTDIR_ITG_YLD,"Q2_W")
		if not os.path.exists(outdir_h2):
			os.makedirs(outdir_h2)
		#! Plotting aesthetics
		ROOT.gStyle.Reset() #! Reset aesthetics which may have been set by some other plot function
		ROOT.gStyle.SetOptStat("neiuo")
		ROOT.gStyle.SetErrorX(0.001)
		for k in h2:
			c=ROOT.TCanvas()
			h2[k].Draw("colz")
			c.SaveAs("%s/c_%s.png"%(outdir_h2,h2[k].GetName()))

		#! 2. Plot projection h2 on W bins i.e. int_yld(W) for various Q2 bins
		outdir_w_proj=os.path.join(self.OUTDIR_ITG_YLD,"W")
		if not os.path.exists(outdir_w_proj):
			os.makedirs(outdir_w_proj)
		nq2bins=h2[h2.keys()[0]].GetNbinsY()
		for iq2bin in range(nq2bins):
			if self.VIEW=="norm" or self.VIEW=="ERyield":
				#! Plotting aesthetics
				#ROOT.gROOT.SetOptStat("ne")
				
				#! + First create all projections: h1p[seq,vst,var]
				#! + This has to be done so that, before plotting, min and max for the Y-axis
				#!   can be determined from all the h1p[seq,vst,var]
				h1p=OrderedDict()
				for k in h2:
					seq,vst,var=k[0],k[1],k[2]
					hname="qbin_%d_%s_VST%d_%s"%(iq2bin+1,seq,vst,var)
					htitle="itg_xsec Q2=%s"%h2[k].GetYaxis().GetBinLabel(iq2bin+1)
					h1p[k]=h2[k].ProjectionX(hname,iq2bin+1,iq2bin+1,"e")
					h1p[k].SetTitle(htitle)
					if   self.VIEW=="norm": 
						h1p[k].SetYTitle("#sigma[#mub]")
						h1p[k].SetMinimum(0)
						h1p[k].SetMaximum(15)
					elif self.VIEW=="ERyield": h1p[k].SetYTitle("counts")
					
					clr=clrd[vst,var]
					if seq=='EC':
						mrkr=mrkr_fulld[var]
					elif seq=='EF':
						mrkr=mrkr_opend[var]
					elif seq=="ER":
						mrkr=mrkr_fulld[var]
					
					h1p[k].SetMarkerStyle(ROOT.gROOT.ProcessLine(mrkr))
					h1p[k].SetLineColor(ROOT.gROOT.ProcessLine(clr))
					h1p[k].SetMarkerColor(ROOT.gROOT.ProcessLine(clr))
					
				#! Determine max and set Y-axis min(=0),max for all h1p[seq,vst,var]
				maxl=[h1p[k].GetMaximum() for k in h2]
				maximum=max(maxl)
				for k in h1p:
					h1p[k].SetMinimum(0.)
					h1p[k].SetMaximum(maximum)
				
				#! Now draw
				ROOT.gStyle.SetOptStat(0)
				c=ROOT.TCanvas("c","c",1200,800)
				#c.Divide(2,1) #! One for the plot and the other for the large legend
				pad_l=ROOT.TPad("pad_l","Title pad",0.70,0.00,1.00,1.00)
				pad_p=ROOT.TPad("pad_p","Plots pad",0.00,0.00,0.70,1.00)
				pad_l.SetFillColor(ROOT.gROOT.ProcessLine("kGray+2"))
				pad_p.SetFillColor(ROOT.gROOT.ProcessLine("kGray+2"))
				pad_l.Draw()
				pad_p.Draw()
				#! legend
				l=ROOT.TLegend(0.0,0.00,1.00,1.00)
				l.SetFillStyle(0)
				l.SetBorderSize(0)
				l.SetTextSize(0.03)#0.02
				#gpad=c.cd(1)
				#gpad.SetFillColor(ROOT.gROOT.ProcessLine("kGray+2"))
				pad_p.cd()
				for i,k in enumerate(h1p):
					seq,vst,var=k[0],k[1],k[2]
					draw_opt=""
					if i>0: draw_opt="same"
					h1p[k].Draw(draw_opt)
					l.AddEntry(h1p[k],"%s_VST%d_%s"%(seq,vst,var),"p")
				#gpad=c.cd(2)
				#gpad.SetFillColor(ROOT.gROOT.ProcessLine("kGray+2"))
				pad_l.cd()
				l.Draw()
				c.SaveAs("%s/c_qbin%d.png"%(outdir_w_proj,iq2bin+1))

			elif self.VIEW=="fullana": 
				#! Plotting aesthetics
				#ROOT.gROOT.SetOptStat("ne")
				#! + First create all projections: h1p[seq,vst,var]
				h1p=OrderedDict()
				for k in h2:
					seq,vst,var=k[0],k[1],k[2]
					if seq=='SH' or seq=='EH': continue
					hname="qbin_%d_%s_VST%d_%s"%(iq2bin+1,seq,vst,var)
					htitle="itg_yld Q2=%s"%h2[k].GetYaxis().GetBinLabel(iq2bin+1)
					h1p[k]=h2[k].ProjectionX(hname,iq2bin+1,iq2bin+1,"e")
					h1p[k].SetTitle(htitle)
					
					clr=clrd[vst,var]
					#! Set appropriate MarkerStyles for SEQS plotted on same cavas
					#! ER,SR on same
					if seq=='ER':
						mrkr=mrkr_opend[var]
					elif seq=='SR':
						mrkr=mrkr_fulld[var]
					#! EC,EF on same; SC,SF,ST on same	
					if seq=='EC' or seq=='SC':
						mrkr=mrkr_fulld[var]
					elif seq=='SF' or seq=='EF':
						mrkr=mrkr_opend[var]
					elif seq=='ST':
						mrkr="kPlus"
					
					h1p[k].SetMarkerStyle(ROOT.gROOT.ProcessLine(mrkr))
					h1p[k].SetLineColor(ROOT.gROOT.ProcessLine(clr))
					h1p[k].SetMarkerColor(ROOT.gROOT.ProcessLine(clr))
				
				#! Now draw
				#! Plotting aesthetics
				ROOT.gStyle.SetOptStat(0)
				#! Draw ER,SR normalized to same integral
				c1=ROOT.TCanvas("c1","c1",1000,500)#,1500,2000)
				c1.Divide(2,1)
				h1n=OrderedDict() #! To keep normed hists
				gpad=c1.cd(1)
				gpad.SetFillColor(ROOT.gROOT.ProcessLine("kGray+2"))
				l1=ROOT.TLegend(0.0,0.00,1.0,1.00)
				l1.SetFillStyle(0)
				l1.SetBorderSize(0)
				l1.SetTextSize(0.02)
				i=0
				for k in h1p:
					seq,vst,var=k[0],k[1],k[2]
					if seq!='ER' and seq!='SR': continue
					draw_opt="" if i==0 else "same"
					h1n[k]=h1p[k].DrawNormalized(draw_opt,1000)
					l1.AddEntry(h1n[k],"%s_VST%d_%s"%(k[0],k[1],k[2]),"p")
					i+=1
				#! Add additional label for ER,SR to say that they are normed to same integral
				pt=ROOT.TPaveText(.05,.90,.95,.95,"NDC")
				pt.AddText("Integral of all hists. normalized to 1000")
				pt.Draw()
				gpad=c1.cd(2)
				gpad.SetFillColor(ROOT.gROOT.ProcessLine("kGray+2"))
				l1.Draw()
				c1.SaveAs("%s/c_qbin%d_ER_SR.png"%(outdir_w_proj,iq2bin+1))

				#! Draw ST,SC,SF
				#! First set max of Y-axis
				maxl=[h1p[k].GetMaximum() for k in h1p if k[0]=='ST' or k[0]=='SC' or k[0]=='SF']
				maximum=max(maxl)
				for k in h1p:
					if k[0]=='ST' or k[0]=='SC' or k[0]=='SF':
						h1p[k].SetMinimum(0)
						h1p[k].SetMaximum(maximum)

				c2=ROOT.TCanvas("c2","c2",1000,500)
				c2.Divide(2,1)
				gpad=c2.cd(1)
				gpad.SetFillColor(ROOT.gROOT.ProcessLine("kGray+2"))
				l2=ROOT.TLegend(0.0,0.00,1.0,1.00)
				l2.SetFillStyle(0)
				l2.SetBorderSize(0)
				l2.SetTextSize(0.02)
				i=0
				#! First draw SC,SF
				for k in h1p:
					seq,vst,var=k[0],k[1],k[2]
					if seq!='SC' and seq != 'SF': continue
					draw_opt="" if i==0 else "same"
					h1p[k].Draw(draw_opt)
					l2.AddEntry(h1p[k],"%s_VST%d_%s"%(k[0],k[1],k[2]),"p")
					i+=1
				#! Now draw ST so that it appears on top
				for k in h1p:
					seq,vst,var=k[0],k[1],k[2]
					if seq!='ST': continue
					draw_opt="" if i==0 else "same"
					h1p[k].Draw(draw_opt)
					l2.AddEntry(h1p[k],"%s_VST%d_%s"%(k[0],k[1],k[2]),"p")
					i+=1
				gpad=c2.cd(2)
				gpad.SetFillColor(ROOT.gROOT.ProcessLine("kGray+2"))
				l2.Draw()
				c2.SaveAs("%s/c_qbin%d_ST_SC_SF.png"%(outdir_w_proj,iq2bin+1))

				#! Draw EC,EF
				#! First set max of Y-axis
				maxl=[h1p[k].GetMaximum() for k in h1p if k[0]=='EC' or k[0]=='EF']
				maximum=max(maxl)
				for k in h1p:
					if k[0]=='EC' or k[0]=='EF':
						h1p[k].SetMinimum(0)
						h1p[k].SetMaximum(maximum)

				c3=ROOT.TCanvas("c3","c3",1000,500)
				c3.Divide(2,1)
				gpad=c3.cd(1)
				gpad.SetFillColor(ROOT.gROOT.ProcessLine("kGray+2"))
				l3=ROOT.TLegend(0.0,0.00,1.0,1.00)
				l3.SetFillStyle(0)
				l3.SetBorderSize(0)
				l3.SetTextSize(0.02)
				i=0
				for k in h1p:
					seq,vst,var=k[0],k[1],k[2]
					if seq!='EC' and seq != 'EF': continue
					draw_opt="" if i==0 else "same"
					h1p[k].Draw(draw_opt)
					l3.AddEntry(h1p[k],"%s_VST%d_%s"%(k[0],k[1],k[2]),"p")
					i+=1
				gpad=c3.cd(2)
				gpad.SetFillColor(ROOT.gROOT.ProcessLine("kGray+2"))
				l3.Draw()
				c3.SaveAs("%s/c_qbin%d_EC_EH.png"%(outdir_w_proj,iq2bin+1))

		print "*** plot_h2_itg_yld() Done ***\n"
		
		
	def fill_h2_itg_yld(self,h2,h1,iq2bin,iwbin):
		print "*** In DispObs::fill_h2_itg_yld ***"
		
		for k in h1:
			seq,vst,var=k[0],k[1],k[2]
			if var=='M1' or var=='M2': #! then directly use TH1::Integral(opt); opt="width" when self.VIEW="norm", "" when self.VIEW="fullana"/"ERyield"
				opt="%s"%("width" if self.VIEW=="norm" else "")
				nbins=h1[k].GetNbinsX()
				itg_err=ROOT.Double(0)#https://root.cern.ch/phpBB3/viewtopic.php?t=2499
				itg=h1[k].IntegralAndError(1,nbins,itg_err,opt)
				h2[k].SetBinContent(iwbin+1,iq2bin+1,itg)
				h2[k].SetBinError(iwbin+1,iq2bin+1,itg_err)
			elif var=='THETA': #! manually compute integral to adapt for DCosTheta irrespective of self.VIEW (NOTE, theta distributions are atleast DCosTheta normalized irrespective of self.VIEW)
				itg,itg_err=0,0
				nbins=h1[k].GetNbinsX()
				for ibin in range(nbins):
					binc=h1[k].GetBinContent(ibin+1)
					bincerr=h1[k].GetBinError(ibin+1)
					theta_a=h1[k].GetBinLowEdge(ibin+1)
					theta_b=h1[k].GetBinLowEdge(ibin+2)
					DCosTheta=math.fabs(math.cos(math.radians(theta_b))-math.cos(math.radians(theta_a)))
					itg+=binc*DCosTheta
					itg_err+=bincerr*DCosTheta
				h2[k].SetBinContent(iwbin+1,iq2bin+1,itg)
				h2[k].SetBinError(iwbin+1,iq2bin+1,itg_err)
			elif var=='ALPHA': #! manually compute integral to adapt for DAlpha; DAlpha is in radians when self.VIEW="norm", 1 when self.VIEW="fullana"/"ERyield"
				itg,itg_err=0,0
				nbins=h1[k].GetNbinsX()
				for ibin in range(nbins):
					binc=h1[k].GetBinContent(ibin+1)
					bincerr=h1[k].GetBinError(ibin+1)
					alpha_a=h1[k].GetBinLowEdge(ibin+1)
					alpha_b=h1[k].GetBinLowEdge(ibin+2)# + h1[k].GetBinWidth(ibin+1)
					if self.VIEW=="norm":
						DAlpha=math.fabs(math.radians(alpha_b)-math.radians(alpha_a))
					else:
						DAlpha=1
					itg+=binc*DAlpha
					itg_err+=bincerr*DAlpha
				h2[k].SetBinContent(iwbin+1,iq2bin+1,itg)
				h2[k].SetBinError(iwbin+1,iq2bin+1,itg_err)


		print "*** fill_h2_itg_yld() Done ***\n"	

	def make_h2_itg_yld(self,q2bng,wbng,h1):
		'''
		+ h1 needed to provide [seq,vst,var] keys
		+ Make h2_itg_yld[seq,vst,var] with xaxis,yaxis=nwbins,nq2bins
			+ 'var' is included for debugging purposes since integrated yield 
			  from all VSTS*VARS should be the same.
		'''
		#! First get binning in Q2 and W from Q2-W binning
		print "In DispObs::make_h2_itg_yld()"
		nq2bins=q2bng['NBINS']
		nwbins=wbng['NBINS']
		q2bins=array.array('f',range(1,nq2bins+1+1))#!Last '+1' to ensure 'range' includes top edge of last bin 
		wbins=array.array('f',range(1,nwbins+1+1))#!Last '+1' to ensure 'range' includes top edge of last bin
		h2=OrderedDict()
		for k in h1:
			seq,vst,var=k[0],k[1],k[2]
			name="h2_%s_VST%d_%s"%(seq,vst,var)
			title="itg_yld(Q^{2},W)"
			h2[seq,vst,var]=ROOT.TH2F(name,title,nwbins,wbins,nq2bins,q2bins) 
			h2[seq,vst,var].SetXTitle("W (GeV)")
			h2[seq,vst,var].SetYTitle("Q^{2} (GeV^{2})")
			#! Label the bins
			for iwbin in range(nwbins):
				le=wbng['BINS'][iwbin]
				ue=wbng['BINS'][iwbin+1]
				h2[seq,vst,var].GetXaxis().SetBinLabel(iwbin+1,"[%.3f,%.3f)"%(le,ue))
			for iq2bin in range(nq2bins):
				le=q2bng['BINS'][iq2bin]
				ue=q2bng['BINS'][iq2bin+1]
				h2[seq,vst,var].GetYaxis().SetBinLabel(iq2bin+1,"[%.2f,%.2f)"%(le,ue))
			
		#! For debuggin print out h2 information for first key in h2[seq,vst,var]
		print "make_h2_itg_yld() nq2bins,nwbins=%d,%d"%(h2[h2.keys()[0]].GetNbinsY(),h2[h2.keys()[0]].GetNbinsX())
		print "make_h2_itg_yld() wbin labels:" 
		for iwbin in range(nwbins):
			print "wbin#=%d,label=%s"%(iwbin+1,h2[h2.keys()[0]].GetXaxis().GetBinLabel(iwbin+1))
		print "make_h2_itg_yld() q2bin labels:" 
		for iq2bin in range(nq2bins):	
			print "q2bin#=%d,label=%s"%(iq2bin+1,h2[h2.keys()[0]].GetYaxis().GetBinLabel(iq2bin+1))

		print "***make_h2_itg_yld() Done \n***"
		return h2

	def disp_itg_yld_drct_from_h5(self):
		"""
		Walk the ROOT file and plot y(w;seq,vst,q2bin). 
		"""
		print "*** In DispObs::disp_itg_yld_drct_from_h5() ***"
		
		# if self.VIEW==False:
		# 	outdir=os.path.join(self.OUTDIR,"Obs_Itg_Yld_drct")
		# else:
		# 	outdir=os.path.join(self.OUTDIR,"Obs_Itg_Yld_drct_norm")
		outdir=os.path.join(self.OUTDIR,"Obs_Itg_Yld_drct_%s"%self.VIEW)
		if not os.path.exists(outdir):
			os.makedirs(outdir)

		#! 1. Get all q2wbins
		if self.DBG==True:
			q2wbinl=self.get_q2wbinlist(self.Q2MIN,self.Q2MAX,self.WMIN,self.WMAX,dbg=True,dbg_bins=2)
		else:
			q2wbinl=self.get_q2wbinlist(self.Q2MIN,self.Q2MAX,self.WMIN,self.WMAX)
		#print q2wbinl

		q2bng=self.get_q2bng(q2wbinl)
		#print q2bng['BINW']
		print "Yield(w) will be plotted for the following Q2 bins:"
		print q2bng['BINS']

		#! 3. Now put together dictionary for yield: y{seq,vst,q2bin:{w:yield}}
		#! First create dict
		y={}
		oy={} #Will be used later to store yields ordered
		for seq in self.SEQS:
			for vst in VSTS:
				for q2wbin in q2wbinl:
					q2bin=q2wbin.split('_')[0]
					y[seq,vst,q2bin]={}
					oy[seq,vst,q2bin]={}
		#! Now fill dict
		for seq in self.SEQS:
			for vst in VSTS:
				for q2wbin in q2wbinl:
					print "seq,vst,q2wbin",seq,vst,q2wbin
					q2bin=q2wbin.split('_')[0]
					#! Get w, yield
					w=float(q2wbin.split('_')[1].split('-')[0])
					dw=float(q2wbin.split('_')[1].split('-')[1])-w
					#wbin=q2wbin.split('_')[1]
					h5=self.FIN.Get("%s/%s/VST%d/h5"%(q2wbin,seq,vst))
					y[seq,vst,q2bin][w]=thntool.GetIntegral(h5)
					if self.VIEW=="norm":
						q2=float(q2wbin.split('_')[0].split('-')[0])
						dq2=float(q2wbin.split('_')[0].split('-')[1])-q2
						#normf=self.LUM*LUM_INVFB_TO_INVMICROB*getvgflux(w,q2,e0=self.E0)*dw*dq2#!mub^-1
						normf=self.LUM*LUM_INVFB_TO_INVMICROB*getvgflux(w+(dw/2),q2+(dq2/2),e0=self.E0)*dw*dq2#!mub^-1
						#normf=self.LUM*LUM_INVFB_TO_INVMICROB*getvgflux(w+dw,q2+dq2,e0=self.E0)*dw*dq2#!mub^-1
						print "yield=",y[seq,vst,q2bin][w]
						print "dw,dq2=",dw,dq2
						print "norm=",normf
						y[seq,vst,q2bin][w]=y[seq,vst,q2bin][w]/normf
						print "yield after norm=",y[seq,vst,q2bin][w]
		#! Make sure y[seq,q2bin:w] are sorted by w
		for k in y.keys():
			oy[k]=OrderedDict(sorted(y[k].items()))
			
		#! 4. Now plot
		fig=plt.figure()
		ax=plt.subplot(111)
		# clrd={('1.25-1.75',1):'red',('1.25-1.75',2):'brown',('1.25-1.75',3):'magenta',
		# 	  ('1.75-2.25',1):'cyan',('1.75-2.25',2):'blue',('1.75-2.25',3):'green',
		# 	  ('2.25-2.75',1):'orange',('2.25-2.75',2):'yellow',('2.25-2.75',3):'black',
		# 	  ('2.75-3.25',1):'cyan',('2.75-3.25',2):'blue',('2.75-3.25',3):'green',
		# 	  ('3.25-3.75',1):'cyan',('3.25-3.75',2):'blue',('3.25-3.75',3):'green',
		# 	  ('3.75-4.25',1):'cyan',('3.75-4.25',2):'blue',('3.75-4.25',3):'green',
		# 	  ('4.25-4.75',1):'cyan',('4.25-4.75',2):'blue',('4.25-4.75',3):'green',
		# 	  ('4.75-5.25',1):'orange',('4.75-5.25',2):'yellow',('4.75-5.25',3):'black'}
		clrd={('1.50-2.00',1):'red',('1.50-2.00',2):'brown',('1.50-2.00',3):'magenta',
			  ('2.00-2.40',1):'cyan',('2.00-2.40',2):'blue',('2.00-2.40',3):'green',
			  ('2.40-3.00',1):'orange',('2.40-3.00',2):'yellow',('2.40-3.00',3):'black',
			  ('3.00-3.50',1):'cyan',('3.00-3.50',2):'blue',('3.00-3.50',3):'green',
			  ('3.50-4.20',1):'cyan',('3.50-4.20',2):'blue',('3.50-4.20',3):'green',
			  ('4.20-5.00',1):'cyan',('4.20-5.00',2):'blue',('4.20-5.00',3):'green'}
		mrkrd={'EC':'o','EF':'^'}
		for k in oy.keys():
			seq,vst,q2wbin=k[0],k[1],k[2]
			lbl='%s:VST%d[%s)'%(seq,vst,q2wbin)
			ax.scatter(oy[k].keys(),oy[k].values(),label=lbl,c=clrd[q2wbin,vst],marker=mrkrd[seq],s=50)
			ax.set_xticks(oy[k].keys())
			ax.set_xticklabels(oy[k].keys(),rotation='vertical')
		if self.VIEW!="norm":
			ax.set_ylim(0,600000)
			ax.set_ylabel(r'Yield [A.U.]',fontsize='xx-large')
		else:
			ax.grid(1)
			ax.set_ylim(0,10)
			ax.set_ylabel(r'$\mu b$',fontsize='xx-large')
		ax.legend(loc='upper left',prop={'size':8}) #loc='lower right'
		fig.savefig('%s/integ_yield.png'%(outdir))
		#fig.savefig('%s/integ_yield.eps'%(outdir))

		print "*** disp_itg_yld_old_mchnry() Done ***\n"

	
	def get_sim_stats(self):
		"""
		Walk the ROOT file and obtain simstats(ss) for a h5 in a Q2-W bin:
		ss={'ST':[[q21,w1,nbins,N,mu,sg],...,[q2N,wN,nbins,N,mu,sg]],
			'SR':[[q21,w1,nbins,N,mu,sg],...,[q2N,wN,nbins,N,mu,sg]],
			'SA':[[q21,w1,nbins,N,mu,sg],...,[q2N,wN,nbins,N,mu,sg]],
			'SH':[[q21,w1,nbins,N,mu,sg],...,[q2N,wN,nbins,N,mu,sg]]}

		where:
			+ nbins=number of filled bins in a h5_UNPOL
			+ N=sum({n_i}) were n_i=events per bin (number of events in a h5_UNPOL)
			+ mu=average({n_i} (average of number of events per bin)
			+ sg=(RMS({n_i}) (RMS of number of events per bin)
		"""
		#! First get all q2wbin directories from file
		q2ws=self.get_q2wbinlist()
		#print "Processing sim_stats for %s:"%self.Q2W
		print q2ws

		ss={'ST':[],'SR':[],'SA':[],'SH':[]}
		for seq in ['ST','SR','SA','SH']:
			for q2w in q2ws:
				print "Processing sim_stats for %s"%q2w
				#! Determine q2,w
				q2bin=q2w.split('_')[0]
				wbin=q2w.split('_')[1]
				#print q2bin,wbin
				q2=float(q2bin.split('-')[0])
				w=float(wbin.split('-')[0])
				#print q2,w
				#! Determine nbins,N,mu,sg for this q2,w
				h5=self.FIN.Get("%s/%s/VST1/h5"%(q2w,seq))
				nbins=thntool.GetNbinsNotEq0(h5)
				N=thntool.GetIntegral(h5)
				binc_stats=np.zeros(2,'f')
				thntool.GetBinContentDistStats(h5,binc_stats)
				mu=binc_stats[0]
				sg=binc_stats[1]
				ss[seq].append([q2,w,nbins,N,mu,sg])
			# #! Compute average
			# ss[seq].append(nevts/len(q2ws))
			# ss[seq].append(nbins/len(q2ws))
		return ss

	def get_sim_stats_commonbins(self):
		"""
		The same as get_sim_stats(), but with the difference that mu,sg
		are obtained only for R-PS bins. I am currently not using this since
		this process takes impractically long.

		Walk the ROOT file and obtain simstats(ss) for a h5_UNPOL in a Q2-W bin:
		ss={'T':[[q21,w1,nbins,N,mu,sg],...,[q2N,wN,nbins,N,mu,sg]],
			'R':[[q21,w1,nbins,N,mu,sg],...,[q2N,wN,nbins,N,mu,sg]],
			'A':[[q21,w1,nbins,N,mu,sg],...,[q2N,wN,nbins,N,mu,sg]],
			'H':[[q21,w1,nbins,N,mu,sg],...,[q2N,wN,nbins,N,mu,sg]]}

		where:
			+ nbins=number of filled bins in a h5_UNPOL
			+ N=sum({n_i}) were n_i=events per bin (number of events in a h5_UNPOL)
			+ mu=average({n_i}) (average of number of events per bin)
				+ Note, average computed over only R-PS bins
			+ sg=(RMS({n_i}) (RMS of number of events per bin)
				+ Note, average computed over only R-PS bins
		"""
		#! First get all q2wbin directories from file
		q2ws=self.get_q2wbinlist()
		print "Processing sim_stats for %s:"%self.Q2W
		print q2ws

		ss={'T':[],'R':[],'A':[],'H':[]}
		f=ROOT.TFile(self.FSIM.GetName())
		for q2w in q2ws:
			print "Processing %s..."%q2w
			#! Determine q2,w
			q2bin=q2w.split('_')[0]
			wbin=q2w.split('_')[1]
			#print q2bin,wbin
			q2=float(q2bin.split('-')[0])
			w=float(wbin.split('-')[0])
			#print q2,w
			#! First get all h5_UNPOLs
			h5_UNPOL={}
			for seq in ['T','R','A','H']:
				h5_UNPOL[seq]=f.Get("%s/VST1/%s/h5_UNPOL"%(q2w,seq))
			#! Now get simstats	
			for seq in ['T','R','A','H']:
				#! Determine nbins,N,mu,sg for this q2,w
				nbins=thntool.GetNbinsNotEq0(h5_UNPOL[seq])
				N=thntool.GetIntegral(h5_UNPOL[seq])
				binc_stats=np.zeros(2,'f')
				print "here"
				thntool.GetBinContentDistStatsCommonBins(h5_UNPOL[seq],h5_UNPOL['R'],binc_stats)
				print "here1"
				mu=binc_stats[0]
				sg=binc_stats[1]
				ss[seq].append([q2,w,nbins,N,mu,sg])
		return ss

	def plot_sim_stats_q2wbin_5D(self,q2wbin='',acc_rel_err_cut=-1,cut_type='lt',vst=1):
		"""
		[11-16-15] 
		+ Orignal in study_acc_tools_lite.py::plot_acc_q2wbin_5D()
		+ Brought over to disp_obs.py in order to consolidate

		Notes:
		+ Unless q2wbin is specified, this function will plot and save 5D simstats 
          for all q2wbins in yield.root
        + If q2wbin is specified, then this function will make an interactive plot for that
          particular q2wbin
		"""
		is_intrctv=False
		if q2wbin=='':#! Get all q2wbin directories from file
			q2wbinl=self.get_q2wbinlist()
			#! Create output directory
			outdir=os.path.join(self.OUTDIR,'simstats')
			if not os.path.exists(outdir):
				os.makedirs(outdir)
			#! Create output.root file
			sfx=''
			if acc_rel_err_cut>0:sfx="_acc_relerr_%s_%.2f"%(cut_type,acc_rel_err_cut)
			fout=ROOT.TFile("%s/simstats_q2wbin%s.root"%(outdir,sfx),"RECREATE")
		else:#! interactive mode for particular q2wbin
			q2wbinl=[q2wbin]
			is_intrctv=True;

		print "Going to plot 5D simstats for q2wbinl=",q2wbinl

		ROOT.gStyle.SetOptStat("nemMrRuo")

		for q2wbin in q2wbinl:
			#! Get 5D histograms
			h5T=self.FIN.Get('%s/ST/VST%d/h5'%(q2wbin,vst))
			h5R=self.FIN.Get('%s/SR/VST%d/h5'%(q2wbin,vst))
			h5A=self.FIN.Get('%s/SA/VST%d/h5'%(q2wbin,vst))
	
			nbins=h5T.GetNbins()
			hT=ROOT.TH1F("hT","ST:%s"%q2wbin,400,0,400)
			hR=ROOT.TH1F("hR","SR:%s"%q2wbin,60,0,60)
			hA=ROOT.TH1F("hA","SA:%s"%q2wbin,100,0,1.5)
			h_relErrA=ROOT.TH1F("hA_rel_err","SA_rel_err:%s"%q2wbin,100,0,1.5)
			#print nbins
			bincoordT=np.zeros(5,'i')
			for ibin in range(nbins):
				bincT=h5T.GetBinContent(ibin,bincoordT)
	
				binR=h5R.GetBin(bincoordT)
				bincR=h5R.GetBinContent(binR)
	   
				binA=h5A.GetBin(bincoordT)
				bincA=h5A.GetBinContent(binA)
				if bincA>0:
					rel_err_A=h5A.GetBinError(binA)/bincA
					if acc_rel_err_cut>0: #! i.e. make a cut on acc_rel_err_cut
						pass_cut=False
						if   cut_type=='lt': pass_cut=rel_err_A<acc_rel_err_cut
						elif cut_type=='gt': pass_cut=rel_err_A>acc_rel_err_cut
						if pass_cut: 
							hT.Fill(bincT)
							hR.Fill(bincR)
							hA.Fill(bincA)
							h_relErrA.Fill(rel_err_A)
					else:
						hT.Fill(bincT)
						hR.Fill(bincR)
						hA.Fill(bincA)
						h_relErrA.Fill(rel_err_A)
	
				# if bincA>0:# and bincA<1:
				# 	hT.Fill(bincT)
				# 	hR.Fill(bincR)
				# 	hA.Fill(bincA)
				# 	h_relErrA.Fill(rel_err_A)
		
			#! Now draw hists
			cname="c_%s"%q2wbin
			c=ROOT.TCanvas(cname,cname)
			c.Divide(2,2)
			c.cd(1)
			hT.Draw()
			c.cd(2)
			hR.Draw()
			c.cd(3)
			hA.Draw()
			c.cd(4)
			h_relErrA.Draw()

			if is_intrctv:
				plt.show()
				# wait for you to close the ROOT canvas before exiting
				wait(True)
			else:
				c.Write()


	def get_q2wbinlist(self,q2min=0.00,q2max=6.00,wmin=0.000,wmax=3.000,dbg=False,dbg_bins=10):
		"""
		The ROOT file is arranged in a Tree Structure. The
		Observable histograms (obs-hists) are located as files in the following directory-path(dirpath):
		q2wbin/vst/seq/hists
		"""
		q2wbinl=[]
		#! File to use to extract q2wbinl
		f=self.FIN
				
		i=0 #! for dbg_bins
		for path,dirs,files in f.walk():
			if path=="":continue #! Avoid root path
			path_arr=path.split("/")
			if len(path_arr)==1:
				q2wbinl.append(path)
				i+=1
			if dbg==True:
				if i>=dbg_bins: break #! Uncomment/comment -> Get limited q2w-bins/Get all q2w-bins

		#! Remove q2wbins that are not within [q2min,q2max],[wmin,wmax] 
		q2wbins_remove=[]
		for q2wbin in q2wbinl:
			q2bin_le=q2wbin.split("_")[0].split("-")[0]
			q2bin_ue=q2wbin.split("_")[0].split("-")[1]
			wbin_le =q2wbin.split("_")[1].split("-")[0]
			wbin_ue =q2wbin.split("_")[1].split("-")[1]
			if float(q2bin_ue)<=q2min or float(q2bin_le)>=q2max or float(wbin_ue)<=wmin or float(wbin_le)>=wmax:
				q2wbins_remove.append(q2wbin)
		for q2wbin in q2wbins_remove:
			q2wbinl.remove(q2wbin)

		return q2wbinl


	def get_q2bng(self,q2wbinl):
		return self.get_xbng('Q2',q2wbinl)
	def get_wbng(self,q2wbinl):
		return self.get_xbng('W',q2wbinl)

	def get_xbng(self,x,q2wbinl):
		"""
		Gets x=(Q2 or W) binning information from q2wbinl
		"""

		#! 1. From q2wbinl, identify xbng 
		xbins=[]
		for q2wbin in q2wbinl:
			#print q2wbin
			if(x=='Q2'):
				xbins.append(float(q2wbin.split('_')[0].split('-')[0]))
				xbins.append(float(q2wbin.split('_')[0].split('-')[1]))
			elif(x=='W'):
				xbins.append(float(q2wbin.split('_')[1].split('-')[0]))
				xbins.append(float(q2wbin.split('_')[1].split('-')[1]))
			else:
				sys.exit("DispObs::get_xbng() x=%s not recognized"%x)
		xbins=set(xbins) #! Keep only unique entries
		xbins=list(xbins) #! convert 'set' back to 'list'
		xbins=sorted(xbins) #! Order entries
		#print xbins
		xbins_le=xbins[:-1]
		xbins_ue=xbins[1:]
		#print xbins_le
		#print xbins_ue
		xmin=min(xbins)
		xmax=max(xbins)
		xbinw=xbins[1]-xbins[0]
		nxbins=len(xbins_le)
		xbng={'MIN':xmin,'MAX':xmax,'BINW':xbinw,'NBINS':nxbins,
		   'BINS_LE':xbins_le,'BINS_UE':xbins_ue,'BINS':xbins}
		return xbng

	def get_q2bin(self,q2wbin):
		return q2wbin.split('_')[0]
	def get_wbin(self,q2wbin):
		return q2wbin.split('_')[1]
	def get_q2bin_le(self,q2wbin):
		return float(self.get_q2bin(q2wbin).split('-')[0])
	def get_wbin_le(self,q2wbin):
		return float(self.get_wbin(q2wbin).split('-')[0])
	def get_q2bin_ue(self,q2wbin):
		return float(self.get_q2bin(q2wbin).split('-')[1])
	def get_wbin_ue(self,q2wbin):
		return float(self.get_wbin(q2wbin).split('-')[1])
	
	def hist_1D_athtcs(self,h1):
		for k in h1.keys():	
			seq,vst,var=k[0],k[1],k[2]
			h1[k].SetTitle("")
			h1[k].SetXTitle( "%s[%s]"%(VAR_NAMES[(vst,var)],VAR_UNIT_NAMES[var]) )
			#! X-axis title aesthetics
			h1[k].GetXaxis().SetLabelSize(.05)
			h1[k].GetXaxis().SetTitleSize(.10)
			h1[k].GetXaxis().SetTitleOffset(.7)
			#! Y-axis title aesthetics
			h1[k].GetYaxis().SetTitleOffset(1.5)
			h1[k].GetYaxis().SetTitleSize(.05)
			if self.VIEW=="norm":
				# if var!='THETA':
				# 	h1[k].SetYTitle("#frac{#Delta#sigma}{#Delta%s}[#mub/%s]"%(VAR_NAMES[(vst,var)],VAR_UNIT_NAMES_AFTR_NORM_FCTR_CALC[var]))
				# elif var=='THETA': #! only difference is to add the 'Cos' of DCosTheta
				# 	h1[k].SetYTitle("#frac{#Delta#sigma}{#Deltacos(%s)}[#mub/%s]"%(VAR_NAMES[(vst,var)],VAR_UNIT_NAMES_AFTR_NORM_FCTR_CALC[var]))
				if var!='THETA':
					h1[k].SetYTitle("#Delta#sigma/#Delta%s [#mub/%s]"%(VAR_NAMES[(vst,var)],VAR_UNIT_NAMES_AFTR_NORM_FCTR_CALC[var]))
				elif var=='THETA': #! only difference is to add the 'Cos' of DCosTheta
					h1[k].SetYTitle("#Delta#sigma/#Deltacos(%s) [#mub/%s]"%(VAR_NAMES[(vst,var)],VAR_UNIT_NAMES_AFTR_NORM_FCTR_CALC[var]))
			elif self.VIEW=="fullana":
				h1[k].SetYTitle("\"Normalized\" counts")
			elif self.VIEW=="ERyield":
				h1[k].SetYTitle("Counts")

			if self.VIEW!="ERyield":
				h1[k].SetMarkerColor(CLRS_PLT_SEQ_ALL[seq])
				h1[k].SetLineColor(CLRS_PLT_SEQ_ALL[seq])
				h1[k].SetMarkerStyle(MRKS_PLT_SEQ_ALL[seq])	

	def plot_1D_athtcs(self):
		#ROOT.gStyle.Reset()
		#! Stats Box
		ROOT.gStyle.SetOptStat(0)

		# ROOT.gStyle.SetLabelSize(0.5,"t")
		# ROOT.gStyle.SetTitleSize(0.5,"t")
		#ROOT.gStyle.SetPaperSize(20,26);
		#ROOT.gStyle.SetPadTopMargin(0.15)#(0.05);
		#ROOT.gStyle.SetPadRightMargin(0.15)#(0.05);
		ROOT.gStyle.SetPadBottomMargin(0.20)#(0.16);
		#ROOT.gStyle.SetPadLeftMargin(0.20)#(0.12);

		ROOT.gStyle.SetTitleW(10)# //title width 
		ROOT.gStyle.SetTitleFontSize(20)# 
		ROOT.gStyle.SetTitleH(0.15)# //title height 
		
		#! + The following options do not seem to work from here
		#! + I have to set them in label_hist_obs1D()
		#ROOT.gStyle.SetTitleFont(42,"xyz")
		#ROOT.gStyle.SetTitleSize(.35,"xyz")
		#ROOT.gStyle.SetTitleOffset(0.5,"xyz");

		#!get rid of X error bars and y error bar caps
		ROOT.gStyle.SetErrorX(0.001)

	def get_signed_integral(self,h):
		itg=0
		for i in range(h.GetNbinsX()):
			itg+=math.fabs(h.GetBinContent(i+1))
		return itg

