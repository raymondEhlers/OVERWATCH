// Driver for zmqReceiver
//
// Author: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University

#include "zmqReceiver.h"

#include <TString.h>
#include <TMessage.h>

TString GetFullArgString(int argc, char** argv);

//_______________________________________________________________________________________
int main(int argc, char** argv)
{
  int mainReturnCode = 0;

  zmqReceiver receiver;

  //process args
  TString argString = GetFullArgString(argc,argv);
  receiver.ProcessOptionString(argString);

  //globally enable schema evolution for serializing ROOT objects
  TMessage::EnableSchemaEvolutionForAll(kTRUE);

  // The context
  receiver.setZMQContext(zmq_ctx_new());

  //init stuff
  if (receiver.InitZMQ() < 0) {
    Printf("failed init");
    return 1;
  }

  // Run zmq receiver
  receiver.Run();

  // destroy ZMQ sockets
  receiver.cleanup();

  return mainReturnCode;
}

//_______________________________________________________________________________________
TString GetFullArgString(int argc, char** argv)
{
  TString argString;
  TString argument="";
  if (argc>0) {
    for (int i=1; i<argc; i++) {
      argument=argv[i];
      if (argument.IsNull()) continue;
      if (!argString.IsNull()) argString+=" ";
      argString+=argument;
    }  
  }
  return argString;
}

