#ifndef ZMQRECEIVER_H /* zmqReceiver.h */
#define ZMQRECEIVER_H
//
// Adapted from ZMQROOTmerger.cxx in HLT/BASE/utils in AliRoot
//
// Author: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University

#include <map>
#include <zmq.h>

#include <TString.h>
#include <TMap.h>
#include <TFile.h>
#include <TH1.h>

class zmqReceiver 
{
 public:
  // Initialize class
  zmqReceiver();
  virtual ~zmqReceiver() {}

  // Helper functions
  int ProcessOptionString(TString arguments);

  // Main usage functions
  int InitZMQ();
  int Run();
  // Close all sockets and destroy context
  void Cleanup();

 protected:
  // Types
  enum runNumberTypes { kUnknownRunNumber = 12345678 };
  typedef std::map<std::string,std::string> stringMap;

  // Methods
  // Parsing
  int ProcessOption(TString option, TString value);
  // Run setup
  TFile * initializeNewRunFile(Bool_t endOfRun = kFALSE, Bool_t missedStartOfRun = kFALSE);
  void writeFile(Bool_t endOfRun = kFALSE, Bool_t missedStartOfRun = kFALSE);
  // Data management
  void ReceiveData();
  void ClearData();
  void writeToFile();
  int HandleDataIn(zmq_msg_t* topicMsg, zmq_msg_t* dataMsg, void* /*socket*/=NULL);
  void processReceivedHistogram(TH1 * object);
  void mergeHists(TH1 * mergeInto, TList * mergingList);
  void mergeAllHists();
  // ZMQ data management
  TObject * UnpackMessage(zmq_msg_t* message);
  // ZMQ request
  void SendRequest();

  // configuration vars
  Int_t fVerbose;
  Int_t fHistogramGroupCounter;
  Double_t fPreviousObjectTime;
  Double_t fMaxTimeBetweenObjects;
  Double_t fMaxWaitTime;
  Int_t fRunNumber;
  TString fZMQconfigIn;
  //AliHLTDataTopic subscribeType = kAliHLTDataTypeHistogram;
  //TString fZMQsubscriptionIN = subscribeType.Description().c_str();
  TString fHistIdentifier;
  TString fDirPrefix;
  TString fPreviousObjectName;
  TString fMergeAfterObjectName;
  Bool_t fLockInMergeName;
  Bool_t fJustWroteFile;

  std::vector <TObject *> fData; // Contains received objects
  TString fSelection;
  int fPollInterval; // In milliseconds
  int fPollTimeout; // In milliseconds

  // internal state
  TMap fMergeObjectMap;        //map of the merged objects, all incoming stuff is merged into these
  TMap fMergeListMap;          //map with the lists of objects to be merged in
  int fMaxObjects;        //trigger merge after this many messages

  //ZMQ stuff
  void* fZMQcontext;    //ze zmq context

  void* fZMQin;        //the in socket - entry point for the data to be merged.
  void* fZMQinternal;   //the pair socket for thread communication
};

#endif /* zmqReceiver.h */
