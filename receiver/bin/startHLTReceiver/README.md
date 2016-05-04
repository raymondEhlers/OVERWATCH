# HLT Receiver Scripts

These scripts are used on a particular system to receive data from the HLT. If you are reading this file, then you almost assuredly **DO NOT** need these scripts.

This requires the `feature-hltdev` branch in AliRoot, as well as `autossh`. This code has not been written to be portable, since it is only used on one system for one purpose.

`runReceiver.sh` and `startReceivers.sh` should be symlinked to the OVERWATCH data directory so that they can be executed there.

The data flow is:

```
      ssh           ssh
     tunnel        tunnel          rsync
HLT -------> lbl5 --------> lbl3 --------> OVERWATCH data dir
```

These scripts are executed on `lbl3`.
