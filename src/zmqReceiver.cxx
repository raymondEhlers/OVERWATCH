// Adapted from ZMQROOTmerger.cxx in HLT/BASE/utils in AliRoot
//
// Author: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University

#include "zmqReceiver.h"

#include <zmq.h>
#include <iostream>
#include <string>
#include <ctime>

// For timing
#include <chrono>
#include <thread>

#include <AliZMQhelpers.h>

#include <TObject.h>
#include <TMessage.h>
#include <TFile.h>
// If desired for more complicated selections
//#include <TPRegexp.h>

zmqReceiver::zmqReceiver():
  fVerbose(1),
  fRunNumber(kUnknownRunNumber),
  fZMQconfigIn("SUB>tcp://localhost:60201"),
  fSelection(""),
  fHLTMode("B"),
  fSubsystem("EMC"),
  fData(),
  fPollInterval(60000),
  fPollTimeout(10000),
  fZMQcontext(NULL),
  fZMQin(NULL)
{
  // Globally enable schema evolution for serializing ROOT objects
  TMessage::EnableSchemaEvolutionForAll(kTRUE);

  // Create the ZMQ context
  fZMQcontext = alizmq_context();
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
      Printf("Connection timed out. Server %s died?", fZMQconfigIn.c_str());
      int fZMQsocketModeIn = alizmq_socket_init(fZMQin, fZMQcontext, fZMQconfigIn.c_str());
      if (fVerbose) { std::cout << fZMQsocketModeIn << std::endl; }
      if (fZMQsocketModeIn < 0) 
      {
        Printf("Cannot reinit ZMQ socket %s, %s, exiting...", fZMQconfigIn.c_str(), zmq_strerror(errno));
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
      fHLTMode = fInfoMap["HLTmode"];
      continue;
    }

    TObject* object;
    alizmq_msg_iter_data(i, object);
    fData.push_back(object);
  }

  // Close message
  alizmq_msg_close(&message);

  // Write Data
  WriteToFile();
}

//______________________________________________________________________________
void zmqReceiver::WriteToFile()
{
  // Get current time
  time_t now = time(NULL);
  struct tm * timestamp = localtime(&now);

  // Format is SUBSYSTEMhistos_runNumber_hltMode_time.root
  // For example, EMChistos_123456_B_2015_3_14_2_3_5.root
  TString filename = TString::Format("%shistos_%d_%s_%d_%d_%d_%d_%d_%d.root", fSubsystem.c_str(), fRunNumber, fHLTMode.c_str(), timestamp->tm_year+1900, timestamp->tm_mon+1, timestamp->tm_mday, timestamp->tm_hour, timestamp->tm_min, timestamp->tm_sec);

  // Create file
  TFile * fOut = new TFile(filename.Data(), "RECREATE");

  // Iterate over all objects and write them to the file
  for (std::vector<TObject *>::iterator it = fData.begin(); it != fData.end(); ++it)
  {
    if (fVerbose) Printf("writing object %s to %s",(*it)->GetName(), filename.Data());
    (*it)->Write((*it)->GetName());
  }

  // Close file
  fOut->Close();
  delete fOut;
}

//______________________________________________________________________________
void zmqReceiver::SendRequest()
{
  std::string request = "";
  if (fSelection != "")
  {
    request += " select=";
    request += fSelection.c_str();
  }
  alizmq_msg_send("CONFIG", request, fZMQin, ZMQ_SNDMORE);
  //alizmq_msg_send("CONFIG", "select=EMC*", fZMQin, ZMQ_SNDMORE);
  if (fVerbose) Printf("sending request CONFIG %s", request.c_str());
  alizmq_msg_send("", "", fZMQin, 0);
}

//_______________________________________________________________________________________
void zmqReceiver::ClearData()
{
  for (std::vector<TObject *>::iterator it = fData.begin(); it != fData.end(); ++it)
  {
    delete *it;
  }
  fData.clear();
}

//______________________________________________________________________________
int zmqReceiver::ProcessOption(TString option, TString value)
{
  //process option
  //to be implemented by the user

  if (option.EqualTo("ZMQconfigIN") || option.EqualTo("in"))
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
  rc += alizmq_socket_init(fZMQin,  fZMQcontext, fZMQconfigIn.c_str());

  return rc;
}

//______________________________________________________________________________
void zmqReceiver::Cleanup()
{
  // Destory zmq sockets
  // TEMP
  //alizmq_socket_close(fZMQin);

  // Terminate the context
  zmq_ctx_term(fZMQcontext);
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
