from dbconnector import set_gen_state, get_gen_state, set_initial_db_state, set_time_spent
from configuration import get_config, get_white_list, get_pin
from send_mail import send_mail
import datetime
import email
import imaplib
import logging
import os.path
import re
import socket
import time
import RPi.GPIO as GPIO

receiver_email = get_config('email')
receiver_password = get_config('password')
sleep_time = int(get_config('sleep_time'))
dir_path = os.path.dirname(os.path.realpath(__file__))
file_logging_path = os.path.join(dir_path, 'generator.txt')
logging.basicConfig(filename=file_logging_path,level=logging.INFO)
down_message = 'Generator is going down'
up_message = 'Generator is going up'
debug_message = 'Debugging message'
pin = int(get_pin())


def generator_cmd(cmd):
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)
    if cmd == 'on':
        GPIO.output(pin, False)
    elif cmd == 'off':
        GPIO.output(pin, True)


def delete_messages():
    msrvr.select('Inbox')
    typ, data = msrvr.search(None, 'ALL')
    for num in data[0].split():
       msrvr.store(num, '+FLAGS', '\\Deleted')
    msrvr.expunge()


def get_machine_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def get_key_command(cnt):
    count, data = msrvr.fetch(cnt[0], '(UID BODY[TEXT])')
    for i in cnt:
        typ, msg_data = msrvr.fetch(str(i), '(RFC822)')
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_string(response_part[1])
    body = get_body_word(data[0][1])
    subject = msg['subject'].lower()
    return subject, body


def get_sender():
    from_data = msrvr.fetch(cnt[0], '(BODY[HEADER.FIELDS (SUBJECT FROM)])')
    header_data = from_data[1][0][1]
    return ''.join(re.findall(r'<(.+?)>', header_data))


def get_body_word(body):
    cut_word = re.findall(r'^.*$', body, re.MULTILINE)[3][:-1].lower()
    return cut_word


def get_current_time():
    ts = time.time()
    time_stamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    return time_stamp


def is_in_white_list(mail_sender):
    if mail_sender in get_white_list():
        return True
    else:
        return False


if __name__ == '__main__':
    ip_address = get_machine_ip()
    startup_msg = '{} {}'.format('Machine runs on', ip_address)
    print(startup_msg)
    logging.info(startup_msg)
    send_mail(send_to='zagalsky@gmail.com', text=startup_msg)
    set_initial_db_state()
    start_time = None
    end_time = None
    i = 1
    while i == 1:
        try:
            msrvr = imaplib.IMAP4_SSL('imap.gmail.com', 993)
            login_stat, login_message = msrvr.login(receiver_email, receiver_password)
            if login_stat == 'OK':
                # logging.info(login_message)
                stat, cnt = msrvr.select('Inbox')
                key_command = get_key_command(cnt)
                from_address = get_sender()
                if is_in_white_list(from_address):
                    current_state = str(get_gen_state())
                    print("{} {} {}".format(get_current_time(), from_address, "is in the white list"))
                    logging.info("{} {} {}".format(get_current_time(), from_address, "is in the white list"))
                    if 'debug' in key_command:
                        print(debug_message)
                        logging.info("{} {}". format(get_current_time(), debug_message))
                        send_mail(send_to=from_address, text=debug_message)
                    elif 'off' in key_command:
                        if current_state is not 'False':
                            generator_cmd(cmd='off')
                            set_gen_state(state=False, time_stamp=get_current_time())
                            print(down_message)
                            logging.info("{} {}". format(get_current_time(), down_message))
                            send_mail(send_to=from_address, text=down_message)
                            end_time = datetime.datetime.now()
                            # Add 2 minutes (???) compensation for going down
                            time_spent = (end_time - start_time).total_seconds()
                            set_time_spent(time_spent)
                        else:
                            print('The generator is already off')
                            logging.info('The generator is already off')
                    elif 'on' in key_command:
                        if current_state is not 'True':
                            generator_cmd(cmd='on')
                            set_gen_state(True, time_stamp=get_current_time())
                            print(up_message)
                            logging.info("{} {}". format(get_current_time(), up_message))
                            send_mail(send_to=from_address, text=up_message)
                            start_time = datetime.datetime.now()
                        else:
                            print('The generator is already on')
                            logging.info('The generator is already on')
                    elif 'log' in key_command:
                        log_message = '{} {}'.format('sending logs to', from_address)
                        print(log_message)
                        logging.info("{} {}". format(get_current_time(), log_message))
                        send_mail(send_to=from_address, text=log_message, file=file_logging_path)
                    else:
                        log_message = '{} {}'.format(''.join(key_command), 'is an unknown command')
                        print(log_message)
                        logging.info("{} {}".format(get_current_time(), log_message))
                        send_mail(send_to=from_address, text=log_message)
                else:
                    print("{} {}".format(from_address,"is not in the white list"))
                    logging.info("{} {}".format(from_address,"is not in the white list"))
                delete_messages()
                time.sleep(sleep_time)
            else:
                print("{} {}".format("Connection failed due to", login_message))
        except:
            print("{} {}".format(get_current_time(), "No mails"))
            logging.info("{} {}".format(get_current_time(), "No mails"))
            time.sleep(sleep_time)
    # msrvr.close()
    # msrvr.logout()
