// Adapted from ZMQROOTmerger.cxx in HLT/BASE/utils in AliRoot
//
// Author: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University

#include "zmqReceiver.h"

#include <zmq.h>
#include <iostream>
#include <string>
#include <ctime>
#include <cstdlib>

#include <AliHLTDataTypes.h>
#include <AliHLTComponent.h>
#include <AliHLTMessage.h>
#include <AliZMQhelpers.h>

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
    fZMQconfigIN("SUB>tcp://localhost:60201"),
    fHistIdentifier("EMCTRQA"),
    fDirPrefix(""),
    fPreviousObjectName(""),
    fMergeAfterObjectName(""),
    fLockInMergeName(kFALSE),
    fJustWroteFile(kFALSE),
    fMaxObjects(10),
    fZMQcontext(NULL),
    fZMQin(NULL),
    fZMQinternal(NULL)
{
    // Don't need to actually initialize anything.
    // NOTE: A few of these options can be changed with command line arguments
    fPreviousObjectTime = time(0);
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
    ResetOutputData();
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
            resetAllData();
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

//_______________________________________________________________________________________
int zmqReceiver::Run()
{
    int rc = 0;

    // Set the time here in case we miss the start of the run
    fPreviousObjectTime = time(0);
    
    //main loop
    while(1)
    {
        errno = 0;

        int inType = alizmq_socket_type(fZMQin);

        // request first
        // We don't think this is currently needed by the HLT
        // Can adapt if needed
        if (inType==ZMQ_REQ) SendRequest(fZMQin);

        //wait for the data
        //poll sockets - we want to take action on one of two conditions:
        //  1 - request comes in - then we merge whatever is not yet merged and send
        //  2 - data comes in - then we add it to the merging list
        zmq_pollitem_t sockets[] = { 
            { fZMQin, 0, ZMQ_POLLIN, 0 },
            { fZMQinternal, 0, ZMQ_POLLIN, 0 },
        };
        rc = zmq_poll(sockets, 2, -1); //poll sockets
        if (rc==-1 && errno==ETERM)
        {
            //this can only happen it the context was terminated, one of the sockets are
            //not valid or operation was interrupted
            Printf("zmq_poll was interrupted! rc = %i, %s", rc, zmq_strerror(errno));
            break;
        }

        //data present socket 0 - in
        if (sockets[0].revents & ZMQ_POLLIN)
        {
            // Receive message
            aliZMQmsg message;
            alizmq_msg_recv(&message, fZMQin, 0);

            // Finish processing message
            for (aliZMQmsg::iterator i=message.begin(); i!=message.end(); ++i)
            {
                HandleDataIn(i->first, i->second, fZMQin);
            }

            alizmq_msg_close(&message);
        }

    }//main loop

    return 0;
}

//______________________________________________________________________________
int zmqReceiver::SendRequest(void*)
{
    return 0;
}

//______________________________________________________________________________
void zmqReceiver::ResetOutputData()
{
    fMergeObjectMap.DeleteAll();
}

//______________________________________________________________________________
void zmqReceiver::resetAllData()
{
    // Iterate over all objects to ensure nothing is missed
    TIter mapIter(&fMergeObjectMap);
    TObject* objectNameStr = NULL;
    while ((objectNameStr = mapIter.Next()))
    {
        TList* mergingList = static_cast<TList*>(fMergeListMap.GetValue(objectNameStr->GetName()));
        mergingList->Clear();
    }

    ResetOutputData();
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

    if (option.EqualTo("reset")) 
    {
        ResetOutputData();
    }
    else if (option.EqualTo("MaxObjects"))
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
        fZMQconfigIN = value;
    }
    else if (option.EqualTo("verbose"))
    {
        fVerbose = value.Atoi();
    }

    return 1; 
}

//_______________________________________________________________________________________
int zmqReceiver::InitZMQ()
{
    //init or reinit stuff
    int rc = 0;
    rc += alizmq_socket_init(fZMQin,  fZMQcontext, fZMQconfigIN.Data(), 0);
    
    // Set subscription
    //rc += zmq_setsockopt(fZMQin, ZMQ_SUBSCRIBE, fZMQsubscriptionIN.Data(), fZMQsubscriptionIN.Length());

    return rc;
}

//______________________________________________________________________________
void zmqReceiver::cleanup()
{
    // Destory zmq sockets
    zmq_close(fZMQin);
    //zmq_close(fZMQmon);
    //zmq_close(fZMQout);
    zmq_ctx_destroy(fZMQcontext);
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
    stringMap* options = TokenizeOptionString(arguments);
    for (stringMap::iterator i=options->begin(); i!=options->end(); ++i)
    {
        //Printf("  %s : %s", i->first.data(), i->second.data());
        ProcessOption(i->first,i->second);
    }
    delete options; //tidy up

    return 1; 
}

//______________________________________________________________________________
stringMap* zmqReceiver::TokenizeOptionString(const TString str)
{
    //options have the form:
    // -option value
    // -option=value
    // -option
    // --option value
    // --option=value
    // --option
    // option=value
    // option value
    // (value can also be a string like 'some string')
    //
    // options can be separated by ' ' or ',' arbitrarily combined, e.g:
    //"-option option1=value1 --option2 value2, -option4=\'some string\'"

    //optionRE by construction contains a pure option name as 3rd submatch (without --,-, =)
    //valueRE does NOT match options
    TPRegexp optionRE("(?:(-{1,2})|((?='?[^,=]+=?)))"
            "((?(2)(?:(?(?=')'(?:[^'\\\\]++|\\.)*+'|[^, =]+))(?==?))"
            "(?(1)[^, =]+(?=[= ,$])))");
    TPRegexp valueRE("(?(?!(-{1,2}|[^, =]+=))"
            "(?(?=')'(?:[^'\\\\]++|\\.)*+'"
            "|[^, =]+))");

    stringMap* options = new stringMap;

    TArrayI pos;
    const TString mods="";
    Int_t start = 0;
    while (1) {
        Int_t prevStart=start;
        TString optionStr="";
        TString valueStr="";

        //check if we have a new option in this field
        Int_t nOption=optionRE.Match(str,mods,start,10,&pos);
        if (nOption>0)
        {
            optionStr = str(pos[6],pos[7]-pos[6]);
            optionStr=optionStr.Strip(TString::kBoth,'\'');
            start=pos[1]; //update the current character to the end of match
        }

        //check if the next field is a value
        Int_t nValue=valueRE.Match(str,mods,start,10,&pos);
        if (nValue>0)
        {
            valueStr = str(pos[0],pos[1]-pos[0]);
            valueStr=valueStr.Strip(TString::kBoth,'\'');
            start=pos[1]; //update the current character to the end of match
        }

        //skip empty entries
        if (nOption>0 || nValue>0)
        {
            (*options)[optionStr.Data()] = valueStr.Data();
        }

        if (start>=str.Length()-1 || start==prevStart ) break;
    }

    //for (stringMap::iterator i=options->begin(); i!=options->end(); ++i)
    //{
    //  printf("%s : %s\n", i->first.data(), i->second.data());
    //}
    return options;
}


