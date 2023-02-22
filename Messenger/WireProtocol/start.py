import curses
import fnmatch
import sys
from server import WireServer
from operations import Operations
from menu import menu

from client import WireClient

def load_user_menu(this_client):
  """
  Displays the user menu and allows the user to select an action.

  Args:
  - this_client (object): The client object for the current user.

  Returns: None
  """
  actions = ["Send messages", "View my messages", "Logout", "Delete account"]
  message = "\n" + this_client.SESSION_INFO["username"] + "'s Account\n\n"
  user_choice = wrap_menu(menu, actions, message)

  if user_choice == "Send messages": # option 1 — send messages

    decoded_data = this_client.list_accounts()
    accounts = decoded_data["info"].split("\n")
    accounts.remove(this_client.SESSION_INFO["username"]) # users cannot send messages to themselves

    if len(accounts) == 0:
      print("\nThere are currently no other users on the server.\n")
      input("Press enter to return to the main menu.\n\n")

    else:
      message = "\nWho would you like to send messages to?\n\n"

      receiver = wrap_menu(menu, accounts, message)

      print("\nInput a message and press enter to share with " + receiver + " or EXIT to end the chat.\n")
      while True: # loop allows users to send messages until done
        message = wrap_input("")
        processed_message = "<NEW MESSAGE FROM " + this_client.SESSION_INFO["username"] + "> " + message
        if message == "EXIT":
          print(f"\n[ENDING CHAT] Ending chat with {receiver}\n")
          break
        this_client.send_message(this_client.SESSION_INFO["username"], receiver, processed_message)

    load_user_menu(this_client) # return to user menu afterwards
    return

  elif user_choice == "View my messages": # option 2 — view my messages
    this_client.view_msgs(this_client.SESSION_INFO["username"])
    wrap_input("\nPress enter to return to the main menu.\n\n")
    load_user_menu(this_client)

  elif user_choice == "Logout": # option 3 — logout
    this_client.logout(this_client.SESSION_INFO["username"])
    start(this_client)
  
  elif user_choice == "Delete account": # option 4 — delete my account
    actions = ["Go back", "Delete forever"]
    message = "\nAre you sure you would like to delete this account? Any unread messages will be permanently lost.\n\n"
    choice = wrap_menu(menu, actions, message)

    if choice == "Delete forever":
      this_client.delete_account(this_client.SESSION_INFO["username"])
      return start(this_client)
    else:
      load_user_menu(this_client)

def start(this_client):
  """
  Displays the start menu and allows the user to select an action from
    {login, create account, list accounts, quit messenger}.

  Args:
  - this_client (object): The client object for the current user.

  Returns: None
  """
  actions = ["Login", "Create account", "List accounts", "Quit Messenger"]
  message = "\nWelcome to Messenger! What would you like to do?\n\n"
  try:
    name = wrap_menu(menu, actions, message)
  except KeyboardInterrupt:
    return this_client.quit_messenger()

  if name == "Quit Messenger" or name == 0: # option 4 — quit messenger
    return this_client.quit_messenger()

  elif name == "Create account": # option 2 — create account
    print("\nWelcome to messenger! Please input a username to join or EXIT to exit.\n")
    status = 1
    while status == 1:
      account_name = wrap_input("Username: ")

      if account_name == "EXIT":
        return start(this_client)

      if len(account_name) > 10:
        print("\nUsernames must be at most 10 characters.\n")
      else:
        status = this_client.create_account(account_name)
    
    load_user_menu(this_client)

  elif name == "Login": # option 1 — login
    try:
        if this_client.get_login_input() == 0:
            load_user_menu(this_client)
        else:
            return start(this_client)
    except KeyboardInterrupt:
        return this_client.quit_messenger()

  elif name == "List accounts": # option 3 — list accounts
    decoded_data = this_client.list_accounts()
    if decoded_data != 1 and decoded_data["operation"] == Operations.SUCCESS:
      accounts = decoded_data["info"].split("\n")
      print("\nPlease input a text wildcard. * matches everything, ? matches any single character, [seq] matches any character in seq, and [!seq] matches any character not in seq.\n")
      wildcard = wrap_input("Text wildcard: ")
      print("\nList of accounts currently on the server matching " + wildcard + ":\n")
      for account in accounts:
        if fnmatch.fnmatch(account, wildcard): # fnmatch handles wildcards
          print(str(account))
      wrap_input("\nPress enter to return to the main menu.\n\n")
    else:
      print("\nThere are currently no accounts on the server.\n")
      wrap_input("Press enter to return to the main menu.\n\n")
    
    return start(this_client)

def wrap_menu(menu, actions, message):
    """
    Wraps the curses wrapper method for displaying a menu.

    Args:
    - menu (object): The menu function.
    - actions (list): A list of actions to display in the menu.
    - message (str): A message to display before the menu.

    Returns:
    - str: The user's selected action. If an error occurs, quit the app.
    """
    try:
        return curses.wrapper(menu, actions, message)
    except KeyboardInterrupt:
        return this_client.quit_messenger()

def wrap_input(string):
    """
    Wraps the input function.

    Args:
    - string (str): A message to display before receiving user input.

    Returns:
    - str: The user's input.
    """
    try:
        return input(string)
    except KeyboardInterrupt:
        return this_client.quit_messenger()


if __name__ == "__main__": # run the program
  if len(sys.argv) < 2:
    print("please specify running client or server")
  elif sys.argv[1] == "client": # runs the client application
    this_client = WireClient()
    this_client.CLIENT.connect(this_client.ADDR)
    this_client.background_listener()
    start(this_client)
  elif sys.argv[1] == "server": # runs the server
    this_server = WireServer()
    this_server.SERVER.bind(this_server.ADDR)
    this_server.start()
  else:
    print("please specify running client or server")
