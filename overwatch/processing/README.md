## HLT Modes

There are a number of valid HLT modes. Their meaning is as follows:

| HLT Mode | Explanation         | Action    |
| -------- | ------------------- | --------- |
| A        | HLT wasn't included in data taking | We recieved no data, so nothing to be done (we won't see this data ever). |
| B        | HLT with no compression | Process data as normal (we don't see the difference between compression included or not). |
| C        | HLT with compression | Process data as normal (we don't see the difference between compression included or not). |
| E        | HLT data replay      | Replay of an old run for testing. This data is saved by the receiver, moved to the "ReplayData" directory, and not processed. |
| U        | HLT mode unknown     | The HLT mode was lost somewhere. Process data as normal. The mode is available in the logbook if needed. |

## Received file mode

The HLT receiver can operate in two possible file modes:

TOOD: Fill in!
