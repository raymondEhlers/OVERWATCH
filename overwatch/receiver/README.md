# DQM Receiver package details

This package serves as a compliment to the ZMQ receiver built in `c++` to receive files from the HLT. It
provides a route for files to be shared from ALICE Data Quality Monitoring (DQM) to Overwatch.

In particular, it provides a REST interface for sending files to Overwatch, which are then processed similarly
to files from the ZMQ receiver. Note that in the case of the ZMQ receiver, it makes explicit requests via ZMQ
to the HLT infrastructure, while in the case of the DQM receiver, the DQM system must explicitly send the
files via the REST API. In summary, the ZMQ receiver pulls, while data is pushed to DQM receiver.

## Receiver API

The receiver can receive files from the DQM system, as well list the files that it received.

### Send and list files

- **URL**

    `/rest/api/files`

- **Method**

    `GET` or `POST` requests are accepted.

- **URL Parameters**

    None.

- **Header Parameters**

    **Required:**

    - `runNumber=[int]`. The run number.
    - `timeStamp=[int]`. The time stamp in unix time.
    - `amoreAgent=[str]`. The name of the AMORE agent of the file being sent.
    - `dataStatus=[int]`. The status of the data taking. `1` for start of a set of data, `2` for the end of data, and 0 (or not set) for somewhere in the middle.
    - `token=[str]`. Token to identify the sender.

- **Data Parameters**

    The file should be attached as a form element named "file". This will be sent as part of a
    `form/multi-part` request.

- **Success Response**

    GET Request:

    - **Code:** 200 <br />
      **Content:** `{ "files" : ["exampleFilename1.root", "exampleFilename2.root", ...] }`

    POST Request:

    - **Code:** 200 <br />
      **Content:**
      ```
      {
          "status" : 200,
          "filename" : "aTestFile.root",
          "message": "Successfully received file and extracted information",
          "received" : {
            "histName1": "Obj name: histName1, Obj IsA() Name: TH1F",
            "histName2": "Obj name: histName2, Obj IsA() Name: TH1F"
          }
      }
      ```

- **Error Response**

    The details of the response are noted above. It will return a status of 200 if successful, and 400 if not. The message will explain a bit further about what happened.

    - Token errors: <br />
      **Code:** 400 <br />
      **Content:**
      ```
      {
          "status" : 400,
          "message": "Received token, but it is invalid!",
          "received" : null
      }
      ```

    OR

    - Payload errors: <br />
      **Code:** 400 <br />
      **Content:**
      ```
      {
          "status" : 400,
          "message": "Successfully received the file, but the file is not valid! Perhaps it was corrupted?",
          "received" : null
      }
      ```

- **Example Call**

    Call via curl:

    ```
    $ curl -F file=@aTestFile.root \
        -H "token: abcd" \
        -H "runNumber: 123" \
        -H "timeStamp: 234" \
        -H "amoreAgent: testagent" \
        -H "dataStatus: 1" \
        /rest/api/files
    ```

### Download individual files

- **URL**

    `/rest/api/files`

- **Method**

    `GET` requests are accepted.

- **URL Parameters**

    **Required:**

    - `filename=[str]`. The name of the file to retrieve.

- **Header Parameters**

    **Required:**

    - `token=[str]`. Token to identify the sender.

- **Success Response**

    - `application/octet-stream` of the actual file.

- **Error Response**

    - Token errors: <br />
      **Code:** 400 <br />
      **Content:**
      ```
      {
          "status" : 400,
          "message": "Received token, but it is invalid!",
          "received" : null
      }
      ```

- **Example Call**

    Call via curl, storing the result in `testFile.root`:

    ```
    $ curl -H "token: abcd" /rest/api/files/aTestFile.root > testFile.root
    ```

#### API documentation formatting note

The format of the documentation is based on [this template](https://bocoup.com/blog/documenting-your-api).

## Request Token

The receiver checks for a special token in the request header to identify it as a known request. This
basically serves as a rudimentary identification function. However, it doesn't need to be sophisticated for
our purposes. As of August 2018, there is only one token, but this could be easily expanded to provide unique
tokens for each user.

