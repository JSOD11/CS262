from distutils.log import info
import logging
import signal
import socket
import curses
import threading
import time
import grpc
from chat_pb2 import ServerMessage

from menu import menu

from chat_pb2_grpc import ChatServiceStub

import chat_pb2

class Client:

    PORT = 5050
    HEADER = 64
    FORMAT = "utf-8"
    DISCONNECT_MESSAGE = "!DISCONNECT"
    SERVER_NAME = socket.gethostname() # gets name representing computer on the network
    SERVER = socket.gethostbyname(SERVER_NAME) # gets host IPv4 address
    ADDR = (SERVER, PORT)
    SESSION_INFO = {"username": "", "background_listen": True}
    CLIENT_LOCK = threading.Lock()
    RECEIVE_EVENT = threading.Event()
    VERSION = "1"

    def login(self, username, stub: ChatServiceStub):
        received_info = stub.LoginClient(chat_pb2.ClientMessage(operation=chat_pb2.LOGIN, info=username))
        return self.login_processing(username, received_info)

    def create_account(self, username, stub: ChatServiceStub):
        received_info = stub.CreateAccountClient(chat_pb2.ClientMessage(operation=chat_pb2.CREATE_ACCOUNT, info=username))
        return self.create_account_processing(username, received_info)

    def delete_account(self, username, stub: ChatServiceStub):
        received_info = stub.DeleteAccountClient(chat_pb2.ClientMessage(operation=chat_pb2.DELETE_ACCOUNT, info=username))
        return self.delete_account_processing(username, received_info)
    
    def logout(self, username, stub: ChatServiceStub):
        received_info = stub.LogoutClient(chat_pb2.ClientMessage(operation=chat_pb2.LOGOUT, info=username))
        return self.logout_processing(username, received_info)

    def list_accounts(self, stub: ChatServiceStub):
        received_info = stub.ListAccountClient(chat_pb2.ClientMessage(operation=chat_pb2.LIST_ACCOUNTS, info=""))
        return self.list_account_processing(received_info)

    def send_message(self, sender, receiver, msg, stub: ChatServiceStub):
        total_info = sender + "\n" + receiver + "\n" + msg
        received_info = stub.SendMessageClient(chat_pb2.ClientMessage(operation=chat_pb2.SEND_MESSAGE, info=total_info))
        return self.send_message_processing(received_info)
    
    def view_msgs(self, username, stub: ChatServiceStub):
        received_info = stub.ViewMessageClient(chat_pb2.ClientMessage(operation=chat_pb2.VIEW_UNDELIVERED_MESSAGES, info=username))
        return self.view_message_processing(received_info)

    def login_processing(self, username, received_info: ServerMessage):
        status = received_info.operation
        if status == chat_pb2.SUCCESS:
            self.SESSION_INFO["username"] = username
            return 0
        elif status == chat_pb2.ACCOUNT_DOES_NOT_EXIST:
            print("\nThe username you entered does not exist on the server. Please try again or input EXIT to exit.\n")
            return 1
        else:
            return None

    def create_account_processing(self, username, received_info: ServerMessage):
        status = received_info.operation
        if status == chat_pb2.SUCCESS:
            self.SESSION_INFO["username"] = username
            return 0
        print("\nThe username you entered already exists on the server. Please try again or input EXIT to exit.\n")
        return 1

    def delete_account_processing(self, username, received_info: ServerMessage):
        status = received_info.operation
        if status == chat_pb2.SUCCESS:
            self.SESSION_INFO["username"] = ""
            return 0
        print("Deletion failure")
        return 1

    def logout_processing(self, username, received_info: ServerMessage):
        status = received_info.operation
        if status == chat_pb2.SUCCESS:
            self.SESSION_INFO["username"] = ""
            return 0
        print("Logout failure")
        return 1

    def list_account_processing(self, received_info: ServerMessage):
        status = received_info.operation
        if status == chat_pb2.SUCCESS:
            return received_info
        print("Account information does not exist")
        return 1

    def send_message_processing(self, received_info: ServerMessage):
        try:
            status = received_info.operation
            if status == chat_pb2.SUCCESS:
                return 0
            print("Message send failure, receiving account does not exist")
            return 1
        except:
            return 1

    def view_message_processing(self, received_info: ServerMessage):
        if received_info.operation == chat_pb2.FAILURE:
            print("\n" + self.SESSION_INFO["username"] + "'s account does not have any unread messages.")
            return 1
        messages = received_info.info.split("\n")
        print("\nList of " + self.SESSION_INFO["username"] + "'s messages:\n")
        for j, message in enumerate(messages):
            print(str(j + 1) + ". " + str(message))
        return 0

    def quit_messenger(self, stub: ChatServiceStub):
        self.RECEIVE_EVENT.clear()
        return


    def receive_incoming_messages(self, username, stub: ChatServiceStub):
      try:
        receive_info = stub.CheckIncomingMessagesClient(chat_pb2.ClientMessage(operation=chat_pb2.RECEIVE_CURRENT_MESSAGE, info=username))
        if receive_info.operation == chat_pb2.MESSAGES_EXIST:
            for message in receive_info.info.split("\n"):
                print("\r" + message)
      except KeyboardInterrupt:
        return -1
      except Exception as e:
        logging.exception(e)

    def poll_incoming_messages(self, event, stub: ChatServiceStub):
      while event.is_set():
        if self.SESSION_INFO["username"] == "":
            continue
        try:
          with self.CLIENT_LOCK:
            if self.SESSION_INFO["background_listen"]:
              message = self.receive_incoming_messages(self.SESSION_INFO["username"], stub)
              if message:
                if message == -1:
                  break
                print("\r[INCOMING MESSAGE]{}".format(message["info"]))
          time.sleep(1)
        except Exception as e:
          logging.exception(e)
          break

    def get_login_input(self, stub: ChatServiceStub):
      received_list = self.list_accounts(stub)
      if received_list != 1:
        accounts = received_list.info.split("\n")
        message = "\nChoose an account:\n\n"
        username = curses.wrapper(menu, accounts, message)
        return self.login(username, stub)
      else:
        print("\nThere are currently no accounts on the server.\n")
        input("Press enter to return to the main menu.\n\n")
        return 1

    def background_listener(self, stub: ChatServiceStub):
      self.RECEIVE_EVENT.set()
      background_thread = threading.Thread(target=self.poll_incoming_messages, args=(self.RECEIVE_EVENT,stub))
      background_thread.start()