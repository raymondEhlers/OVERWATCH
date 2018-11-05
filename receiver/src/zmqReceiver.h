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

#include <signal.h>

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
  int Init();
  int Run();
  void Cleanup();
  /* @} */

  // Helper functions
  int ProcessOptions(int argc, char * argv[]);
  int ProcessOptionString(TString arguments);

  /// Print usage information
  static std::string Usage() { return fgUsage; }

 protected:
  // Parsing
  int ProcessOption(TString option, TString value);
  // Status
  std::string PrintConfiguration();
  // Signal handler
  static void caughtSignal(int i);
  // Heartbeat
  void WriteHeartbeat();
  // Data management
  void ReceiveData();
  void ClearData();
  void WriteToFile();
  // ZMQ init
  int InitZMQ();
  // ZMQ request
  void SendRequest();

  // Configuration
  static const std::string fgUsage; //!<! Usage string
  // Receiver
  int fVerbose;             ///< Sets verbosity in printing
  int fRunNumber;           ///< Contains the run number
  bool fResetMerger;        ///< Request the merger to reset the data
  std::string fSubsystem;   ///< Contains the subsystem that this receiver should be interested in
  bool fFirstRequest;       ///< True when we are making the first request
  bool fRequestStreamers;   ///< True if the ROOT streamers schema should be requested from the merger
  std::string fHLTMode;     ///< Contains the HLT mode
  std::string fSelection;   ///< Selection option that should be requested to the merger
  std::string fDataPath;    ///< Path to the data stroage directory
  // ZMQ
  int fPollInterval;        ///< Time between each request for data in milliseconds
  int fPollTimeout;         ///< Time to wait for data after each request In milliseconds
  std::string fZMQconfigIn; ///< Contains the address for ZMQ

  // Received data
  std::vector <TObject *> fData; //!<! Contains received objects

  // Signal status
  static volatile sig_atomic_t fgSignalCaught; //!<! Status of whether a INT signal has been caught

  // ZMQ context and socket
  void* fZMQcontext;    //!<! The ZMQ context
  void* fZMQin;         //!<! The in socket - entry point for the received data.
};

#endif /* zmqReceiver.h */
