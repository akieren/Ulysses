import time

import pyautogui


def open_app(parameters: dict, response: str, client_instance):
    app_name = parameters.get("app_name")

    if not app_name:
        client_instance.speak(
            "Sir, I am not sure which application you want me to open."
        )
        return False

    client_instance.speak(response)

    try:
        pyautogui.PAUSE = 0.1

        pyautogui.hotkey("alt", "space")
        time.sleep(0.3)

        pyautogui.write(app_name, interval=0.03)
        time.sleep(0.2)

        pyautogui.press("enter")
        time.sleep(0.6)

        return True

    except Exception as e:
        print(f"\033[31m[ERROR] Failed to open app: {e}\033[0m")
        client_instance.speak(
            "Sir, I encountered an error while trying to open the application."
        )
        return False
