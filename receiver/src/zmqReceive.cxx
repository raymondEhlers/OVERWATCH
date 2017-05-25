/**
 * @file zmqReceive.cxx
 * @brief Driver for zmqReceiver
 *
 * Main driver function for the zmqReceiver class, which requests and receives
 * data from the HLT mergers via ZMQ.
 *
 * @author: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
 * @date May 25, 2017
 */

#include "zmqReceiver.h"

#include <string>

#include <AliZMQhelpers.h>

int main(int argc, char** argv)
{
  std::string fUsage =
  "zmqReceive\n"
  "    Receive ROOT objects from the HLT via ZMQ.\n\n"
  "Options:\n"
  "    --in <address>: address for incoming ZMQ data. Format should be \"MODE>tcp://address:port\".\n"
  "              For example: \"REQ>tcp://localhost:1234\"\n"
  "    --verbose <level>: Control verbosity level. Disable with 0. Default: 1.\n"
  "    --resetMerger: Reset the merger after each request. Use with care! Default: false\n"
  "    --requestStreamers: Request ROOT streamers from the mergers. Default: true\n"
  "    --select <string>: Selection string to request data from the merger.\n"
  "              Defaults to \"\" (ie No special selection).\n"
  "    --sleep <seconds>: Time to sleep between each request in seconds. Default: 60.\n"
  "    --timeout <seconds>: Time to wait for a response to a request in seconds. Default: 10.\n"
  ;
  
  // Create receiver
  zmqReceiver receiver;

  // Process options from the terminal
  int nOptions = receiver.ProcessOptions(argc, argv);
  if (nOptions <= 0) 
  {
    Printf("%s", fUsage.c_str());
    return 1;
  }

  // Init ZMQ
  if (receiver.InitZMQ() < 0) {
    Printf("failed init");
    return 1;
  }

  // Run zmq receiver
  receiver.Run();

  // If we get to here, execution somehow ended or ctrl-c has been caught,
  // so we should cleanup ZMQ and exit.
  // Destroy ZMQ sockets
  receiver.Cleanup();

  return 0;
}

