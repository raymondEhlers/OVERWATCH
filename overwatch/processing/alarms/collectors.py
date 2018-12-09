from slackclient import SlackClient
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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
    def __init__(self, alarmsParameters=None):
        if alarmsParameters is not None:
            smtpSettings = alarmsParameters["emailDelivery"]["smtpSettings"]
            host = smtpSettings["address"]
            port = smtpSettings["port"]
            password = smtpSettings["password"]
            self.user_name = smtpSettings["userName"]
            self.s = smtplib.SMTP(host=host, port=port)
            self._login(password)

    def _login(self, password):
        self.s.starttls()
        self.s.login(user=self.user_name, password=password)

def printCollector(alarm):
    print(alarm)

class MailSender:
    """Manages sending emails.

    Args:
        addresses (list): List of email addresses
    Attributes:
        recipients (list): List of email addresses
    """
    def __init__(self, addresses):
        self.recipients = addresses

    def __call__(self, alarm):
        self.sendMail(alarm)

    def sendMail(self, payload):
        """ Sends message to specified earlier recipients.

        Args:
            payload (str): Message to send
        Return:
            None.
        """
        if self.recipients is not None:
            mail = Mail()
            msg = MIMEMultipart()
            msg['From'] = mail.user_name
            msg['To'] = ", ".join(self.recipients)
            msg['Subject'] = 'Overwatch Alarm'
            msg.attach(MIMEText(payload, 'plain'))
            mail.s.sendmail(mail.user_name, self.recipients, msg.as_string())

class SlackNotification(Singleton):
    """Manages sending notifications on Slack.

    Args:
        alarmsParameters (dict): Parameters read from configuration files
    Attributes:
        sc (SlackClient):
        channel (str): Channel name
    """
    def __init__(self, alarmsParameters=None):
        if alarmsParameters is not None:
            self.sc = SlackClient(alarmsParameters["apiToken"])
            self.channel = alarmsParameters["slackChannel"]

    def __call__(self, alarm):
        self.sendMessage(alarm)
        
    def sendMessage(self, payload):
        """ Sends message to specified earlier channel.

        Args:
            payload (str): Message to send
        Return:
            None.
        """
        self.sc.api_call('chat.postMessage', channel=self.channel,
                text=payload, username='Alarms OVERWATCH',
                icon_emoji=':robot_face:')

class AlarmCollector():
    """
    Class that collects generated alarms. Collected alarms are grouped and announced to
    specified receivers.

    Attributes:
        alarms (list): List of alarms. Each element is a pair [Alarm, str]
    """
    def __init__(self):
        self.alarms = []

    def addAlarm(self, alarm):
        """ It adds alarm to the existing list of alarms

        Args:
            alarm ([Alarm, str]): A pair - Alarm object and message
        Return:
            None.
        """
        self.alarms.append(alarm)

    def announceAlarm(self):
        """ It sends collected and grouped messages to receivers.
        Then resets list of alarms. It can be called anywhere:
        after processing each histogram, after each RUN, ect.

        Args:
            None.
        Return:
            None.
        """
        receivers = self._groupAlarms()
        for receiver in receivers:
            msg = '\n'.join(receivers[receiver])
            receiver(msg)
        self._resetCollector()

    def _resetCollector(self):
        self.alarms = []

    def _groupAlarms(self):
        receivers = {}
        for alarmMsg in self.alarms:
            alarm = alarmMsg[0]
            msg = alarmMsg[1]
            for receiver in alarm.receivers:
                if receiver not in receivers:
                    receivers[receiver] = []
                receivers[receiver].append(msg)
        return receivers


alarmCollector = AlarmCollector()
