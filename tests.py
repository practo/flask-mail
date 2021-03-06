# -*- coding: utf-8 -*-

from __future__ import with_statement

import unittest
import mailbox

from email import encoders

from flask import Flask, g
from flaskext.mail import Mail, Message, BadHeaderError, Attachment

class TestCase(unittest.TestCase):

    TESTING = True
    DEFAULT_MAIL_SENDER = "support@mysite.com"

    def setUp(self):

        self.app = Flask(__name__)
        self.app.config.from_object(self)

        self.assertTrue(self.app.testing)

        self.mail = Mail(self.app)

        self.ctx = self.app.test_request_context()
        self.ctx.push()

    def tearDown(self):

        self.ctx.pop()


class TestMessage(TestCase):

    def test_initialize(self):

        msg = Message(subject="subject",
                      recipients=["to@example.com"])


        self.assertEqual(msg.sender, "support@mysite.com")
        self.assertEqual(msg.recipients, ["to@example.com"])

    def test_recipients_properly_initialized(self):

        msg = Message(subject="subject")
        self.assertEqual(msg.recipients, [])

        msg2 = Message(subject="subject")
        msg2.add_recipient("somebody@here.com")
        self.assertEqual(len(msg2.recipients), 1)

    def test_sendto_properly_set(self):
        msg = Message(subject="subject", recipients=["somebody@here.com"],
                       cc=["cc@example.com"], bcc=["bcc@example.com"])
        self.assertEqual(len(msg.send_to), 3)
        msg.add_recipient("cc@example.com")
        self.assertEqual(len(msg.send_to), 3)

    def test_add_recipient(self):

        msg = Message("testing")
        msg.add_recipient("to@example.com")

        self.assertEqual(msg.recipients, ["to@example.com"])


    def test_sender_as_tuple(self):

        msg = Message(subject="testing",
                      sender=("tester", "tester@example.com"))

    def test_reply_to(self):

        msg = Message(subject="testing",
                      recipients=["to@example.com"],
                      sender="spammer <spammer@example.com>",
                      reply_to="somebody <somebody@example.com>",
                      body="testing")

        response = msg.get_response()
        self.assertIn("Reply-To: somebody <somebody@example.com>", str(response))

    def test_send_without_sender(self):

        del self.app.config['DEFAULT_MAIL_SENDER']

        msg = Message(subject="testing",
                      recipients=["to@example.com"],
                      body="testing")

        self.assertRaises(AssertionError, self.mail.send, msg)

    def test_send_without_recipients(self):

        msg = Message(subject="testing",
                      recipients=[],
                      body="testing")

        self.assertRaises(AssertionError, self.mail.send, msg)

    def test_send_without_body(self):

        msg = Message(subject="testing",
                      recipients=["to@example.com"])

        self.assertRaises(AssertionError, self.mail.send, msg)

        msg.html = "<b>test</b>"

        self.mail.send(msg)

    def test_normal_send(self):
        """
        This will not actually send a message unless the mail server
        is set up. The error will be logged but test should still
        pass.
        """

        self.app.config['TESTING'] = False
        self.mail.init_app(self.app)

        with self.mail.record_messages() as outbox:

            msg = Message(subject="testing",
                          recipients=["to@example.com"],
                          body="testing")

            self.mail.send(msg)

            self.assertEqual(len(outbox), 1)

        self.app.config['TESTING'] = True

    def test_bcc(self):

        msg = Message(subject="testing",
                      recipients=["to@example.com"],
                      body="testing",
                      bcc=["tosomeoneelse@example.com"])

        response = msg.get_response()
        self.assertIn("Bcc: tosomeoneelse@example.com", str(response))

    def test_cc(self):

        msg = Message(subject="testing",
                      recipients=["to@example.com"],
                      body="testing",
                      cc=["tosomeoneelse@example.com"])

        response = msg.get_response()
        self.assertIn("Cc: tosomeoneelse@example.com", str(response))

    def test_attach(self):

        msg = Message(subject="testing",
                      recipients=["to@example.com"],
                      body="testing")

        msg.attach(data="this is a test",
                   content_type="text/plain")


        a = msg.attachments[0]

        self.assertIsNone(a.filename)
        self.assertEqual(a.disposition, 'attachment')
        self.assertEqual(a.content_type, "text/plain")
        self.assertEqual(a.data, "this is a test")


    def test_bad_header_subject(self):

        msg = Message(subject="testing\n\r",
                      sender="from@example.com",
                      body="testing",
                      recipients=["to@example.com"])

        self.assertRaises(BadHeaderError, self.mail.send, msg)

    def test_bad_header_sender(self):

        msg = Message(subject="testing",
                      sender="from@example.com\n\r",
                      recipients=["to@example.com"],
                      body="testing")

        self.assertRaises(BadHeaderError, self.mail.send, msg)

    def test_bad_header_reply_to(self):

        msg = Message(subject="testing",
                      sender="from@example.com",
                      reply_to="evil@example.com\n\r",
                      recipients=["to@example.com"],
                      body="testing")

        self.assertRaises(BadHeaderError, self.mail.send, msg)

    def test_bad_header_recipient(self):

        msg = Message(subject="testing",
                      sender="from@example.com",
                      recipients=[
                          "to@example.com",
                          "to\r\n@example.com"],
                      body="testing")

        self.assertRaises(BadHeaderError, self.mail.send, msg)


class TestMail(TestCase):

    def test_send(self):

        with self.mail.record_messages() as outbox:
            msg = Message(subject="testing",
                          recipients=["tester@example.com"],
                          body="test")

            self.mail.send(msg)

            self.assertEqual(len(outbox), 1)

    def test_send_message(self):

        with self.mail.record_messages() as outbox:
            self.mail.send_message(subject="testing",
                                   recipients=["tester@example.com"],
                                   body="test")

            self.assertEqual(len(outbox), 1)

            msg = outbox[0]

            self.assertEqual(msg.subject, "testing")
            self.assertEqual(msg.recipients, ["tester@example.com"])
            self.assertEqual(msg.body, "test")


class TestConnection(TestCase):

    def test_send_message(self):

        with self.mail.record_messages() as outbox:
            with self.mail.connect() as conn:
                conn.send_message(subject="testing",
                                  recipients=["to@example.com"],
                                  body="testing")

            self.assertEqual(len(outbox), 1)

    def test_send_single(self):

        with self.mail.record_messages() as outbox:
            with self.mail.connect() as conn:
                msg = Message(subject="testing",
                              recipients=["to@example.com"],
                              body="testing")

                conn.send(msg)

            self.assertEqual(len(outbox), 1)

    def test_send_many(self):

        messages = []

        with self.mail.record_messages() as outbox:
            with self.mail.connect() as conn:
                for i in xrange(100):
                    msg = Message(subject="testing",
                                  recipients=["to@example.com"],
                                  body="testing")

                    conn.send(msg)

            self.assertEqual(len(outbox), 100)

    def test_max_emails(self):

        messages = []

        with self.mail.record_messages() as outbox:
            with self.mail.connect(max_emails=10) as conn:
                for i in xrange(100):
                    msg = Message(subject="testing",
                                  recipients=["to@example.com"],
                                  body="testing")

                    conn.send(msg)

                    print conn.num_emails
                    if i % 10 == 0:
                        self.assertEqual(conn.num_emails, 1)

            self.assertEqual(len(outbox), 100)

