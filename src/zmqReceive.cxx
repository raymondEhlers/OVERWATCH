// Driver for zmqReceiver
//
// Author: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University

#include "zmqReceiver.h"

#include <string>

#include <AliZMQhelpers.h>

//#include <TString.h>

//_______________________________________________________________________________________
int main(int argc, char** argv)
{
  int mainReturnCode = 0;

  std::string fUsage = "Use the proper options";
  
  // Create receiver
  zmqReceiver receiver;

  // Process args
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

