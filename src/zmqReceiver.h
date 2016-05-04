#ifndef ZMQRECEIVER_H /* zmqReceiver.h */
#define ZMQRECEIVER_H
//
// Adapted from ZMQROOTmerger.cxx in HLT/BASE/utils in AliRoot
//
// Author: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University

#include <zmq.h>

#include <TString.h>

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
  enum runNumberTypes { kUnknownRunNumber = 12345678 };

  // Methods
  // Parsing
  int ProcessOption(TString option, TString value);
  // Data management
  void ReceiveData();
  void ClearData();
  void WriteToFile();
  // ZMQ request
  void SendRequest();

  // Configuration
  // Receiver
  int fVerbose; // Sets verbosity in printing
  int fRunNumber; // Contains the run number
  std::string fSubsystem; // Contains the subsystem that this receiver should be interested in
  std::string fHLTMode; // Contains the HLT mode
  std::string fSelection; // Selection option that should be requested to the merger
  // ZMQ
  int fPollInterval; // Time between each request for data in milliseconds
  int fPollTimeout; // Time to wait for data after each request In milliseconds
  std::string fZMQconfigIn; // Contains the address for ZMQ

  // Received data
  std::vector <TObject *> fData; // Contains received objects

  // ZMQ context and socket
  void* fZMQcontext;    //ze zmq context
  void* fZMQin;        //the in socket - entry point for the received data.
};

#endif /* zmqReceiver.h */
