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
#include <iostream>

#include <AliZMQhelpers.h>

int main(int argc, char** argv)
{
  // Create receiver
  zmqReceiver receiver;

  // Process options from the terminal
  int nOptions = receiver.ProcessOptions(argc, argv);
  if (nOptions <= 0) 
  {
    std::cout << zmqReceiver::Usage();
    return 1;
  }

  // Init reciever
  if (receiver.Init() < 0) {
    std::cout << "Failed init";
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

