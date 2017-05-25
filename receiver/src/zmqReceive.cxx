// Driver for zmqReceiver
//
// Author: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University

#include "zmqReceiver.h"

#include <string>

#include <AliZMQhelpers.h>
#include <AliOptionParser.h>

//#include <TString.h>

//_______________________________________________________________________________________
int main(int argc, char** argv)
{
  int mainReturnCode = 0;

  std::string fUsage =
  "zmqReceive\n"
  "    Receive ROOT objects from the HLT via ZMQ.\n\n"
  "Options:\n"
  "    --in <address>: address for incoming ZMQ data. Format should be \"MODE>tcp://address:port\".\n"
  "              For example: \"REQ>tcp://localhost:1234\"\n"
  "    --verbose <level>: Control verbosity level. Disable with 0. Default: 1.\n"
  "    --select <string>: Selection string to request data from the merger.\n"
  "              Defaults to \"\" (ie No special selection).\n"
  "    --sleep <seconds>: Time to sleep between each request in seconds. Default: 60.\n"
  "    --timeout <seconds>: Time to wait for a response to a request in seconds. Default: 10.\n"
  ;
  
  // Create receiver
  zmqReceiver receiver;

  // Process args using the HLT infrastructure for simplicity
  int nOptions = receiver.ProcessOptionString(AliOptionParser::GetFullArgString(argc,argv));
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
  // TODO: Catch ctrl-c!
  receiver.Run();

  // destroy ZMQ sockets
  receiver.Cleanup();

  return mainReturnCode;
}

