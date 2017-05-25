// Adapted from ZMQROOTmerger.cxx in HLT/BASE/utils in AliRoot
//
// Author: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University

#include "zmqReceiver.h"

#include <zmq.h>
#include <iostream>
#include <string>
#include <sstream>
#include <ctime>

// For timing
#include <chrono>
#include <thread>

#include <AliZMQhelpers.h>
#include <AliOptionParser.h>

#include <TObject.h>
#include <TMessage.h>
#include <TFile.h>
// If desired for more complicated selections
//#include <TPRegexp.h>

using namespace AliZMQhelpers;

zmqReceiver::zmqReceiver():
  fVerbose(0),
  fRunNumber(kUnknownRunNumber),
  fResetMerger(false),
  fSubsystem("EMC"),
  fHLTMode("B"),
  fSelection(""),
  fPollInterval(60000),
  fPollTimeout(10000),
  fZMQconfigIn("SUB>tcp://localhost:60201"),
  fData(),
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

  std::cout << PrintConfiguration() << std::endl;

  //main loop
  while(1)
  {
    errno = 0;

    // Request the data
    SendRequest();

    // Define ZMQ sockets
    zmq_pollitem_t sockets[] = { 
      { fZMQin, 0, ZMQ_POLLIN, 0 },
    };

    // Wait for the data by polling sockets
    // The second argument denotes the number of sockets that are being polled
    // The third argument is the timeout
    rc = zmq_poll(sockets, 1, -1); 
    if (rc==-1 && errno == ETERM)
    {
      // This can only happen it the context was terminated, one of the sockets are
      // not valid, or operation was interrupted
      Printf("ZMQ context was terminated! Bailing out! rc = %i, %s", rc, zmq_strerror(errno));
      return -1;
    }

    // Handle if server died
    if (!(sockets[0].revents & ZMQ_POLLIN))
    {
      // Server died
      Printf("Connection timed out. Server %s died?", fZMQconfigIn.c_str());
      int fZMQsocketModeIn = alizmq_socket_init(fZMQin, fZMQcontext, fZMQconfigIn.c_str());
      if (fVerbose) { std::cout << fZMQsocketModeIn << std::endl; }
      if (fZMQsocketModeIn < 0) 
      {
        Printf("Cannot reinit ZMQ socket %s, %s, exiting...", fZMQconfigIn.c_str(), zmq_strerror(errno));
        return -1;
      }

      // If we managed to reinitialize the socket, then we start over again
      continue;
    }
    // Data present in socket 0 (ie fZMQin)
    else if (sockets[0].revents & ZMQ_POLLIN)
    {
      ReceiveData();
    }

    // Sleep so that we are not constantly requesting data
    std::this_thread::sleep_for(std::chrono::milliseconds(fPollInterval));

  }

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

  // Processing message data
  for (aliZMQmsg::iterator i=message.begin(); i!=message.end(); ++i)
  {
    // Check for information about the data
    if (alizmq_msg_iter_check_id(i, "INFO")==0)
    {
      // Retrieve info about the data
      std::string info;
      alizmq_msg_iter_data(i, info);
      if (fVerbose) { Printf("processing INFO %s", info.c_str()); }
      
      // Parse the info string
      stringMap fInfoMap = ParseParamString(info);

      // Retrieve run number and HLT mode
      fRunNumber = atoi(fInfoMap["run"].c_str());
      fHLTMode = fInfoMap["HLT_MODE"];

      if (fVerbose) { Printf("Received:\n\tRun Number: %i\n\tHLT Mode: %s\n", fRunNumber, fHLTMode.c_str()); }

      // Now move onto processing the actual data
      continue;
    }

    // Store the data to be written out
    TObject* object;
    alizmq_msg_iter_data(i, object);
    fData.push_back(object);
  }

  // Close message
  alizmq_msg_close(&message);

  // The HLT sends run number 0 after it is has reset receivers at the end of a run.
  // We shouldn't bother writing out the file in that case.
  if (fRunNumber != 0)
  {
    // Write Data
    WriteToFile();
  }
  else {
    Printf("fRunNumber == 0. Not printing, since this is not a real run!");
  }
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

  if (fVerbose) { std::cout << "Writing " << fData.size() << " objects to " << filename.Data() << std::endl; }

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
  if (fResetMerger == true)
  {
    request += " ResetOnRequest";
  }
  alizmq_msg_send("CONFIG", request, fZMQin, ZMQ_SNDMORE);
  //alizmq_msg_send("CONFIG", "select=EMC*", fZMQin, ZMQ_SNDMORE);
  if (fVerbose) Printf("\nsending request CONFIG with request \"%s\"", request.c_str());
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

//_______________________________________________________________________________________
int zmqReceiver::InitZMQ()
{
  // Init or reinit ZMQ socket
  int rc = 0;
  rc += alizmq_socket_init(fZMQin,  fZMQcontext, fZMQconfigIn.c_str());

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

//______________________________________________________________________________
std::string zmqReceiver::PrintConfiguration()
{
  std::stringstream status;
  status << "Running receiver with configuration:" << std::endl;
  status << "\tVerbosity: " << fVerbose << std::endl;
  status << "\tSelection: \"" << fSelection << "\"" << std::endl;
  status << "\tResetMerger: " << fResetMerger << std::endl;
  status << "\tSleep time between requests: " << fPollInterval/1e3 << " s" << std::endl;
  status << "\tRequest timeout: " << fPollTimeout/1e3 << " s" << std::endl;
  status << "\tZMQ In Configuration: " << fZMQconfigIn << std::endl;

  return status.str();
}

////////////////////////////////////////////////////////////////////////////////
// Handle command line options
////////////////////////////////////////////////////////////////////////////////

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
    fVerbose = atoi(value);
  }
  else if (option.EqualTo("select"))
  {
    fSelection = value;
  }
  else if (option.EqualTo("resetMerger"))
  {
    fResetMerger = true;
  }
  else if (option.EqualTo("subsystem"))
  {
    fSubsystem = value;
  }
  else if (option.EqualTo("PollInterval") || option.EqualTo("sleep"))
  {
    fPollInterval = round(value.Atof()*1e3);
  }
  else if (option.EqualTo("PollTimeout") || option.EqualTo("timeout"))
  {
    fPollTimeout = round(value.Atof()*1e3);
  }
  else
  {
    return -1;
  }

  return 1; 
}

//______________________________________________________________________________
int zmqReceiver::ProcessOptionString(TString arguments)
{
  // Process passed options
  aliStringVec* options = AliOptionParser::TokenizeOptionString(arguments);
  int nOptions = 0;
  for (aliStringVec::iterator i=options->begin(); i!=options->end(); ++i)
  {
    if (ProcessOption(i->first,i->second) < 0)
    {
      // If an option is not found, then print the help
      nOptions = -1;
      break;
    }

    // Keep track of number succssfully parsed
    nOptions++;
  }

  delete options; //tidy up

  return nOptions; 
}
