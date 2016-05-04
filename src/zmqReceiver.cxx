// Adapted from ZMQROOTmerger.cxx in HLT/BASE/utils in AliRoot
//
// Author: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University

#include "zmqReceiver.h"

#include <zmq.h>
#include <iostream>
#include <string>
//#include <ctime>
#include <cstdlib>

// For timing
#include <chrono>
#include <thread>

#include <AliHLTDataTypes.h>
#include <AliHLTComponent.h>
#include <AliHLTMessage.h>
#include <AliZMQhelpers.h>

#include <TObject.h>
#include <TSystem.h>
#include <TClass.h>
#include <TMap.h>
#include <TPRegexp.h>
#include <TObjString.h>
#include <TList.h>
#include <TMessage.h>
#include <TRint.h>
#include <TApplication.h>
#include <TROOT.h>
#include <TTimeStamp.h>
#include <TKey.h>
#include <TH1.h>
#include <TFile.h>

zmqReceiver::zmqReceiver():
  fVerbose(1),
  fHistogramGroupCounter(0),
  fMaxTimeBetweenObjects(0.1),
  fPreviousObjectTime(0),
  fMaxWaitTime(1),
  fRunNumber(kUnknownRunNumber),
  fZMQconfigIn("SUB>tcp://localhost:60201"),
  fHistIdentifier("EMCTRQA"),
  fDirPrefix(""),
  fPreviousObjectName(""),
  fMergeAfterObjectName(""),
  fLockInMergeName(kFALSE),
  fJustWroteFile(kFALSE),
  fMaxObjects(10),
  fSelection(""),
  fData(),
  fPollInterval(60000),
  fPollTimeout(10000),
  fZMQcontext(NULL),
  fZMQin(NULL),
  fZMQinternal(NULL)
{
  // Globally enable schema evolution for serializing ROOT objects
  TMessage::EnableSchemaEvolutionForAll(kTRUE);

  // Create the ZMQ context
  fZMQcontext = alizmq_context();
}

//_______________________________________________________________________________________
TFile * zmqReceiver::initializeNewRunFile(Bool_t endOfRun, Bool_t missedStartOfRun)
{
  Int_t runNumber = -1;
  if (missedStartOfRun == kTRUE)
  {
    runNumber = kUnknownRunNumber;
  }
  else
  {
    runNumber = fRunNumber;
  }

  TString dir = "";
  if (fDirPrefix != "")
  {
    dir = Form("%s/Run%i", fDirPrefix.Data(), runNumber);
  }
  else
  {
    dir = Form("Run%i", runNumber);
  }
  // Create the directory if necessary 
  gSystem->Exec(Form("mkdir -p %s", dir.Data()));

  // Will only possible be passed at true at the end of run
  if (missedStartOfRun == kTRUE && endOfRun == kTRUE)
  {
    // Create file with the proper run number to allow for renaming later!
    gSystem->Exec(Form("touch %s/%i", dir.Data(), fRunNumber));
  }

  TString filename = "";
  filename = Form("%s/hists.%.0ld.root", dir.Data(), time(0));
  /*if (endOfRun == kTRUE)
   {
   filename = Form("%s/hists.root", dir.Data());
   }
   else
   {
   filename = Form("%s/hists.%.0ld.root", dir.Data(), time(0));
   }*/

  if (fVerbose > 0) { Printf("Opening file %s", filename.Data()); }

  TFile * fOut = TFile::Open(filename.Data(), "RECREATE");

  return fOut;
}

//_______________________________________________________________________________________
void zmqReceiver::mergeHists(TH1 * mergeInto, TList * mergingList)
{
  if (fVerbose > 1)
  {
    Printf("*****\nMerging list! List has %i entries", mergingList->GetEntries());
    Printf("mergeInto entries before merge: %.1f", mergeInto->GetEntries());
  }

  // Get objects from list and merge
  TIter listIter(mergingList); 
  TObject * object = 0;
  while ((object = listIter.Next()))
  {
    mergeInto->Add((TH1 *) object);
  }

  // Cleanup after the merge
  mergingList->Clear();

  if (fVerbose > 1)
  {
    Printf("mergeInto entries after merge: %.1f", mergeInto->GetEntries());
    Printf("List Merged! List now has %i entries\n*****", mergingList->GetEntries());
  }
}

//_______________________________________________________________________________________
void zmqReceiver::mergeAllHists()
{
  if (fVerbose > 1) { Printf("\n*****"); }
  if (fVerbose > 0) { Printf("Merging all histograms!"); }

  // Iterate over all objects to ensure nothing is missed
  TIter mapIter(&fMergeObjectMap);
  TObject* objectNameStr = NULL;
  while ((objectNameStr = mapIter.Next()))
  {
    TList* mergingList = static_cast<TList*>(fMergeListMap.GetValue(objectNameStr->GetName()));

    // Get hist to merge into
    TH1 * tempHist = static_cast<TH1 *>(fMergeObjectMap.GetValue(objectNameStr));
    if (fVerbose > 0) { Printf("Merging hist: %s", tempHist->GetName()); }

    // If the list isn't returned then it somehow wasn't created. Merging certainly won't work.
    if (mergingList != 0)
    {
      mergeHists(tempHist, mergingList); 
    }
  }

  if (fVerbose > 1) { Printf("\n*****"); }
}

//_______________________________________________________________________________________
void zmqReceiver::writeFile(Bool_t endOfRun, Bool_t missedStartOfRun)
{
  TFile * fOut = initializeNewRunFile(endOfRun, missedStartOfRun);

  if (fVerbose > 1) { Printf("\n*****"); }

  // Ensure everything is merged first.
  mergeAllHists();

  TIter mapIter(&fMergeObjectMap);
  TObject* objectNameStr = NULL;
  while ((objectNameStr = mapIter.Next()))
  {
    //TList* mergingList = static_cast<TList*>(fMergeListMap.GetValue(objectNameStr->GetName()));

    // Get hist to merge into
    TH1 * tempHist = static_cast<TH1 *>(fMergeObjectMap.GetValue(objectNameStr));
    /*if (fVerbose > 1) { Printf("\n*****"); }
     if (fVerbose > 0) { Printf("Merging hist: %s", tempHist->GetName()); }

     if (mergingList != 0)
     {
     mergeHists(tempHist, mergingList); 
     }*/

    // Save the merged hist
    if (fVerbose > 0) { Printf("Saving hist: %s", tempHist->GetName()); }
    TH1 * clonedTempHist = static_cast<TH1 *>(tempHist->Clone());
    //TH1 * clonedTempHist = static_cast<TH1 *>(tempHist->Clone(Form("%sClone", tempHist->GetName()) ));
    clonedTempHist->Write();

    //tempHist->SetDirectory(0);
  }

  if (fVerbose > 1) { Printf("*****\n"); }

  // Reset for next run
  // Write is not necessary since the histograms have already been written!
  fOut->Close();

  if (endOfRun == kTRUE)
  {
    if (fVerbose > 1) { Printf("End of run. Clearing main histograms and resetting counter."); }
  }

  // Reset data for next set
  //ResetOutputData();
  // Reset for hist counting
  fLockInMergeName = kFALSE;
  fHistogramGroupCounter = 0;
  fMaxTimeBetweenObjects = 0.1;
  fPreviousObjectName = "";
  fMergeAfterObjectName = "";
  fJustWroteFile = kTRUE;
}

//_____________________________________________________________________
void zmqReceiver::processReceivedHistogram(TH1 * object)
{
  if (object)
  {

    const char* name = object->GetName();

    // If the identifier is not contained then we are not interested
    if (fVerbose > 1) { Printf("Object name: %s", name); }
    if (strstr(name, fHistIdentifier.Data()) != NULL)
    {
      // Handle if file is just written
      if (fJustWroteFile == kTRUE)
      {
        fPreviousObjectTime = time(0);
        fJustWroteFile = kFALSE;
        if (fVerbose > 0) { Printf("Resetting time after writing to file."); }
      }

      // Now handle object
      TList* mergingList = static_cast<TList*>(fMergeListMap.GetValue(name));
      TObject* mergingObject = fMergeObjectMap.GetValue(name);
      if (!mergingObject)
      {
        if (fVerbose > 0) { Printf("adding %s to fMergeObjectMap as first instance", name); }
        fMergeObjectMap.Add(new TObjString(name), object);
      }
      else if (!mergingList) 
      {
        if (fVerbose > 0) { Printf("adding a new list %s to fMergeListMap", name); }
        //if (fVerbose > 0) Printf("adding a new list %s to fMergeObjectMap", name);
        mergingList = new TList();
        mergingList->SetOwner();
        fMergeListMap.Add(new TObjString(name), mergingList);

        // Still need to add the object to the list we just created 
        mergingList->Add(object);
      }
      else
      {
        //add object and maybe merge
        if (fVerbose > 0) { Printf("Adding object name %s to list containing %i entries before the addition", name, mergingList->GetEntries()); }
        mergingList->Add(object);

        // We don't want to merge until the name is locked in.
        if (mergingList->GetEntries() >= fMaxObjects && fLockInMergeName == kTRUE && (fMergeAfterObjectName == name) )
        {
          if (fVerbose > 0) { Printf("%i %s's in, starting merging because hit max number of objects in list",mergingList->GetEntries(),name); }
          mergeAllHists();
        }
      }
      // Immediately merge each individual object
      /*else
       {
       if (fVerbose > 0) { Printf("Merging object %s", name); }
       if (!strcmp(name, "histEMCalPatchAmpREJEOnline")) { fCounter++; Printf("Counter: %i", fCounter); }
       if (fCounter >= fMaxObjects)
       {
      //TFile * fOut = initializeNewRunFile();
      writeFile(kFALSE);
      fCounter = 0;
      }
      TH1 * tempHist = static_cast<TH1 *>(fMergeObjectMap.GetValue(name));
      tempHist->Add(static_cast<TH1 *>(object));
      }*/

      // After the proper name is set, increment each time we see the hist
      if ((fMergeAfterObjectName == name) && fHistogramGroupCounter > 0)
      {
        ++fHistogramGroupCounter;
        if (fVerbose > 0) { Printf("Seeing mergeAfter hist %s. Group %i has completed!", name, fHistogramGroupCounter); }
        // If we have gotten past group 5 and the name is still not locked, then lock it anyway.
        // We usually have the right name at this point, and we don't want a fluctuation in time
        // to ruin that.
        if (fHistogramGroupCounter > 5 && fLockInMergeName != kTRUE)
        {
          fLockInMergeName = kTRUE;
          if (fVerbose > 0) { Printf("Locking in mergeAfter as %s due to taking too long to lock in.", fMergeAfterObjectName.Data()); }
        }
      }

      // Determine when to merge and write
      if ( ((time(0) - fPreviousObjectTime) >= fMaxTimeBetweenObjects) && fLockInMergeName != kTRUE)
      {
        // Only notify if the name is new and isn't the first time that it is set!
        if ((fMergeAfterObjectName != fPreviousObjectName) && (fMergeAfterObjectName != ""))
        {
          if (fVerbose > 0) { Printf("Setting mergeAfter to %s with time difference of %f, as compared to the previous value of %s with time diff %f", fPreviousObjectName.Data(), time(0) - fPreviousObjectTime, fMergeAfterObjectName.Data(), fMaxTimeBetweenObjects); }
          if (fHistogramGroupCounter > 0 && fVerbose > 0)
          {
            // Check to see if same and print message if different.
            Printf("Changing merge after from %s to %s", fMergeAfterObjectName.Data(), fPreviousObjectName.Data());
          }
        }
        else
        {
          // We should only be here after setting the appropriate name once. 
          if ((fMergeAfterObjectName == fPreviousObjectName) && (fMergeAfterObjectName != ""))
          {
            // Lock in name!
            fLockInMergeName = kTRUE;
            if (fVerbose > 0) { Printf("Locking in mergeAfter as %s", fMergeAfterObjectName.Data()); }
          }
        }

        // This almost certainly occurs without the above statement when it is being set for 
        // the first time. It will often be too short and not at the end, so we aren't interested
        // Hence the > 1, suppressing it most of the time
        if (fVerbose > 0) { Printf("Setting merge after to %s with time difference of %f, as compared to the previous value of %s with time diff %f. Outside of if statement", fPreviousObjectName.Data(), time(0) - fPreviousObjectTime, fMergeAfterObjectName.Data(), fMaxTimeBetweenObjects); }

        // Set merge control variables 
        fMaxTimeBetweenObjects = time(0) - fPreviousObjectTime;
        fMergeAfterObjectName = fPreviousObjectName;

        // Increment counter if time is more than one fMaxWaitTime. This will ignore changes in the
        // first time through where we be in between hists
        if ((fMaxTimeBetweenObjects > fMaxWaitTime) && fLockInMergeName != kTRUE)
        {
          ++fHistogramGroupCounter;
        }
      }

      // Reset timer
      //if (fVerbose > 0) { Printf("fMergeAfterObjectName: %s", fMergeAfterObjectName.Data()); }
      //Printf("fPreviousObjectName: %s, fPreviousObjectTime: %f, fLockInMergeName: %i", fPreviousObjectName.Data(), fPreviousObjectTime, fLockInMergeName);
      fPreviousObjectName = name;
      fPreviousObjectTime = time(0);

      // Write out file at the appropraite time
      // 60*10 seconds = 10 minutes
      if ((fHistogramGroupCounter >= 12) && fLockInMergeName == kTRUE && (fMergeAfterObjectName == name) )
      {
        writeFile(kFALSE);
      }
    }
  }
  else
  {
    if (fVerbose > 0) { Printf("no object!"); }
  }
}

//_____________________________________________________________________
int zmqReceiver::HandleDataIn(zmq_msg_t* topicMsg, zmq_msg_t* dataMsg, void* socket)
{
  // Just for clarity in printing when working with lots of debug information
  if (fVerbose > 1) { Printf("*****"); }

  //handle the message
  //add to the list of objects to merge for each object type (by name)
  //topic
  AliHLTDataTopic dataTopic;
  memcpy(&dataTopic, zmq_msg_data(topicMsg),std::min(zmq_msg_size(topicMsg),sizeof(dataTopic)));
  if (fVerbose > 1) { Printf("in: data: %s", dataTopic.Description().c_str()); }

  // Classify the various messages
  // Start of Run
  if (!memcmp(dataTopic.GetID().c_str(), kAliHLTDataTypeSOR.fID, kAliHLTComponentDataTypefIDsize))
  {
    AliHLTRunDesc run;
    memcpy(&run, zmq_msg_data(dataMsg), zmq_msg_size(dataMsg));
    fRunNumber = run.fRunNo;

    // TODO: If missed EOR, clear list and objects
    if (fMergeObjectMap.GetEntries() != 0)
    {
      if (fVerbose > 0) { Printf("Missed EOR. Clearing previous data."); }
      //resetAllData();
    }

    if (fVerbose > 0) { Printf("Start of run %i!", fRunNumber); }

    // Set the time here
    fPreviousObjectTime = time(0);
  }
  // End of Run
  else if (!memcmp(dataTopic.GetID().c_str(), kAliHLTDataTypeEOR.fID, kAliHLTComponentDataTypefIDsize))
  {
    // Process message
    AliHLTRunDesc run;
    memcpy(&run, zmq_msg_data(dataMsg), zmq_msg_size(dataMsg));

    if (fVerbose > 0) { Printf("End of run %i!", run.fRunNo); }

    Bool_t missedStartOfRun = kFALSE;
    if (fRunNumber == kUnknownRunNumber)
    {
      if (fVerbose > 0) { Printf("Missed start of run number %i. Creating file for proper run number!", run.fRunNo); }
      missedStartOfRun = kTRUE;
    }

    fRunNumber = run.fRunNo;

    // Handle end of run
    // Open file and then save out hists with proper merging if neessary
    //TFile * fOut = initializeNewRunFile(kTRUE, missedStartOfRun);
    writeFile(kTRUE, missedStartOfRun);

    //TEMP
    // Quit after finishing run 12
    /*if (run.fRunNo > 11)
     {
     std::exit(0);
     }*/
    //END TEMP
  }
  // TH1 histogram
  else if (!memcmp(dataTopic.GetID().c_str(), kAliHLTDataTypeHistogram.fID, kAliHLTComponentDataTypefIDsize))
  {
    if (fVerbose > 1) { Printf("Histogram found!"); }
    // Process message
    TObject* object = UnpackMessage(dataMsg );

    processReceivedHistogram(static_cast<TH1*>(object));
  }
  else
  {
    if (fVerbose > 0) { Printf("Not recognized as SOR, EOR or histogram!"); }
  }

  // Just for clarity in printing when working with lots of debug information
  if (fVerbose > 1) { Printf("*****\n"); }

  return 0;
}

//////////////////////////////////////////////////////////////////////////////////////////////

//_______________________________________________________________________________________
void zmqReceiver::ClearData()
{
  for(std::vector<TObject *>::iterator it = fData.begin(); it != fData.end(); ++it)
  {
    delete *it;
  }
  fData.clear();
}

//_______________________________________________________________________________________
int zmqReceiver::Run()
{
  int rc = 0;

  //main loop
  while(1)
  {
    errno = 0;

    // Request the data
    SendRequest();

    // Wait for the data
    zmq_pollitem_t sockets[] = { 
      { fZMQin, 0, ZMQ_POLLIN, 0 },
    };

    // poll sockets
    // The second argument denotes the number of sockets that are being polled
    // The third argument is the timeout
    rc = zmq_poll(sockets, 1, -1); 
    if (rc==-1 && errno == ETERM)
    {
      // This can only happen it the context was terminated, one of the sockets are
      // not valid or operation was interrupted
      Printf("ZMQ context was terminated! Bailing out! rc = %i, %s", rc, zmq_strerror(errno));
      return -1;
    }

    // Handle if server died
    if (!(sockets[0].revents & ZMQ_POLLIN))
    {
      //server died
      Printf("Connection timed out. Server %s died?", fZMQconfigIn.Data());
      int fZMQsocketModeIn = alizmq_socket_init(fZMQin, fZMQcontext, fZMQconfigIn.Data());
      if (fVerbose) { std::cout << fZMQsocketModeIn << std::endl; }
      if (fZMQsocketModeIn < 0) 
      {
        Printf("Cannot reinit ZMQ socket %s, %s, exiting...", fZMQconfigIn.Data(), zmq_strerror(errno));
        return -1;
      }

      continue;
    }
    // data present socket 0 - in
    else if (sockets[0].revents & ZMQ_POLLIN)
    {
      ReceiveData();
    }

    // Set the sleep time here (equivalent to the poll interval)
    std::this_thread::sleep_for(std::chrono::milliseconds(fPollInterval));

  }//main loop

  return 0;
}

//______________________________________________________________________________
void zmqReceiver::ReceiveData()
{
  // Clear previous data
  ClearData();
  
  // Receive message
  aliZMQmsg message;
  alizmq_msg_recv(&message, fZMQin, 0);

  // Processing messages
  for (aliZMQmsg::iterator i=message.begin(); i!=message.end(); ++i)
  {
    if (alizmq_msg_iter_check(i, "INFO")==0)
    {
      //check if we have a runnumber in the string
      std::string info;
      alizmq_msg_iter_data(i,info);
      if (fVerbose) { Printf("processing INFO %s", info.c_str()); }
      
      stringMap fInfoMap = ParseParamString(info);

      // Retrieve run number and HLT mode
      fRunNumber = atoi(fInfoMap["run"].c_str());
      fHLTmode = fInfoMap["HLTmode"];
      continue;
    }

    TObject* object;
    alizmq_msg_iter_data(i, object);
    fData.push_back(object);
    //HandleDataIn(i->first, i->second, fZMQin);
  }

  alizmq_msg_close(&message);

  // Write Data
  writeToFile();
}

//______________________________________________________________________________
void writeToFile()
{
  //
}

//______________________________________________________________________________
void zmqReceiver::SendRequest()
{
  std::string request = "";
  if (fSelection != "")
  {
    request += " select=";
    request += fSelection.Data();
  }
  alizmq_msg_send("CONFIG", request, fZMQin, ZMQ_SNDMORE);
  //alizmq_msg_send("CONFIG", "select=EMC*", fZMQin, ZMQ_SNDMORE);
  if (fVerbose) Printf("sending request CONFIG %s", request.c_str());
  alizmq_msg_send("", "", fZMQin, 0);
}

//______________________________________________________________________________
int zmqReceiver::ProcessOption(TString option, TString value)
{
  //process option
  //to be implemented by the user

  //if (option.EqualTo("ZMQpollIn"))
  //{
  //  fZMQpollIn = (value.EqualTo("0"))?kFALSE:kTRUE;
  //}

  if (option.EqualTo("MaxObjects"))
  {
    fMaxObjects = value.Atoi();
  }
  else if (option.EqualTo("histIdentifier"))
  {
    fHistIdentifier = value;
  }
  else if (option.EqualTo("dirPrefix"))
  {
    fDirPrefix = value;
  }
  else if (option.EqualTo("ZMQconfigIN") || option.EqualTo("in"))
  {
    fZMQconfigIn = value;
  }
  else if (option.EqualTo("verbose"))
  {
    fVerbose = value.Atoi();
  }
  else if (option.EqualTo("select"))
  {
    fSelection = value;
  }
  else if (option.EqualTo("PollInterval") || option.EqualTo("sleep"))
  {
    fPollInterval = round(value.Atof()*1e3);
  }
  else if (option.EqualTo("PollTimeout") || option.EqualTo("timeout"))
  {
    fPollTimeout = round(value.Atof()*1e3);
  }

  return 1; 
}

//_______________________________________________________________________________________
int zmqReceiver::InitZMQ()
{
  // Init or reinit stuff
  int rc = 0;
  rc += alizmq_socket_init(fZMQin,  fZMQcontext, fZMQconfigIn.Data());

  return rc;
}

//______________________________________________________________________________
void zmqReceiver::Cleanup()
{
  // Destory zmq sockets
  alizmq_socket_close(fZMQin);

  // Terminate the context
  zmq_ctx_term(fZMQcontext);
}

//_______________________________________________________________________________________
TObject* zmqReceiver::UnpackMessage(zmq_msg_t* message)
{
  size_t size = zmq_msg_size(message);
  void* data = zmq_msg_data(message);

  TObject* object = NULL;
  object = AliHLTMessage::Extract(data, size);
  return object;
}

////////////////////////////////////////////////////////////////////////////////

//______________________________________________________________________________
int zmqReceiver::ProcessOptionString(TString arguments)
{
  //process passed options
  aliStringVec* options = AliOptionParser::TokenizeOptionString(arguments);
  for (aliStringVec::iterator i=options->begin(); i!=options->end(); ++i)
  {
    //Printf("  %s : %s", i->first.data(), i->second.data());
    ProcessOption(i->first,i->second);
  }
  delete options; //tidy up

  return 1; 
}
