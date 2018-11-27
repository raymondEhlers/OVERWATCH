from slackclient import SlackClient
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# from overwatch.base import config
# (alarmsParameters, filesRead) = config.readConfig(config.configurationType.alarms)
import yaml

with open("config.yaml", 'r') as ymlfile:
    alarmsParameters = yaml.load(ymlfile)

# works in Python 2 & 3
class _Singleton(type):
    """ A metaclass that creates a Singleton base class when called. """
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Singleton(_Singleton('SingletonMeta', (object,), {})):
    # https://stackoverflow.com/questions/6760685/creating-a-singleton-in-python
    pass


class Mail(Singleton):
    def __init__(self):
        smtpSettings = alarmsParameters["email_delivery"]["smtp_settings"]
        host = smtpSettings["address"]
        port = smtpSettings["port"]
        password = smtpSettings["password"]
        self.user_name = smtpSettings["user_name"]
        self.s = smtplib.SMTP(host=host, port=port)
        self._login(password)

    def _login(self, password):
        self.s.starttls()
        self.s.login(user=self.user_name, password=password)


def printCollector(alarm):
    print(alarm)


class MailSender:
    def __init__(self, address):
        self.address = address
        self.mail = Mail()

    def __call__(self, alarm):
        self.sendMail(alarm)

    def sendMail(self, payload):
        msg = MIMEMultipart()
        msg['From'] = self.mail.user_name
        msg['To'] = self.address
        msg['Subject'] = 'Test Alarm'
        msg.attach(MIMEText(payload, 'plain'))
        printCollector("MAIL TO:{} FROM:alarm@overwatch PAYLOAD:'{}'".format(self.address, payload))
        self.mail.s.sendmail(self.mail.user_name, self.address, msg.as_string())
        
        
class SlackNotification(Singleton):
    def __init__(self):
        self.sc = SlackClient(alarmsParameters["apiToken"])
        self.channel = alarmsParameters["slackChannel"]

    def __call__(self, alarm):
        self.sendMessage(alarm)
        
    def sendMessage(self, payload):
        self.sc.api_call('chat.postMessage', channel=self.channel,
                text=payload, username='Alarms OVERWATCH',
                icon_emoji=':robot_face:')


def httpCollector(alarm):
    printCollector("HTTP: <alarm>{}</alarm>".format(alarm))


workerMail = MailSender("test@mail")
workerSlack = SlackNotification()
