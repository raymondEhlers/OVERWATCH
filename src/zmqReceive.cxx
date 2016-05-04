// Driver for zmqReceiver
//
// Author: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University

#include "zmqReceiver.h"

#include <AliZMQhelpers.h>

#include <TString.h>

//_______________________________________________________________________________________
int main(int argc, char** argv)
{
  int mainReturnCode = 0;

  TString fUsage = "Use the proper options";
  
  // Create receiver
  zmqReceiver receiver;

  // Process args
  int nOptions = receiver.ProcessOptionString(AliOptionParser::GetFullArgString(argc,argv));
  if (nOptions <= 0) 
  {
    Printf("%s", fUsage.Data());
    return 1;
  }

  //init stuff
  if (receiver.InitZMQ() < 0) {
    Printf("failed init");
    return 1;
  }

  // Run zmq receiver
  receiver.Run();

  // destroy ZMQ sockets
  receiver.Cleanup();

  return mainReturnCode;
}

