#ifndef ZMQRECEIVER_H /* zmqReceiver.h */
#define ZMQRECEIVER_H
/**
 * @class zmqReceiver
 * @brief ZMQ Receiver for files sent from the HLT
 *
 * This class sends requests and receivers content viz ZeroMQ from
 * the HLT mergers. The code is adapted from ZMQROOTmerger.cxx in
 * $ALICE_ROOT/HLT/BASE/utils.
 *
 * @author: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
 * @date May 25, 2017
 */

#include <zmq.h>

#include <TString.h>

class zmqReceiver 
{
 public:
  zmqReceiver();
  virtual ~zmqReceiver() {}

  /* @{
   * @name Main usage functions
   */
  int InitZMQ();
  int Run();
  void Cleanup();
  /* @} */

  // Helper functions
  int ProcessOptionString(TString arguments);

 protected:
  // Parsing
  int ProcessOption(TString option, TString value);
  // Status
  std::string PrintConfiguration();
  // Data management
  void ReceiveData();
  void ClearData();
  void WriteToFile();
  // ZMQ request
  void SendRequest();

  // Configuration
  // Receiver
  int fVerbose;             ///< Sets verbosity in printing
  int fRunNumber;           ///< Contains the run number
  bool fResetMerger;        ///< Request the merger to reset the data
  std::string fSubsystem;   ///< Contains the subsystem that this receiver should be interested in
  bool fFirstRequest;       ///< True when we are making the first request
  bool fRequestStreamers;   ///< True if the ROOT streamers schema should be requested from the merger
  std::string fHLTMode;     ///< Contains the HLT mode
  std::string fSelection;   ///< Selection option that should be requested to the merger
  // ZMQ
  int fPollInterval;        ///< Time between each request for data in milliseconds
  int fPollTimeout;         ///< Time to wait for data after each request In milliseconds
  std::string fZMQconfigIn; ///< Contains the address for ZMQ

  // Received data
  std::vector <TObject *> fData; //!<! Contains received objects

  // ZMQ context and socket
  void* fZMQcontext;    //!<! The ZMQ context
  void* fZMQin;         //!<! The in socket - entry point for the received data.
};

#endif /* zmqReceiver.h */
