

def printCollector(alarm):
    print(alarm)


class MailSender:
    def __init__(self, address):
        self.address = address

    def __call__(self, alarm):
        self.sendMail(alarm)

    def sendMail(self, payload):
        printCollector("MAIL TO:{} FROM:alarm@overwatch PAYLOAD:'{}'".format(self.address, payload))


def httpCollector(alarm):
    printCollector("HTTP: <alarm>{}</alarm>".format(alarm))


workerMail = MailSender("worker@cern")
